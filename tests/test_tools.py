from app.global_recon.clients.recon_client import ReconApiError, set_recon_client
from app.global_recon.tools import get_dataset, update_recon_plan


class FakeClient:
    def get_dataset(self, dataset_id: str):
        if dataset_id == "missing":
            raise ReconApiError("Dataset not found")
        return {"id": dataset_id, "status": "PROFILED"}

    def update_plan(self, plan_id: str, payload: dict):
        return {"id": plan_id, "payload": payload}


def setup_function():
    set_recon_client(FakeClient())


def teardown_function():
    set_recon_client(None)


def test_get_dataset_wraps_success():
    result = get_dataset("ds_1")
    assert result["success"] is True
    assert result["dataset"]["id"] == "ds_1"


def test_get_dataset_wraps_failure():
    result = get_dataset("missing")
    assert result["success"] is False
    assert "Dataset not found" in result["error"]


def test_update_recon_plan_validates_mappings():
    result = update_recon_plan(
        plan_id="plan_1",
        key_mappings=[{"left_field": "tradeId", "right_field": "tradeId"}],
        field_mappings=[
            {
                "left_field": "qty",
                "right_field": "quantity",
                "match_type": "NUMERIC_TOLERANCE",
                "tolerance": 0,
            }
        ],
    )
    assert result["success"] is True
    assert result["plan"]["payload"]["keyMappings"][0]["leftField"] == "tradeId"
