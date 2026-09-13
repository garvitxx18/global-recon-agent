from app.global_recon.models import FieldMapping, KeyMapping, UpdatePlanInput


def test_update_plan_payload_uses_java_field_names():
    payload = UpdatePlanInput(
        key_mappings=[KeyMapping(left_field="tradeId", right_field="Trade_ID", confidence=0.9)],
        field_mappings=[
            FieldMapping(
                left_field="quantity",
                right_field="qty",
                match_type="NUMERIC_TOLERANCE",
                tolerance=0.0,
            )
        ],
        user_notes="trades only",
        approve=False,
    ).to_api_payload()

    assert payload["keyMappings"][0]["leftField"] == "tradeId"
    assert payload["fieldMappings"][0]["matchType"] == "NUMERIC_TOLERANCE"
    assert payload["fieldMappings"][0]["tolerance"] == 0.0
    assert payload["userNotes"] == "trades only"
    assert payload["approve"] is False
