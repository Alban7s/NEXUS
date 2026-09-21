import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    github_token: Optional[str] = os.getenv("GITHUB_TOKEN")
    github_owner: Optional[str] = os.getenv("GITHUB_OWNER")
    github_repo: Optional[str] = os.getenv("GITHUB_REPO")

    prometheus_url: Optional[str] = os.getenv("PROMETHEUS_URL")
    argocd_url: Optional[str] = os.getenv("ARGOCD_URL")
    argocd_token: Optional[str] = os.getenv("ARGOCD_TOKEN")

    aws_region: str = os.getenv("AWS_REGION", "us-east-1")

    # --- Deploy pipeline -------------------------------------------------
    # Gate on the upload endpoint. If unset, uploads are unauthenticated —
    # fine for local/dev use, NOT fine for anything reachable on a network.
    nexus_api_key: Optional[str] = os.getenv("NEXUS_API_KEY")

    # Where NEXUS unpacks/builds uploads. Wiped and recreated per job.
    work_dir: str = os.getenv("NEXUS_WORK_DIR", "/tmp/nexus-jobs")

    # Container registry (ECR). If unset, the "push" step is skipped and
    # the pipeline falls back to a local docker run for preview.
    ecr_repository_prefix: Optional[str] = os.getenv("ECR_REPOSITORY_PREFIX")

    # Kubernetes target for "direct" deploys.
    k8s_namespace: str = os.getenv("K8S_NAMESPACE", "default")
    ingress_domain: Optional[str] = os.getenv("INGRESS_DOMAIN")
    ingress_class: str = os.getenv("INGRESS_CLASS", "nginx")

    # GitOps target. If set (together with a reachable Argo CD), NEXUS
    # commits manifests here instead of touching the cluster directly.
    git_repo_url: Optional[str] = os.getenv("GIT_REPO_URL")
    git_branch: str = os.getenv("GIT_BRANCH", "main")
    git_manifests_path: str = os.getenv("GIT_MANIFESTS_PATH", "apps")
    git_user_name: str = os.getenv("GIT_USER_NAME", "nexus-bot")
    git_user_email: str = os.getenv("GIT_USER_EMAIL", "nexus-bot@local")

    # Host the browser can reach for local-fallback preview links.
    public_host: str = os.getenv("NEXUS_PUBLIC_HOST", "localhost")


settings = Settings()
