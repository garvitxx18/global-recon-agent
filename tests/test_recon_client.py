import json

import httpx
import pytest

from app.global_recon.clients.recon_client import ReconApiError, ReconClient


def _client(handler) -> ReconClient:
    transport = httpx.MockTransport(handler)
    return ReconClient(
        base_url="http://recon.test",
        user_email="tester@company.com",
        transport=transport,
    )


def test_get_dataset_sends_user_email_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-User-Email"] == "tester@company.com"
        assert request.url.path == "/api/v1/datasets/ds_1"
        return httpx.Response(200, json={"id": "ds_1", "status": "PROFILED"})

    client = _client(handler)
    assert client.get_dataset("ds_1")["id"] == "ds_1"


def test_discover_plan_posts_java_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v1/recon-plans/discover"
        body = json.loads(request.content)
        assert body == {
            "leftDatasetId": "left_1",
            "rightDatasetId": "right_1",
            "notes": "only tradeList",
        }
        return httpx.Response(202, json={"id": "job_1", "status": "QUEUED"})

    client = _client(handler)
    job = client.discover_plan("left_1", "right_1", "only tradeList")
    assert job["id"] == "job_1"


def test_api_error_uses_message_from_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Recon plan not found: plan_9"})

    client = _client(handler)
    with pytest.raises(ReconApiError, match="Recon plan not found: plan_9"):
        client.get_plan("plan_9")


def test_missing_email_fails_before_request():
    client = ReconClient(base_url="http://recon.test", user_email="")
    with pytest.raises(ReconApiError, match="RECON_USER_EMAIL"):
        client.get_dataset("ds_1")
