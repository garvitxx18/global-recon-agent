from pydantic import BaseModel, Field


class KeyMapping(BaseModel):
    leftField: str
    rightField: str
    confidence: float | None = None


class FieldMapping(BaseModel):
    leftField: str
    rightField: str
    matchType: str = Field(
        description="EXACT, CASE_INSENSITIVE, DATE_NORMALIZED, or NUMERIC_TOLERANCE",
    )
    confidence: float | None = None
    tolerance: float | None = None


class MappingSuggestion(BaseModel):
    keyMappings: list[KeyMapping] = Field(default_factory=list)
    fieldMappings: list[FieldMapping] = Field(default_factory=list)
    overallConfidence: float | None = None
