from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._client.request(
                method,
                path,
                params=params,
                json=json,
                files=files,
                data=data,
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

    def upload_dataset(
        self,
        file_name: str,
        file_bytes: bytes,
        *,
        name: str | None = None,
        notes: str | None = None,
        record_path: str | None = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if name:
            data["name"] = name
        if notes:
            data["notes"] = notes
        if record_path:
            data["recordPath"] = record_path
        return self._request(
            "POST",
            "/api/v1/datasets",
            files={"file": (file_name, file_bytes)},
            data=data or None,
        )

    def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/datasets/{dataset_id}")

    def get_dataset_profile(self, dataset_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/datasets/{dataset_id}/profile")

    def get_dataset_records(
        self, dataset_id: str, *, page: int = 0, size: int = 5
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/api/v1/datasets/{dataset_id}/records",
            params={"page": page, "size": size},
        )

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

    def get_run_summary(self, run_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/recon-runs/{run_id}/summary")

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

    def save_comparison(self, run_id: str, name: str) -> dict[str, Any]:
        return self._request("POST", "/api/v1/comparisons", json={"runId": run_id, "name": name})

    def list_comparisons(
        self, *, saved: bool | None = None, page: int = 0, size: int = 20
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "size": size}
        if saved is not None:
            params["saved"] = saved
        return self._request("GET", "/api/v1/comparisons", params=params)


def read_upload_source(file_path: str | None = None, file_url: str | None = None) -> tuple[str, bytes]:
    if file_path:
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise ReconApiError(f"File not found: {file_path}")
        return path.name, path.read_bytes()

    if file_url:
        parsed = urlparse(file_url)
        if parsed.scheme not in {"http", "https"}:
            raise ReconApiError("file_url must be http or https")
        try:
            response = httpx.get(file_url, timeout=60.0, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ReconApiError(f"Failed to download file_url: {exc}") from exc
        name = Path(parsed.path).name or "dataset"
        return name, response.content

    raise ReconApiError("file_path or file_url is required")


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
