import httpx
import pytest

from app.global_recon.clients.recon_client import ReconApiError, ReconClient
from app.global_recon.services.recon_workflow import discover_and_wait, wait_for_job


def test_wait_for_job_returns_completed_job():
    states = iter(
        [
            {"id": "job_1", "status": "QUEUED"},
            {"id": "job_1", "status": "RUNNING"},
            {"id": "job_1", "status": "COMPLETED", "resultId": "plan_1"},
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(states))

    client = ReconClient(
        base_url="http://recon.test",
        user_email="tester@company.com",
        transport=httpx.MockTransport(handler),
    )
    job = wait_for_job(client, "job_1", timeout_seconds=2, poll_seconds=0)
    assert job["resultId"] == "plan_1"


def test_wait_for_job_raises_on_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"id": "job_1", "status": "FAILED", "errorMessage": "dataset not profiled"},
        )

    client = ReconClient(
        base_url="http://recon.test",
        user_email="tester@company.com",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ReconApiError, match="dataset not profiled"):
        wait_for_job(client, "job_1", timeout_seconds=1, poll_seconds=0)


def test_discover_and_wait_loads_plan():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/recon-plans/discover":
            return httpx.Response(202, json={"id": "job_1", "status": "QUEUED"})
        if request.url.path == "/api/v1/jobs/job_1":
            return httpx.Response(
                200,
                json={"id": "job_1", "status": "COMPLETED", "resultId": "plan_1"},
            )
        if request.url.path == "/api/v1/recon-plans/plan_1":
            return httpx.Response(200, json={"id": "plan_1", "status": "DRAFT"})
        return httpx.Response(404, json={"message": request.url.path})

    client = ReconClient(
        base_url="http://recon.test",
        user_email="tester@company.com",
        transport=httpx.MockTransport(handler),
    )
    result = discover_and_wait(client, "left_1", "right_1", "notes")
    assert result["plan"]["id"] == "plan_1"
    assert result["job"]["resultId"] == "plan_1"
