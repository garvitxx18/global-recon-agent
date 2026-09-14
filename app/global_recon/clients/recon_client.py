from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

USER_EMAIL_HEADER = "X-User-Email"


class ReconApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class ReconClient:
    """HTTP client for the existing Global Recon Java APIs."""

    def __init__(
        self,
        base_url: str | None = None,
        user_email: str | None = None,
        timeout_seconds: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("RECON_API_BASE_URL") or "http://127.0.0.1:8080").rstrip(
            "/"
        )
        self.user_email = (user_email or os.getenv("RECON_USER_EMAIL") or "").strip()
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        if not self.user_email:
            raise ReconApiError("RECON_USER_EMAIL is not configured")
        headers = {USER_EMAIL_HEADER: self.user_email}
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._client.request(
                method,
                path,
                params=params,
                json=json,
                headers=self._headers(),
            )
        except httpx.HTTPError as exc:
            logger.exception("Recon API request failed: %s %s", method, path)
            raise ReconApiError(f"Recon API call failed: {exc}") from exc

        if response.status_code >= 400:
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = response.text
            message = _error_message(body) or f"HTTP {response.status_code}"
            logger.error("Recon API error %s %s: %s", method, path, message)
            raise ReconApiError(message, status_code=response.status_code, body=body)

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise ReconApiError("Recon API returned non-JSON") from exc

    def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/datasets/{dataset_id}")

    def get_dataset_profile(self, dataset_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/datasets/{dataset_id}/profile")

    def discover_plan(
        self, left_dataset_id: str, right_dataset_id: str, notes: str | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "leftDatasetId": left_dataset_id,
            "rightDatasetId": right_dataset_id,
        }
        if notes:
            payload["notes"] = notes
        return self._request("POST", "/api/v1/recon-plans/discover", json=payload)

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/jobs/{job_id}")

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/recon-plans/{plan_id}")

    def update_plan(self, plan_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", f"/api/v1/recon-plans/{plan_id}", json=payload)

    def approve_plan(self, plan_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/recon-plans/{plan_id}/approve")

    def start_run(self, recon_plan_id: str) -> dict[str, Any]:
        return self._request("POST", "/api/v1/recon-runs", json={"reconPlanId": recon_plan_id})

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/recon-runs/{run_id}")

    def get_run_results(
        self,
        run_id: str,
        *,
        status: str | None = None,
        page: int = 0,
        size: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "size": size}
        if status:
            params["status"] = status
        return self._request("GET", f"/api/v1/recon-runs/{run_id}/results", params=params)


def _error_message(body: Any) -> str | None:
    if isinstance(body, dict):
        for key in ("message", "error", "detail"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value
    if isinstance(body, str) and body.strip():
        return body.strip()
    return None


_CLIENT: ReconClient | None = None


def get_recon_client() -> ReconClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = ReconClient()
    return _CLIENT


def set_recon_client(client: ReconClient | None) -> None:
    global _CLIENT
    _CLIENT = client
