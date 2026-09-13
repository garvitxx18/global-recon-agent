from __future__ import annotations

import logging
import os
import time
from typing import Any

from ..clients.recon_client import ReconApiError, ReconClient

logger = logging.getLogger(__name__)

TERMINAL_JOB_STATUSES = {"COMPLETED", "FAILED"}


def job_poll_seconds() -> float:
    return float(os.getenv("RECON_JOB_POLL_SECONDS", "2"))


def job_timeout_seconds() -> float:
    return float(os.getenv("RECON_JOB_TIMEOUT_SECONDS", "180"))


def wait_for_job(
    client: ReconClient,
    job_id: str,
    *,
    timeout_seconds: float | None = None,
    poll_seconds: float | None = None,
) -> dict[str, Any]:
    timeout = job_timeout_seconds() if timeout_seconds is None else timeout_seconds
    interval = job_poll_seconds() if poll_seconds is None else poll_seconds
    deadline = time.monotonic() + timeout
    job: dict[str, Any] = {}

    while time.monotonic() < deadline:
        job = client.get_job(job_id)
        status = str(job.get("status") or "").upper()
        logger.info("Job %s status=%s", job_id, status)
        if status in TERMINAL_JOB_STATUSES:
            if status == "FAILED":
                raise ReconApiError(job.get("errorMessage") or f"Job {job_id} failed")
            return job
        time.sleep(max(interval, 0.2))

    raise ReconApiError(
        f"Job {job_id} did not finish within {timeout} seconds",
        body=job,
    )


def discover_and_wait(
    client: ReconClient,
    left_dataset_id: str,
    right_dataset_id: str,
    notes: str | None = None,
) -> dict[str, Any]:
    job = client.discover_plan(left_dataset_id, right_dataset_id, notes)
    completed = wait_for_job(client, job["id"])
    plan_id = completed.get("resultId")
    if not plan_id:
        raise ReconApiError("Discovery completed without a plan id")
    plan = client.get_plan(str(plan_id))
    return {"job": completed, "plan": plan}


def start_run_and_wait(client: ReconClient, recon_plan_id: str) -> dict[str, Any]:
    job = client.start_run(recon_plan_id)
    completed = wait_for_job(client, job["id"])
    run_id = completed.get("resultId")
    if not run_id:
        raise ReconApiError("Run completed without a run id")
    run = client.get_run(str(run_id))
    summary = client.get_run_summary(str(run_id))
    return {"job": completed, "run": run, "summary": summary}
