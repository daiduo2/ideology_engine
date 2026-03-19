"""Pydantic models for API requests and responses."""

from typing import Any, Optional

from pydantic import BaseModel, Field


# Protocol models
class ProtocolResponse(BaseModel):
    """Protocol response model."""

    id: str
    name: str
    description: str
    dimensions: list[dict[str, Any]]
    coverage_targets: Optional[list[str]] = None
    stopping_rules: dict[str, Any]


class CreateProtocolRequest(BaseModel):
    """Create protocol request."""

    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1)
    dimensions: list[dict[str, Any]]
    coverage_targets: Optional[list[str]] = None
    question_strategies: Optional[list[str]] = None
    stopping_rules: dict[str, Any]
    report_template: Optional[str] = "default"


# Session models
class StartSessionRequest(BaseModel):
    """Start session request."""

    protocol_id: str
    user_context: Optional[dict[str, Any]] = None


class SessionResponse(BaseModel):
    """Session response."""

    session_id: str
    protocol_id: str
    status: str
    round_index: int
    state: dict[str, Any]
    created_at: str
    updated_at: str


class SubmitAnswerRequest(BaseModel):
    """Submit answer request."""

    answer: str = Field(..., min_length=1, max_length=10000)


class SubmitAnswerResponse(BaseModel):
    """Submit answer response."""

    status: str
    round_index: int
    observations: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    state: dict[str, Any]
    is_complete: bool


class QuestionResponse(BaseModel):
    """Question response."""

    question: str
    round_index: int
    strategy: Optional[str] = None
    target_dimension: Optional[str] = None


class FinalizeResponse(BaseModel):
    """Finalize response."""

    session_id: str
    status: str
    report: dict[str, Any]
    final_state: dict[str, Any]


class ReportResponse(BaseModel):
    """Report response."""

    session_id: str
    protocol_id: str
    status: str
    report: dict[str, Any]
    created_at: str
    completed_at: Optional[str] = None


# Error models
class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    code: str
