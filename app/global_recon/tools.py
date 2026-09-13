from __future__ import annotations

import logging
from typing import Any

from .clients.recon_client import ReconApiError, get_recon_client, read_upload_source
from .models import FieldMapping, KeyMapping, UpdatePlanInput
from .services.recon_workflow import discover_and_wait, start_run_and_wait, wait_for_job

logger = logging.getLogger(__name__)


def _ok(data: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"success": True}
    if data:
        result.update(data)
    return result


def _fail(exc: Exception) -> dict[str, Any]:
    logger.exception("Recon tool failed")
    return {"success": False, "error": str(exc)}


def upload_dataset(
    file_path: str | None = None,
    file_url: str | None = None,
    name: str | None = None,
    notes: str | None = None,
    record_path: str | None = None,
) -> dict[str, Any]:
    """Upload a CSV, JSON, or XLSX file to Global Recon.

    Provide either a local file_path the agent can read or an http(s) file_url.
    Use record_path when the JSON has a nested list, for example tradeList.

    Args:
        file_path: Local filesystem path to the dataset file.
        file_url: HTTP or HTTPS URL of the dataset file.
        name: Optional display name.
        notes: Optional ingest notes, for example ignore header and use tradeList.
        record_path: Optional JSON path to each record, for example tradeList.

    Returns:
        The created dataset, including dataset id, status, and row count.
    """
    try:
        file_name, file_bytes = read_upload_source(file_path, file_url)
        dataset = get_recon_client().upload_dataset(
            file_name,
            file_bytes,
            name=name,
            notes=notes,
            record_path=record_path,
        )
        return _ok({"dataset": dataset})
    except (ReconApiError, OSError) as exc:
        return _fail(exc)


def get_dataset(dataset_id: str) -> dict[str, Any]:
    """Fetch dataset metadata by id.

    Args:
        dataset_id: Dataset identifier returned by upload_dataset.

    Returns:
        Dataset name, format, status, row count, record path, and notes.
    """
    try:
        return _ok({"dataset": get_recon_client().get_dataset(dataset_id)})
    except ReconApiError as exc:
        return _fail(exc)


def get_dataset_profile(dataset_id: str) -> dict[str, Any]:
    """Fetch column profiles used to choose keys and compare fields.

    Args:
        dataset_id: Dataset identifier.

    Returns:
        Row count and each column's name, type, unique ratio, nulls, and samples.
    """
    try:
        return _ok({"profile": get_recon_client().get_dataset_profile(dataset_id)})
    except ReconApiError as exc:
        return _fail(exc)


def get_dataset_records(dataset_id: str, page: int = 0, size: int = 5) -> dict[str, Any]:
    """Fetch a small page of ingested records for inspection.

    Args:
        dataset_id: Dataset identifier.
        page: Zero-based page number.
        size: Page size. Keep this small.

    Returns:
        A Spring page of normalized JSON records.
    """
    try:
        return _ok(
            {
                "records": get_recon_client().get_dataset_records(
                    dataset_id, page=page, size=min(size, 20)
                )
            }
        )
    except ReconApiError as exc:
        return _fail(exc)


def discover_recon_plan(
    left_dataset_id: str,
    right_dataset_id: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """Queue mapping discovery and wait for the draft recon plan.

    The Java service may call an LLM for suggestions, then validates field names.
    This tool does not invent mappings itself.

    Args:
        left_dataset_id: Left dataset id.
        right_dataset_id: Right dataset id.
        notes: Optional user comparison notes.

    Returns:
        The completed discovery job and the draft recon plan.
    """
    try:
        return _ok(
            discover_and_wait(
                get_recon_client(),
                left_dataset_id,
                right_dataset_id,
                notes,
            )
        )
    except ReconApiError as exc:
        return _fail(exc)


def get_job(job_id: str) -> dict[str, Any]:
    """Get an async job by id.

    Args:
        job_id: Job identifier from discover or start run.

    Returns:
        Job type, status, resultId, and errorMessage when failed.
    """
    try:
        return _ok({"job": get_recon_client().get_job(job_id)})
    except ReconApiError as exc:
        return _fail(exc)


def wait_for_recon_job(job_id: str) -> dict[str, Any]:
    """Poll an async job until it completes or fails.

    Args:
        job_id: Job identifier.

    Returns:
        The terminal job payload. resultId is the plan id or run id.
    """
    try:
        return _ok({"job": wait_for_job(get_recon_client(), job_id)})
    except ReconApiError as exc:
        return _fail(exc)


def get_recon_plan(plan_id: str) -> dict[str, Any]:
    """Fetch a recon plan, including key and field mappings.

    Args:
        plan_id: Recon plan identifier.

    Returns:
        Plan status, notes, warnings, keyMappings, and fieldMappings.
    """
    try:
        return _ok({"plan": get_recon_client().get_plan(plan_id)})
    except ReconApiError as exc:
        return _fail(exc)


def update_recon_plan(
    plan_id: str,
    key_mappings: list[dict[str, Any]],
    field_mappings: list[dict[str, Any]],
    left_dataset_id: str | None = None,
    right_dataset_id: str | None = None,
    user_notes: str | None = None,
    approve: bool | None = None,
) -> dict[str, Any]:
    """Replace the mappings on a recon plan.

    Field names must match the dataset profiles exactly. Identifier keys should
    stay EXACT. Numeric fields should use NUMERIC_TOLERANCE.

    Args:
        plan_id: Recon plan identifier.
        key_mappings: Join keys. Each item needs left_field and right_field.
        field_mappings: Compare fields. Each item needs left_field, right_field,
            and match_type.
        left_dataset_id: Optional left dataset id if changing files.
        right_dataset_id: Optional right dataset id if changing files.
        user_notes: Optional notes stored on the plan.
        approve: Set true only after the user confirmed the mapping.

    Returns:
        The updated recon plan.
    """
    try:
        update = UpdatePlanInput(
            key_mappings=[KeyMapping.model_validate(item) for item in key_mappings],
            field_mappings=[FieldMapping.model_validate(item) for item in field_mappings],
            left_dataset_id=left_dataset_id,
            right_dataset_id=right_dataset_id,
            user_notes=user_notes,
            approve=approve,
        )
        plan = get_recon_client().update_plan(plan_id, update.to_api_payload())
        return _ok({"plan": plan})
    except (ReconApiError, ValueError) as exc:
        return _fail(exc)


def approve_recon_plan(plan_id: str) -> dict[str, Any]:
    """Approve a recon plan so a run can start.

    Only call this after the user confirmed the mapping, or when the mapping is
    an obvious high-confidence key and the user asked to run.

    Args:
        plan_id: Recon plan identifier.

    Returns:
        The approved recon plan.
    """
    try:
        return _ok({"plan": get_recon_client().approve_plan(plan_id)})
    except ReconApiError as exc:
        return _fail(exc)


def start_recon_run(recon_plan_id: str) -> dict[str, Any]:
    """Start reconciliation for an approved plan and wait for the run.

    Java performs the match. This tool only starts the job and returns counts.

    Args:
        recon_plan_id: Approved recon plan identifier.

    Returns:
        The job, run, and summary counts.
    """
    try:
        return _ok(start_run_and_wait(get_recon_client(), recon_plan_id))
    except ReconApiError as exc:
        return _fail(exc)


def get_recon_run(run_id: str) -> dict[str, Any]:
    """Fetch a recon run, including progress and counts.

    Args:
        run_id: Recon run identifier.

    Returns:
        Run status and match / break / only-in-left / only-in-right counts.
    """
    try:
        return _ok({"run": get_recon_client().get_run(run_id)})
    except ReconApiError as exc:
        return _fail(exc)


def get_recon_summary(run_id: str) -> dict[str, Any]:
    """Fetch summary counts for a completed run.

    Args:
        run_id: Recon run identifier.

    Returns:
        Status counts from the Java service.
    """
    try:
        return _ok({"summary": get_recon_client().get_run_summary(run_id)})
    except ReconApiError as exc:
        return _fail(exc)


def get_recon_results(
    run_id: str,
    status: str | None = "BREAK",
    page: int = 0,
    size: int = 20,
) -> dict[str, Any]:
    """Fetch a page of recon results.

    Status values: MATCHED, BREAK, ONLY_IN_LEFT, ONLY_IN_RIGHT, DUPLICATE_LEFT,
    DUPLICATE_RIGHT, AMBIGUOUS.

    Args:
        run_id: Recon run identifier.
        status: Optional status filter. Defaults to BREAK.
        page: Zero-based page number.
        size: Page size. Keep this small.

    Returns:
        A Spring page of results with keys, payloads, and field differences.
    """
    try:
        return _ok(
            {
                "results": get_recon_client().get_run_results(
                    run_id,
                    status=status,
                    page=page,
                    size=min(size, 50),
                )
            }
        )
    except ReconApiError as exc:
        return _fail(exc)


def save_comparison(run_id: str, name: str) -> dict[str, Any]:
    """Save a completed run as a named comparison.

    Args:
        run_id: Completed recon run identifier.
        name: Display name, for example Daily trades vs settlement.

    Returns:
        The saved comparison summary.
    """
    try:
        return _ok({"comparison": get_recon_client().save_comparison(run_id, name)})
    except ReconApiError as exc:
        return _fail(exc)


def list_comparisons(saved: bool | None = True, page: int = 0, size: int = 20) -> dict[str, Any]:
    """List recent or saved comparisons for the current user.

    Args:
        saved: True for named saves, False for unsaved runs, omit for both.
        page: Zero-based page number.
        size: Page size.

    Returns:
        A Spring page of comparison summaries.
    """
    try:
        return _ok(
            {
                "comparisons": get_recon_client().list_comparisons(
                    saved=saved, page=page, size=min(size, 50)
                )
            }
        )
    except ReconApiError as exc:
        return _fail(exc)
