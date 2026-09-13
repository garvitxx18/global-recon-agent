from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KeyMapping(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    left_field: str = Field(description="Exact left dataset field name", alias="leftField")
    right_field: str = Field(description="Exact right dataset field name", alias="rightField")
    confidence: float | None = None


class FieldMapping(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    left_field: str = Field(description="Exact left dataset field name", alias="leftField")
    right_field: str = Field(description="Exact right dataset field name", alias="rightField")
    match_type: str = Field(
        description="EXACT, CASE_INSENSITIVE, DATE_NORMALIZED, or NUMERIC_TOLERANCE",
        alias="matchType",
    )
    confidence: float | None = None
    tolerance: float | None = None
    included: bool = True


class UpdatePlanInput(BaseModel):
    key_mappings: list[KeyMapping] = Field(default_factory=list)
    field_mappings: list[FieldMapping] = Field(default_factory=list)
    left_dataset_id: str | None = None
    right_dataset_id: str | None = None
    user_notes: str | None = None
    approve: bool | None = None

    def to_api_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "keyMappings": [
                {
                    "leftField": item.left_field,
                    "rightField": item.right_field,
                    "confidence": item.confidence,
                }
                for item in self.key_mappings
            ],
            "fieldMappings": [
                {
                    "leftField": item.left_field,
                    "rightField": item.right_field,
                    "matchType": item.match_type,
                    "confidence": item.confidence,
                    "tolerance": item.tolerance,
                    "included": item.included,
                }
                for item in self.field_mappings
            ],
        }
        if self.left_dataset_id:
            payload["leftDatasetId"] = self.left_dataset_id
        if self.right_dataset_id:
            payload["rightDatasetId"] = self.right_dataset_id
        if self.user_notes is not None:
            payload["userNotes"] = self.user_notes
        if self.approve is not None:
            payload["approve"] = self.approve
        return payload
