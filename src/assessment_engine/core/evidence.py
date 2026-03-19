from pydantic import BaseModel, Field


class DimensionMapping(BaseModel):
    dimension_id: str
    direction: int = Field(..., ge=-1, le=1)
    weight: float = Field(..., ge=0, le=1)
    confidence: float = Field(..., ge=0, le=1)


class Evidence(BaseModel):
    id: str
    round_index: int = Field(..., ge=0)
    source_text: str
    evidence_type: str
    normalized_claim: str
    mapped_dimensions: list[DimensionMapping]
    tags: list[str] = Field(default_factory=list)
