from pydantic import BaseModel, Field
from typing import List, Literal


class Contradiction(BaseModel):
    id: str
    round_index: int = Field(..., ge=0)
    description: str
    related_dimension_ids: List[str]
    evidence_ids: List[str]
    severity: Literal["low", "medium", "high"]
    needs_followup: bool = True
