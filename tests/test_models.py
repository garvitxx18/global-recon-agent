from app.global_recon.models import FieldMapping, KeyMapping, MappingSuggestion


def test_mapping_suggestion_uses_java_field_names():
    payload = MappingSuggestion(
        keyMappings=[KeyMapping(leftField="tradeId", rightField="Trade_ID", confidence=0.9)],
        fieldMappings=[
            FieldMapping(
                leftField="quantity",
                rightField="qty",
                matchType="NUMERIC_TOLERANCE",
                tolerance=0.0,
            )
        ],
        overallConfidence=0.88,
    ).model_dump()

    assert payload["keyMappings"][0]["leftField"] == "tradeId"
    assert payload["fieldMappings"][0]["matchType"] == "NUMERIC_TOLERANCE"
    assert payload["fieldMappings"][0]["tolerance"] == 0.0
    assert payload["overallConfidence"] == 0.88
