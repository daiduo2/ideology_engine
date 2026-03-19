from typing import Literal

from pydantic import BaseModel, Field


class Contradiction(BaseModel):
    id: str
    round_index: int = Field(..., ge=0)
    description: str
    related_dimension_ids: list[str]
    evidence_ids: list[str]
    severity: Literal["low", "medium", "high"]
    needs_followup: bool = True
