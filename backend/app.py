import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import httpx

from .config import settings
from .services.kubernetes import cluster_snapshot
from .services.prometheus import prometheus_query, first_value
from .services.github import workflow_runs
from .services.argocd import applications as argocd_applications
from .services.jobs import job_store
from .services.pipeline import PipelineError, inspect_upload, slugify, run_pipeline


app = FastAPI(title="NEXUS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parent.parent


def response(mode: str, source: str, data: Any = None, error: str | None = None):
    return {
        "mode": mode,
        "source": source,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "error": error,
    }


@app.get("/api/health")
async def health():
    checks: dict[str, dict[str, Any]] = {}

    # Prometheus connectivity
    if settings.prometheus_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(settings.prometheus_url.rstrip("/") + "/-/ready")
                checks["prometheus"] = {"connected": r.is_success}
        except httpx.HTTPError as exc:
            checks["prometheus"] = {"connected": False, "error": str(exc)}
    else:
        checks["prometheus"] = {"connected": False, "error": "PROMETHEUS_URL not configured"}

    # Kubernetes connectivity
    try:
        snapshot = cluster_snapshot()
        checks["kubernetes"] = {
            "connected": True,
            "status": snapshot["clusterStatus"],
        }
    except Exception as exc:
        checks["kubernetes"] = {"connected": False, "error": str(exc)}

    # GitHub configuration (actual API test is done by /api/deployments)
    checks["github"] = {
        "configured": bool(settings.github_owner and settings.github_repo),
    }

    # Argo CD configuration
    checks["argocd"] = {
        "configured": bool(settings.argocd_url),
    }

    connected_count = sum(
        1 for item in checks.values()
        if item.get("connected") is True
    )
    configured_count = len(checks)

    if connected_count == configured_count:
        status = "CONNECTED"
    elif connected_count > 0:
        status = "DEGRADED"
    else:
        status = "NOT CONNECTED"

    return response("live", "NEXUS integration health", {
        "status": status,
        "checks": checks,
    })


@app.get("/api/kubernetes")
async def kubernetes():
    try:
        data = cluster_snapshot()
        return response("live", "Kubernetes API", data)
    except Exception as exc:
        return response("unavailable", "Kubernetes API", None, str(exc))


@app.get("/api/observability")
async def observability():
    if not settings.prometheus_url:
        return response(
            "unavailable",
            "Prometheus",
            None,
            "PROMETHEUS_URL not configured",
        )

    queries = {
        "CPU utilization": '100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])))',
        "Memory utilization": '100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))',
        "Request rate": 'sum(rate(http_requests_total[5m]))',
        "Error rate": '100 * sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))',
    }

    panels = []

    for label, query in queries.items():
        payload = await prometheus_query(settings.prometheus_url, query)
        value = first_value(payload)

        if value is None:
            panels.append({
                "label": label,
                "value": None,
                "source": "Prometheus",
                "status": "NO DATA",
            })
        else:
            suffix = "%" if label in {"CPU utilization", "Memory utilization", "Error rate"} else " req/s"
            panels.append({
                "label": label,
                "value": f"{value:.2f}{suffix}",
                "source": "Prometheus",
                "status": "LIVE",
            })

    return response("live", "Prometheus", {"panels": panels})


@app.get("/api/deployments")
async def deployments():
    if not settings.github_owner or not settings.github_repo:
        return response("unavailable", "GitHub Actions", None, "GITHUB_OWNER / GITHUB_REPO not configured")

    try:
        payload = await workflow_runs(
            settings.github_owner,
            settings.github_repo,
            settings.github_token,
        )

        runs = []
        for run in payload.get("workflow_runs", []):
            runs.append({
                "app": settings.github_repo,
                "env": "unknown",
                "version": run.get("display_title") or run.get("name"),
                "commit": (run.get("head_sha") or "")[:7],
                "branch": run.get("head_branch"),
                "author": (run.get("actor") or {}).get("login"),
                "startedAt": run.get("run_started_at") or run.get("created_at"),
                "durationSec": None,
                "status": (run.get("conclusion") or run.get("status") or "UNKNOWN").upper(),
                "health": "UNKNOWN",
            })

        return response("live", "GitHub Actions", runs)
    except Exception as exc:
        return response("error", "GitHub Actions", None, str(exc))


@app.get("/api/pipelines")
async def pipelines():
    if not settings.github_owner or not settings.github_repo:
        return response("unavailable", "GitHub Actions", None, "GitHub repository not configured")

    try:
        payload = await workflow_runs(
            settings.github_owner,
            settings.github_repo,
            settings.github_token,
        )
        runs = payload.get("workflow_runs", [])
        if not runs:
            return response("live", "GitHub Actions", None, "No workflow runs found")

        run = runs[0]
        data = {
            "pipeline": f'{settings.github_repo} / {run.get("name")}',
            "commit": (run.get("head_sha") or "")[:7],
            "branch": run.get("head_branch"),
            "triggeredBy": (run.get("actor") or {}).get("login"),
            "startedAt": run.get("run_started_at") or run.get("created_at"),
            "durationSec": None,
            "currentStage": run.get("status"),
            "status": (run.get("conclusion") or run.get("status") or "UNKNOWN").upper(),
            "stages": [],
        }
        return response("live", "GitHub Actions", data)
    except Exception as exc:
        return response("error", "GitHub Actions", None, str(exc))


@app.get("/api/gitops")
async def gitops():
    if not settings.argocd_url:
        return response("unavailable", "Argo CD", None, "ARGOCD_URL not configured")

    try:
        payload = await argocd_applications(settings.argocd_url, settings.argocd_token)
        items = payload.get("items", [])
        data = []

        for item in items:
            status = item.get("status", {})
            operation = status.get("operationState", {})
            summary = status.get("summary", {})
            data.append({
                "app": item.get("metadata", {}).get("name"),
                "repo": summary.get("images", []),
                "targetRevision": item.get("spec", {}).get("source", {}).get("targetRevision"),
                "desired": item.get("spec", {}).get("source", {}).get("targetRevision"),
                "live": status.get("sync", {}).get("revision"),
                "sync": (status.get("sync", {}).get("status") or "UNKNOWN").upper(),
                "health": (status.get("health", {}).get("status") or "UNKNOWN").upper(),
                "lastSync": operation.get("finishedAt") or operation.get("startedAt"),
            })

        return response("live", "Argo CD", data)
    except Exception as exc:
        return response("error", "Argo CD", None, str(exc))


@app.get("/api/infrastructure")
async def infrastructure():
    try:
        eks = boto3.client("eks", region_name=settings.aws_region)
        ecr = boto3.client("ecr", region_name=settings.aws_region)

        clusters = eks.list_clusters().get("clusters", [])
        repositories = ecr.describe_repositories().get("repositories", [])

        return response("live", f"AWS ({settings.aws_region})", {
            "clusters": clusters,
            "ecrRepositories": [r.get("repositoryName") for r in repositories],
        })
    except (BotoCoreError, ClientError, Exception) as exc:
        return response("unavailable", f"AWS ({settings.aws_region})", None, str(exc))


@app.get("/api/security")
async def security():
    return response(
        "unavailable",
        "Security scanners",
        None,
        "Security scan ingestion is not configured yet. Do not fabricate findings.",
    )


@app.get("/api/logs")
async def logs():
    return response(
        "unavailable",
        "Loki",
        None,
        "Loki log ingestion is not configured yet. Do not fabricate logs.",
    )


@app.get("/api/costs")
async def costs():
    return response(
        "unavailable",
        "AWS Cost Explorer",
        None,
        "Cost Explorer integration is not configured yet. Do not fabricate costs.",
    )


@app.get("/api/metrics")
async def metrics():
    return response(
        "unavailable",
        "NEXUS live metric aggregation",
        None,
        "Platform-level SLO/MTTR/deployment-frequency aggregation will be added from live sources.",
    )


def _require_api_key(x_nexus_api_key: str | None) -> None:
    if settings.nexus_api_key and x_nexus_api_key != settings.nexus_api_key:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Nexus-Api-Key header.")


@app.post("/api/deploy")
async def deploy(
    file: UploadFile = File(...),
    app_name: str | None = Form(None),
    x_nexus_api_key: str | None = Header(None),
):
    """Upload a zip of website files and kick off the full build/deploy
    pipeline in the background. Returns immediately with a job id — poll
    /api/deploy/jobs/{id} or stream /api/deploy/jobs/{id}/stream for progress.
    """
    _require_api_key(x_nexus_api_key)

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload must be a .zip file.")

    work_root = Path(settings.work_dir)
    work_root.mkdir(parents=True, exist_ok=True)
    upload_path = work_root / f"upload-{uuid.uuid4().hex}.zip"

    size = 0
    with open(upload_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 300 * 1024 * 1024:
                upload_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Upload exceeds 300MB.")
            f.write(chunk)

    try:
        inspection = await asyncio.to_thread(inspect_upload, upload_path, file.filename)
    except PipelineError as exc:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # The optional field wins, but a blank field means the server-derived
    # archive/package name becomes the release name.
    name = slugify(app_name) if app_name and app_name.strip() else inspection["suggestedName"]
    job = job_store.create(app_name=name, project=inspection)
    asyncio.create_task(run_pipeline(job, upload_path))

    return response("live", "NEXUS deploy pipeline", {
        "jobId": job.id,
        "app": name,
        "project": inspection,
    })


@app.get("/api/deploy/config")
async def deploy_config():
    """Public, non-secret configuration needed to make the upload UI honest."""
    if settings.git_repo_url and settings.argocd_url:
        target = {
            "mode": "gitops",
            "label": "GitOps / Argo CD target configured",
            "detail": "NEXUS will commit generated manifests; Argo CD performs the cluster rollout and verification remains asynchronous.",
        }
    elif settings.ecr_repository_prefix:
        target = {
            "mode": "direct-candidate",
            "label": "Kubernetes direct target configured",
            "detail": "NEXUS will use Kubernetes only if the backend can reach the cluster; otherwise it falls back to a local preview.",
        }
    else:
        target = {
            "mode": "local",
            "label": "Local preview target",
            "detail": "No cloud target is configured. NEXUS will build the image and run a local Docker preview.",
        }
    target["requiresApiKey"] = bool(settings.nexus_api_key)
    return response("live", "NEXUS deploy configuration", target)


@app.get("/api/deploy/jobs")
async def list_jobs():
    jobs = [j.to_summary() for j in job_store.list_recent()]
    return response("live", "NEXUS deploy pipeline", jobs)


@app.get("/api/deploy/jobs/{job_id}")
async def get_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return response("live", "NEXUS deploy pipeline", job.to_detail())


@app.get("/api/deploy/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    """Server-sent events: pushes new log lines / step changes as they
    happen so the UI doesn't have to poll aggressively."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_source():
        sent = 0
        while True:
            job = job_store.get(job_id)
            if not job:
                break
            detail = job.to_detail(since=sent)
            sent += len(detail["logs"])
            yield f"data: {json.dumps(detail)}\n\n"
            if job.status in ("success", "failed"):
                break
            await job_store.wait(job_id, timeout=10.0)

    return StreamingResponse(event_source(), media_type="text/event-stream")


# Serve the existing frontend from the same origin.
app.mount("/", StaticFiles(directory=str(ROOT), html=True), name="frontend")
