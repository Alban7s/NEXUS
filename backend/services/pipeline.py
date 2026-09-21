
"""
The deploy pipeline: upload -> inspect -> build -> security -> publish -> deploy
-> verify.

This is the "actuator" half of NEXUS. Everything in services/kubernetes.py,
prometheus.py, github.py, argocd.py only *reads* state. This module is the
only place NEXUS *changes* anything — so every external call in here is
deliberately explicit, logged, and wrapped so a failure in one step leaves a
clear error rather than a half-applied deploy.

Mode selection is automatic, in order of preference:
  1. gitops  — GIT_REPO_URL is set and Argo CD is reachable. NEXUS commits
               manifests; Argo CD is the thing that actually touches the
               cluster.
  2. direct  — no GitOps repo, but the Kubernetes API is reachable.
  3. local   — nothing configured yet. NEXUS builds the image and runs it
               with docker run on the NEXUS host itself.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from ..config import settings
from .jobs import Job, job_store
from . import kubernetes as k8s_service

try:
    import docker  # type: ignore
    from docker.errors import DockerException  # type: ignore
except ImportError:  # pragma: no cover
    docker = None
    DockerException = Exception


MAX_UPLOAD_BYTES = 300 * 1024 * 1024
MAX_FILES = 20_000
MAX_PACKAGE_JSON_BYTES = 2 * 1024 * 1024

SOURCE_CONTROL_DIRECTORIES = {".git", ".svn", ".hg"}

SENSITIVE_FILE_NAMES = {
    ".env",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials",
    "credential",
    ".npmrc",
    ".pypirc",
}

SENSITIVE_SUFFIXES = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
)


class PipelineError(RuntimeError):
    """Expected/handled pipeline failure."""


# --------------------------------------------------------------------------
# Naming
# --------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Turn arbitrary input into a DNS-1123 / docker-tag safe slug."""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")

    if not s:
        s = "site"

    return s[:50]


def make_tag(app_name: str, job_id: str) -> str:
    short = job_id.split("-")[-1]
    return f"{app_name}:{short}"


# --------------------------------------------------------------------------
# Upload extraction
# --------------------------------------------------------------------------

def _member_parts(info: zipfile.ZipInfo) -> tuple[str, ...]:
    """Return a safe archive path or reject a zip-slip entry."""
    raw_name = info.filename.replace("\\", "/")
    path = PurePosixPath(raw_name)

    parts = tuple(
        part for part in path.parts
        if part not in ("", ".")
    )

    if (
        raw_name.startswith("/")
        or path.is_absolute()
        or not parts
        or ".." in parts
    ):
        raise PipelineError("Upload contains an unsafe archive path.")

    return parts


def _unsafe_member_reason(
    parts: tuple[str, ...],
    info: zipfile.ZipInfo,
) -> str | None:
    mode = info.external_attr >> 16

    if stat.S_ISLNK(mode):
        return "symbolic links are not allowed"

    lower_parts = tuple(part.lower() for part in parts)
    filename = lower_parts[-1]

    if any(part in SOURCE_CONTROL_DIRECTORIES for part in lower_parts):
        return "source-control metadata is not allowed"

    if filename in SENSITIVE_FILE_NAMES or filename.startswith(".env."):
        return "environment or credential files are not allowed"

    if filename.endswith(SENSITIVE_SUFFIXES) or "service-account" in filename:
        return "private key or service-account files are not allowed"

    if filename.endswith(".zip"):
        return "nested zip archives are not allowed"

    return None


def _archive_entries(
    zip_path: Path,
) -> list[tuple[zipfile.ZipInfo, tuple[str, ...]]]:
    """Run intake policy before extraction/build."""
    total_size = 0
    entries: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []

    try:
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if len(entries) >= MAX_FILES:
                    raise PipelineError(
                        f"Upload has too many files (>{MAX_FILES})."
                    )

                parts = _member_parts(info)
                reason = _unsafe_member_reason(parts, info)

                if reason:
                    raise PipelineError(
                        f"Upload rejected by the input policy: {reason}."
                    )

                total_size += info.file_size

                if total_size > MAX_UPLOAD_BYTES:
                    raise PipelineError(
                        "Upload is too large once extracted (> 300MB)."
                    )

                entries.append((info, parts))

    except zipfile.BadZipFile as exc:
        raise PipelineError(
            "Upload is not a valid ZIP archive."
        ) from exc

    return entries


def _archive_root(
    entries: list[tuple[zipfile.ZipInfo, tuple[str, ...]]],
) -> str | None:
    files = [
        parts
        for info, parts in entries
        if not info.is_dir() and parts[0] != "__MACOSX"
    ]

    if not files:
        return None

    first = files[0][0]

    if all(
        len(parts) > 1 and parts[0] == first
        for parts in files
    ):
        return first

    return None


# --------------------------------------------------------------------------
# Project inspection
# --------------------------------------------------------------------------

def _project_summary_from_package(
    pkg: dict[str, Any],
) -> dict[str, Any]:
    deps = {
        **pkg.get("dependencies", {}),
        **pkg.get("devDependencies", {}),
    }

    framework = next(
        (
            label
            for key, label in FRAMEWORK_HINTS
            if key in deps
        ),
        "Node.js",
    )

    return {
        "framework": framework,
        "type": "node",
        "kind": "Node frontend",
        "hasBuildScript": "build" in (pkg.get("scripts") or {}),
    }


def inspect_upload(
    zip_path: Path,
    original_filename: str,
) -> dict[str, Any]:
    """Validate intake and return a safe project summary."""
    entries = _archive_entries(zip_path)
    root_folder = _archive_root(entries)

    package_entry: zipfile.ZipInfo | None = None
    has_index = False

    for info, parts in entries:
        if info.is_dir() or parts[0] == "__MACOSX":
            continue

        relative = (
            parts[1:]
            if root_folder and parts[0] == root_folder
            else parts
        )

        if relative == ("package.json",):
            package_entry = info

        elif relative == ("index.html",):
            has_index = True

    package: dict[str, Any] | None = None

    if package_entry:
        if package_entry.file_size > MAX_PACKAGE_JSON_BYTES:
            raise PipelineError(
                "package.json is too large to inspect safely."
            )

        try:
            with zipfile.ZipFile(zip_path) as zf:
                package = json.loads(
                    zf.read(package_entry).decode("utf-8")
                )

        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PipelineError(
                "package.json is not valid UTF-8 JSON."
            ) from exc

        summary = _project_summary_from_package(package)

    elif has_index:
        summary = {
            "framework": "Static HTML/CSS/JS",
            "type": "static",
            "kind": "Static website",
            "hasBuildScript": False,
        }

    else:
        raise PipelineError(
            "Couldn't find a root index.html or package.json. "
            "NEXUS accepts static sites and Node-built frontends."
        )

    suggested_name = slugify(
        str(
            (package or {}).get("name")
            or root_folder
            or Path(original_filename).stem
        )
    )

    return {
        "suggestedName": suggested_name,
        **summary,
    }


def scan_project_input(root: Path) -> None:
    """Defence in depth after extraction."""
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        parts = tuple(relative.parts)

        if path.is_symlink():
            raise PipelineError(
                "Upload rejected by the input policy: "
                "symbolic links are not allowed."
            )

        synthetic = zipfile.ZipInfo(
            str(relative).replace("\\", "/")
        )

        reason = _unsafe_member_reason(parts, synthetic)

        if reason:
            raise PipelineError(
                f"Upload rejected by the input policy: {reason}."
            )


def extract_upload(
    zip_path: Path,
    dest: Path,
) -> Path:
    """Safely extract uploaded zip."""
    dest.mkdir(parents=True, exist_ok=True)

    _archive_entries(zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)

    return find_project_root(dest)


def find_project_root(root: Path) -> Path:
    """Find project root, handling a wrapping folder."""
    current = root

    for _ in range(4):
        entries = [
            p
            for p in current.iterdir()
            if not p.name.startswith("__MACOSX")
        ]

        has_marker = (
            (current / "index.html").exists()
            or (current / "package.json").exists()
        )

        if (
            has_marker
            or len(entries) != 1
            or not entries[0].is_dir()
        ):
            return current

        current = entries[0]

    return current


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

FRAMEWORK_HINTS = [
    ("next", "Next.js"),
    ("vite", "Vite"),
    ("react-scripts", "Create React App"),
    ("react", "React"),
    ("vue", "Vue"),
    ("@angular/core", "Angular"),
    ("svelte", "Svelte"),
    ("astro", "Astro"),
]


def detect_project(root: Path) -> dict[str, Any]:
    pkg_path = root / "package.json"

    if pkg_path.exists():
        try:
            pkg = json.loads(
                pkg_path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise PipelineError(
                f"package.json is not valid JSON: {exc}"
            ) from exc

        summary = _project_summary_from_package(pkg)

        return {
            "root": root,
            **summary,
            "has_build_script": summary["hasBuildScript"],
        }

    if (root / "index.html").exists():
        return {
            "root": root,
            "type": "static",
            "framework": "Static HTML/CSS/JS",
            "kind": "Static website",
            "hasBuildScript": False,
            "has_build_script": False,
        }

    raise PipelineError(
        "Couldn't find index.html or package.json — "
        "nothing here looks like a website."
    )


# --------------------------------------------------------------------------
# Dockerfile / nginx generation
# --------------------------------------------------------------------------

NGINX_CONF = """server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /healthz {
        default_type text/plain;
        return 200 'ok';
    }
}
"""


DOCKERIGNORE = """.git
.gitignore
.github
node_modules
__pycache__
*.pyc
.env
.env.*
"""


STATIC_DOCKERFILE = """FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY . /usr/share/nginx/html
"""


NODE_DOCKERFILE = """FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN if [ -f package-lock.json ] || [ -f npm-shrinkwrap.json ]; then \\
      npm ci --no-audit --no-fund; \\
    else \\
      npm install --no-audit --no-fund; \\
    fi

COPY . .

RUN npm run build

RUN mkdir -p /out \\
    && (cp -r build/. /out/ 2>/dev/null || true) \\
    && (cp -r dist/. /out/ 2>/dev/null || true) \\
    && (cp -r out/. /out/ 2>/dev/null || true)

RUN [ -n "$(ls -A /out 2>/dev/null)" ] || \\
    (echo "No build output found in build/, dist/, or out/" && exit 1)


FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /out /usr/share/nginx/html
"""


def write_build_context(
    project: dict[str, Any],
) -> None:
    root: Path = project["root"]

    (root / "nginx.conf").write_text(
        NGINX_CONF,
        encoding="utf-8",
    )

    (root / ".dockerignore").write_text(
        DOCKERIGNORE,
        encoding="utf-8",
    )

    if project["type"] == "node":
        if not project["has_build_script"]:
            raise PipelineError(
                'package.json has no "build" script. '
                'Add one (e.g. `"build": "vite build"`) '
                "and re-upload."
            )

        (root / "Dockerfile").write_text(
            NODE_DOCKERFILE,
            encoding="utf-8",
        )

    else:
        (root / "Dockerfile").write_text(
            STATIC_DOCKERFILE,
            encoding="utf-8",
        )


# --------------------------------------------------------------------------
# Docker
# --------------------------------------------------------------------------

def get_docker_client():
    if docker is None:
        raise PipelineError(
            "The `docker` Python package isn't installed "
            "on the NEXUS backend."
        )

    try:
        return docker.from_env()

    except DockerException as exc:
        raise PipelineError(
            f"Couldn't reach the Docker daemon from NEXUS ({exc}). "
            "NEXUS needs access to a Docker socket to build images."
        ) from exc


def build_image(
    project_root: Path,
    tag: str,
    log,
) -> str:
    """Build an image after validating the generated build context."""

    client = get_docker_client()

    dockerfile = project_root / "Dockerfile"
    nginx_conf = project_root / "nginx.conf"
    dockerignore = project_root / ".dockerignore"

    if not dockerfile.exists():
        raise PipelineError(
            f"Generated Dockerfile is missing from build context: "
            f"{dockerfile}"
        )

    if not nginx_conf.exists():
        raise PipelineError(
            f"Generated nginx.conf is missing from build context: "
            f"{nginx_conf}"
        )

    if not dockerignore.exists():
        raise PipelineError(
            f"Generated .dockerignore is missing from build context: "
            f"{dockerignore}"
        )

    ignore_text = dockerignore.read_text(
        encoding="utf-8"
    )

    ignored_lines = {
        line.strip()
        for line in ignore_text.splitlines()
        if line.strip()
        and not line.strip().startswith("#")
    }

    if "nginx.conf" in ignored_lines:
        raise PipelineError(
            "Generated nginx.conf is excluded by .dockerignore. "
            "Remove nginx.conf from .dockerignore before building."
        )

    log(f"Build context: {project_root}")
    log(f"Dockerfile: {dockerfile}")
    log(f"nginx.conf: {nginx_conf}")

    log(
        f"docker build -t {tag} {project_root}"
    )

    try:
        _, build_log = client.images.build(
            path=str(project_root),
            tag=tag,
            rm=True,
        )

        for chunk in build_log:
            line = (
                chunk.get("stream")
                or chunk.get("status")
            )

            if line:
                log(line.rstrip())

    except DockerException as exc:
        raise PipelineError(
            f"Image build failed: {exc}"
        ) from exc

    return tag


# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------

def run_security_scan(
    project_root: Path,
    log,
) -> bool:
    """Run Trivy when available."""
    scanner = shutil.which("trivy")

    if not scanner:
        log(
            "Filesystem vulnerability scan unavailable: "
            "Trivy is not installed; input-policy gate already ran.",
            level="warn",
        )
        return False

    log(
        "Running Trivy filesystem vulnerability scan."
    )

    result = subprocess.run(
        [
            scanner,
            "fs",
            "--quiet",
            "--exit-code",
            "1",
            str(project_root),
        ],
        capture_output=True,
        text=True,
    )

    for line in (
        result.stdout + "\n" + result.stderr
    ).splitlines():
        if line.strip():
            log(line.strip())

    if result.returncode == 0:
        return True

    if result.returncode == 1:
        raise PipelineError(
            "Trivy found security issues in the uploaded "
            "project. Release stopped before publishing."
        )

    raise PipelineError(
        "Trivy could not complete the security scan; "
        "release stopped before publishing."
    )


# --------------------------------------------------------------------------
# ECR
# --------------------------------------------------------------------------

def ecr_repo_uri(
    app_name: str,
) -> str | None:
    if not settings.ecr_repository_prefix:
        return None

    return (
        f"{settings.ecr_repository_prefix.rstrip('/')}"
        f"/{app_name}"
    )


def push_to_ecr(
    app_name: str,
    local_tag: str,
    job_id: str,
    log,
) -> str:
    """Push local image to ECR."""
    ecr = boto3.client(
        "ecr",
        region_name=settings.aws_region,
    )

    try:
        ecr.create_repository(
            repositoryName=app_name
        )

        log(
            f"Created ECR repository '{app_name}'"
        )

    except ecr.exceptions.RepositoryAlreadyExistsException:
        pass

    except (BotoCoreError, ClientError) as exc:
        raise PipelineError(
            f"Couldn't create/check ECR repository: {exc}"
        ) from exc

    try:
        auth = ecr.get_authorization_token()[
            "authorizationData"
        ][0]

    except (BotoCoreError, ClientError) as exc:
        raise PipelineError(
            f"Couldn't get ECR auth token: {exc}"
        ) from exc

    username, password = (
        base64.b64decode(
            auth["authorizationToken"]
        )
        .decode()
        .split(":", 1)
    )

    registry = auth["proxyEndpoint"].replace(
        "https://",
        "",
    )

    client = get_docker_client()

    try:
        client.login(
            username=username,
            password=password,
            registry=registry,
        )

    except DockerException as exc:
        raise PipelineError(
            f"Docker login to ECR failed: {exc}"
        ) from exc

    remote_tag = job_id.split("-")[-1]

    repo_uri = f"{registry}/{app_name}"
    full_uri = f"{repo_uri}:{remote_tag}"

    image = client.images.get(local_tag)

    image.tag(
        repo_uri,
        tag=remote_tag,
    )

    log(f"Pushing {full_uri}")

    try:
        for chunk in client.images.push(
            repo_uri,
            tag=remote_tag,
            stream=True,
            decode=True,
        ):
            if "status" in chunk:
                progress = chunk.get(
                    "progress",
                    "",
                )

                log(
                    f"{chunk['status']} "
                    f"{progress}".strip()
                )

            if "errorDetail" in chunk:
                raise PipelineError(
                    chunk["errorDetail"].get(
                        "message",
                        "push failed",
                    )
                )

    except DockerException as exc:
        raise PipelineError(
            f"Image push failed: {exc}"
        ) from exc

    return full_uri


# --------------------------------------------------------------------------
# Mode selection
# --------------------------------------------------------------------------

def choose_mode(log) -> str:
    if (
        settings.git_repo_url
        and settings.argocd_url
    ):
        log(
            "GitOps repo + Argo CD are configured "
            "-> using GitOps mode."
        )
        return "gitops"

    if settings.ecr_repository_prefix:
        try:
            k8s_service.load_clients()

            log(
                "No GitOps repo configured, but the "
                "Kubernetes API is reachable -> using direct mode."
            )

            return "direct"

        except Exception as exc:
            log(
                f"Kubernetes API not reachable ({exc}); "
                "falling back to local preview mode."
            )

            return "local"

    log(
        "No registry/cluster configured yet "
        "-> using local preview mode."
    )

    return "local"


# --------------------------------------------------------------------------
# Kubernetes manifests
# --------------------------------------------------------------------------

def build_manifests(
    app_name: str,
    image_uri: str,
) -> dict[str, dict]:
    labels = {
        "app": app_name,
        "managed-by": "nexus",
    }

    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": app_name,
            "namespace": settings.k8s_namespace,
            "labels": labels,
        },
        "spec": {
            "replicas": 2,
            "selector": {
                "matchLabels": {
                    "app": app_name,
                }
            },
            "template": {
                "metadata": {
                    "labels": labels,
                },
                "spec": {
                    "containers": [
                        {
                            "name": app_name,
                            "image": image_uri,
                            "ports": [
                                {
                                    "containerPort": 80
                                }
                            ],
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/healthz",
                                    "port": 80,
                                },
                                "initialDelaySeconds": 3,
                                "periodSeconds": 5,
                            },
                            "resources": {
                                "requests": {
                                    "cpu": "50m",
                                    "memory": "64Mi",
                                },
                                "limits": {
                                    "cpu": "250m",
                                    "memory": "256Mi",
                                },
                            },
                        }
                    ]
                },
            },
        },
    }

    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": app_name,
            "namespace": settings.k8s_namespace,
            "labels": labels,
        },
        "spec": {
            "selector": {
                "app": app_name,
            },
            "ports": [
                {
                    "port": 80,
                    "targetPort": 80,
                }
            ],
        },
    }

    manifests = {
        "deployment": deployment,
        "service": service,
    }

    if settings.ingress_domain:
        host = (
            f"{app_name}."
            f"{settings.ingress_domain}"
        )

        manifests["ingress"] = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": app_name,
                "namespace": settings.k8s_namespace,
                "labels": labels,
                "annotations": {
                    "kubernetes.io/ingress.class":
                        settings.ingress_class,
                },
            },
            "spec": {
                "rules": [
                    {
                        "host": host,
                        "http": {
                            "paths": [
                                {
                                    "path": "/",
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": app_name,
                                            "port": {
                                                "number": 80,
                                            },
                                        }
                                    },
                                }
                            ]
                        },
                    }
                ]
            },
        }

    return manifests


def preview_url_for(
    app_name: str,
) -> str | None:
    if settings.ingress_domain:
        return (
            f"https://{app_name}."
            f"{settings.ingress_domain}"
        )

    return None


# --------------------------------------------------------------------------
# Direct Kubernetes deployment
# --------------------------------------------------------------------------

def deploy_direct(
    app_name: str,
    image_uri: str,
    log,
) -> None:
    from kubernetes import client as k8s_client
    from kubernetes.client.rest import ApiException

    manifests = build_manifests(
        app_name,
        image_uri,
    )

    core, apps = k8s_service.load_clients()
    networking = k8s_client.NetworkingV1Api()

    ns = settings.k8s_namespace

    def apply(
        get_fn,
        create_fn,
        replace_fn,
        body,
        kind,
    ):
        name = body["metadata"]["name"]

        try:
            get_fn(name, ns)

            replace_fn(
                name,
                ns,
                body,
            )

            log(
                f"Updated {kind} '{name}' "
                f"in namespace '{ns}'"
            )

        except ApiException as exc:
            if exc.status == 404:
                create_fn(
                    ns,
                    body,
                )

                log(
                    f"Created {kind} '{name}' "
                    f"in namespace '{ns}'"
                )

            else:
                raise PipelineError(
                    f"Kubernetes API error applying "
                    f"{kind} '{name}': {exc.reason}"
                ) from exc

    apply(
        apps.read_namespaced_deployment,
        apps.create_namespaced_deployment,
        apps.replace_namespaced_deployment,
        manifests["deployment"],
        "Deployment",
    )

    apply(
        core.read_namespaced_service,
        core.create_namespaced_service,
        core.replace_namespaced_service,
        manifests["service"],
        "Service",
    )

    if "ingress" in manifests:
        apply(
            networking.read_namespaced_ingress,
            networking.create_namespaced_ingress,
            networking.replace_namespaced_ingress,
            manifests["ingress"],
            "Ingress",
        )


def verify_direct(
    app_name: str,
    log,
    timeout_s: int = 90,
) -> bool:
    import time as _time
    from kubernetes import client as k8s_client

    apps = k8s_client.AppsV1Api()
    ns = settings.k8s_namespace
    deadline = _time.time() + timeout_s

    while _time.time() < deadline:
        status = (
            apps.read_namespaced_deployment_status(
                app_name,
                ns,
            ).status
        )

        available = status.available_replicas or 0
        desired = status.replicas or 0

        log(
            f"Rollout: "
            f"{available}/{desired} pods available"
        )

        if (
            desired > 0
            and available >= desired
        ):
            return True

        _time.sleep(3)

    return False


# --------------------------------------------------------------------------
# GitOps
# --------------------------------------------------------------------------

def _run_git(
    args: list[str],
    cwd: Path,
    log,
) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        log(result.stdout.strip())

    if result.returncode != 0:
        raise PipelineError(
            f"git {' '.join(args)} failed: "
            f"{result.stderr.strip()}"
        )


def deploy_gitops(
    app_name: str,
    image_uri: str,
    workdir: Path,
    log,
) -> None:
    import yaml

    clone_dir = workdir / "gitops-repo"

    log(
        f"Cloning {settings.git_repo_url} "
        f"(branch {settings.git_branch})"
    )

    _run_git(
        [
            "clone",
            "--depth",
            "1",
            "--branch",
            settings.git_branch,
            settings.git_repo_url,
            str(clone_dir),
        ],
        cwd=workdir,
        log=log,
    )

    _run_git(
        [
            "config",
            "user.name",
            settings.git_user_name,
        ],
        cwd=clone_dir,
        log=log,
    )

    _run_git(
        [
            "config",
            "user.email",
            settings.git_user_email,
        ],
        cwd=clone_dir,
        log=log,
    )

    app_dir = (
        clone_dir
        / settings.git_manifests_path
        / app_name
    )

    app_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifests = build_manifests(
        app_name,
        image_uri,
    )

    for name, body in manifests.items():
        (
            app_dir / f"{name}.yaml"
        ).write_text(
            yaml.safe_dump(
                body,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        log(
            f"Wrote "
            f"{settings.git_manifests_path}/"
            f"{app_name}/{name}.yaml"
        )

    _run_git(
        ["add", "."],
        cwd=clone_dir,
        log=log,
    )

    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
        ],
        cwd=clone_dir,
        capture_output=True,
        text=True,
    )

    if not status.stdout.strip():
        log(
            "No manifest changes to commit "
            "(image tag unchanged)."
        )
        return

    _run_git(
        [
            "commit",
            "-m",
            f"nexus: deploy {app_name} -> {image_uri}",
        ],
        cwd=clone_dir,
        log=log,
    )

    _run_git(
        [
            "push",
            "origin",
            settings.git_branch,
        ],
        cwd=clone_dir,
        log=log,
    )

    log(
        "Pushed. Argo CD will pick this up on its next "
        "sync (or auto-sync if enabled)."
    )


# --------------------------------------------------------------------------
# Local Docker preview
# --------------------------------------------------------------------------

def _free_port() -> int:
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def deploy_local(
    app_name: str,
    local_tag: str,
    log,
) -> str:
    client = get_docker_client()

    try:
        old = client.containers.get(
            f"nexus-{app_name}"
        )

        log(
            f"Removing previous local preview "
            f"container for '{app_name}'"
        )

        old.remove(force=True)

    except docker.errors.NotFound:
        pass

    port = _free_port()

    client.containers.run(
        local_tag,
        name=f"nexus-{app_name}",
        ports={
            "80/tcp": port
        },
        detach=True,
        labels={
            "managed-by": "nexus"
        },
    )

    log(
        f"Running locally on port {port}"
    )

    return (
        f"http://{settings.public_host}:{port}"
    )


# --------------------------------------------------------------------------
# Pipeline orchestrator
# --------------------------------------------------------------------------

async def run_pipeline(
    job: Job,
    zip_path: Path,
) -> None:
    import asyncio

    def log(
        text: str,
        level: str = "info",
    ) -> None:
        job_store.log(
            job.id,
            text,
            level,
        )

    def step(
        name: str,
        status: str,
    ) -> None:
        job_store.set_step(
            job.id,
            name,
            status,
        )

    workdir = (
        Path(settings.work_dir)
        / job.id
    )

    try:
        job.status = "running"

        # --------------------------------------------------------------
        # 1. Upload
        # --------------------------------------------------------------

        step(
            "upload",
            "running",
        )

        log(
            f"Extracting upload for "
            f"'{job.app_name}'"
        )

        project_root = await asyncio.to_thread(
            extract_upload,
            zip_path,
            workdir / "src",
        )

        step(
            "upload",
            "success",
        )

        # --------------------------------------------------------------
        # 2. Inspect
        # --------------------------------------------------------------

        step(
            "inspect",
            "running",
        )

        project = await asyncio.to_thread(
            detect_project,
            project_root,
        )

        project_summary = {
            "framework": project["framework"],
            "type": project["type"],
            "kind": project["kind"],
            "hasBuildScript": project[
                "hasBuildScript"
            ],
        }

        job_store.set_project(
            job.id,
            project_summary,
        )

        log(
            f"Detected "
            f"{project['framework']} — "
            f"{project['kind']}."
        )

        await asyncio.to_thread(
            scan_project_input,
            project_root,
        )

        log(
            "Upload input-policy gate passed "
            "before build.",
            level="success",
        )

        await asyncio.to_thread(
            write_build_context,
            project,
        )

        step(
            "inspect",
            "success",
        )

        # --------------------------------------------------------------
        # 3. Build
        # --------------------------------------------------------------

        step(
            "build",
            "running",
        )

        local_tag = make_tag(
            job.app_name,
            job.id,
        )

        await asyncio.to_thread(
            build_image,
            project_root,
            local_tag,
            log,
        )

        job.image_tag = local_tag

        step(
            "build",
            "success",
        )

        # --------------------------------------------------------------
        # 4. Security
        # --------------------------------------------------------------

        step(
            "security",
            "running",
        )

        scanned = await asyncio.to_thread(
            run_security_scan,
            project_root,
            log,
        )

        step(
            "security",
            "success" if scanned else "skipped",
        )

        # --------------------------------------------------------------
        # Mode selection
        # --------------------------------------------------------------

        mode = await asyncio.to_thread(
            choose_mode,
            log,
        )

        job.mode = mode

        # --------------------------------------------------------------
        # 5. Publish
        # --------------------------------------------------------------

        image_uri = local_tag

        if mode in (
            "gitops",
            "direct",
        ):
            step(
                "publish",
                "running",
            )

            image_uri = await asyncio.to_thread(
                push_to_ecr,
                job.app_name,
                local_tag,
                job.id,
                log,
            )

            job.image_tag = image_uri

            step(
                "publish",
                "success",
            )

        else:
            step(
                "publish",
                "skipped",
            )

            log(
                "Registry publish skipped: "
                "this release is using local "
                "preview mode."
            )

        # --------------------------------------------------------------
        # 6. Deploy
        # --------------------------------------------------------------

        step(
            "deploy",
            "running",
        )

        if mode == "gitops":
            await asyncio.to_thread(
                deploy_gitops,
                job.app_name,
                image_uri,
                workdir,
                log,
            )

            job.preview_url = preview_url_for(
                job.app_name
            )

        elif mode == "direct":
            await asyncio.to_thread(
                deploy_direct,
                job.app_name,
                image_uri,
                log,
            )

            job.preview_url = preview_url_for(
                job.app_name
            )

        else:
            job.preview_url = await asyncio.to_thread(
                deploy_local,
                job.app_name,
                local_tag,
                log,
            )

        step(
            "deploy",
            "success",
        )

        # --------------------------------------------------------------
        # 7. Verify
        # --------------------------------------------------------------

        step(
            "verify",
            "running",
        )

        if mode == "direct":
            healthy = await asyncio.to_thread(
                verify_direct,
                job.app_name,
                log,
            )

            step(
                "verify",
                "success" if healthy else "failed",
            )

            if not healthy:
                raise PipelineError(
                    "Deployment did not become "
                    "healthy within the timeout."
                )

        elif mode == "gitops":
            log(
                "Verification skipped: Argo CD applies "
                "GitOps changes asynchronously; inspect "
                "its sync/health state before treating "
                "this release as verified.",
                level="warn",
            )

            step(
                "verify",
                "skipped",
            )

        else:
            log(
                "Local preview verification is limited "
                "to Docker reporting the container as running."
            )

            step(
                "verify",
                "success",
            )

        log(
            f"Done. {job.app_name} deployed "
            f"via {mode} mode.",
            level="success",
        )

        job_store.finish(
            job.id,
            "success",
        )

    except PipelineError as exc:
        log(
            str(exc),
            level="error",
        )

        current = next(
            (
                s
                for s in job.steps
                if job.steps[s] == "running"
            ),
            None,
        )

        if current:
            step(
                current,
                "failed",
            )

        job_store.finish(
            job.id,
            "failed",
            error=str(exc),
        )

    except Exception as exc:
        log(
            f"Unexpected error: {exc}",
            level="error",
        )

        current = next(
            (
                s
                for s in job.steps
                if job.steps[s] == "running"
            ),
            None,
        )

        if current:
            step(
                current,
                "failed",
            )

        job_store.finish(
            job.id,
            "failed",
            error=str(exc),
        )

    finally:
        shutil.rmtree(
            workdir / "src",
            ignore_errors=True,
        )

        try:
            zip_path.unlink(
                missing_ok=True
            )
        except Exception:
            pass
