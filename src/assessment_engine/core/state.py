from typing import Literal, Optional

from pydantic import BaseModel, Field


class DimensionState(BaseModel):
    score: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.0, ge=0, le=1)
    evidence_count: int = Field(default=0, ge=0)
    last_updated_at_round: int = Field(default=0, ge=0)


class Coverage(BaseModel):
    model_config = {"extra": "allow"}


class NextTarget(BaseModel):
    type: Literal["coverage_gap", "dimension_uncertainty", "contradiction", "ambiguity"]
    target: str
    reason: Optional[str] = None
    recommended_strategy: Optional[str] = None


class TerminationStatus(BaseModel):
    eligible: bool = False
    reasons: list[str] = Field(default_factory=list)


class AssessmentState(BaseModel):
    dimensions: dict[str, DimensionState]
    coverage: Coverage = Field(default_factory=Coverage)
    evidence_ids: list[str] = Field(default_factory=list)
    contradiction_ids: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    recommended_next_target: Optional[NextTarget] = None
    termination: TerminationStatus = Field(default_factory=TerminationStatus)
