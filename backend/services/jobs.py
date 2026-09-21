"""
In-memory job tracking for the deploy pipeline.

Deliberately not a database: NEXUS is a control plane, not a system of
record. A job's real history lives in the git commits / image tags / k8s
objects it produces. This store just powers the live UI (progress steps,
log console, recent-runs list) while the process is up.
"""

from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["queued", "running", "success", "failed"]

# Canonical pipeline steps, in order. A job's `steps` dict always has all
# of these keys so the UI can render a fixed-width progress tracker
# instead of guessing what's next.
STEP_ORDER = [
    "upload",
    "inspect",
    "build",
    "security",
    "publish",
    "deploy",
    "verify",
]

StepStatus = Literal["pending", "running", "success", "failed", "skipped"]

_id_counter = itertools.count(1)


@dataclass
class LogLine:
    ts: float
    text: str
    level: str = "info"  # info | warn | error | success


@dataclass
class Job:
    id: str
    app_name: str
    status: Status = "queued"
    mode: str | None = None  # "gitops" | "direct" | "local"
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    steps: dict[str, StepStatus] = field(
        default_factory=lambda: {s: "pending" for s in STEP_ORDER}
    )
    logs: list[LogLine] = field(default_factory=list)
    preview_url: str | None = None
    error: str | None = None
    image_tag: str | None = None
    # This is deliberately a small, user-facing summary. It describes only
    # what NEXUS inferred from the upload; it never contains file contents.
    project: dict[str, Any] | None = None

    def to_summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "app": self.app_name,
            "status": self.status,
            "mode": self.mode,
            "createdAt": self.created_at,
            "finishedAt": self.finished_at,
            "steps": self.steps,
            "previewUrl": self.preview_url,
            "error": self.error,
            "imageTag": self.image_tag,
            "project": self.project,
        }

    def to_detail(self, since: int = 0) -> dict[str, Any]:
        d = self.to_summary()
        d["logs"] = [
            {"ts": l.ts, "text": l.text, "level": l.level}
            for l in self.logs[since:]
        ]
        d["logCount"] = len(self.logs)
        return d


class JobStore:
    """Thread/async-safe-enough store for a single-process NEXUS backend.

    If you ever run NEXUS with multiple worker processes, this needs to
    move to Redis or similar — job state would otherwise split across
    workers and the UI would see partial history depending on which
    worker served the request.
    """

    def __init__(self, max_jobs: int = 200) -> None:
        self._jobs: dict[str, Job] = {}
        self._order: list[str] = []
        self._max_jobs = max_jobs
        self._lock = asyncio.Lock()
        # Per-job event, so the log-stream endpoint can wait efficiently
        # instead of polling in a tight loop.
        self._events: dict[str, asyncio.Event] = {}

    def create(self, app_name: str, project: dict[str, Any] | None = None) -> Job:
        job_id = f"job-{next(_id_counter)}-{int(time.time())}"
        job = Job(id=job_id, app_name=app_name, project=project)
        self._jobs[job_id] = job
        self._order.append(job_id)
        self._events[job_id] = asyncio.Event()
        if len(self._order) > self._max_jobs:
            oldest = self._order.pop(0)
            self._jobs.pop(oldest, None)
            self._events.pop(oldest, None)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list_recent(self, limit: int = 25) -> list[Job]:
        ids = list(reversed(self._order))[:limit]
        return [self._jobs[i] for i in ids if i in self._jobs]

    def log(self, job_id: str, text: str, level: str = "info") -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.logs.append(LogLine(ts=time.time(), text=text, level=level))
        ev = self._events.get(job_id)
        if ev:
            ev.set()
            ev.clear()

    def set_step(self, job_id: str, step: str, status: StepStatus) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.steps[step] = status
        ev = self._events.get(job_id)
        if ev:
            ev.set()
            ev.clear()

    def set_project(self, job_id: str, project: dict[str, Any]) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.project = project
        ev = self._events.get(job_id)
        if ev:
            ev.set()
            ev.clear()

    def finish(self, job_id: str, status: Status, error: str | None = None) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.status = status
        job.error = error
        job.finished_at = time.time()
        ev = self._events.get(job_id)
        if ev:
            ev.set()
            ev.clear()

    async def wait(self, job_id: str, timeout: float = 25.0) -> None:
        ev = self._events.get(job_id)
        if not ev:
            return
        try:
            await asyncio.wait_for(ev.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass


# Single process-wide store.
job_store = JobStore()
