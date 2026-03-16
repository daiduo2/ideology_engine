from pydantic import BaseModel, Field
from typing import List


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
    mapped_dimensions: List[DimensionMapping]
    tags: List[str] = Field(default_factory=list)
