from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AssessmentSession(BaseModel):
    session_id: str
    protocol_id: str
    status: Literal["active", "completed", "abandoned"]
    round_index: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_context: dict[str, Any] = Field(default_factory=dict)
    conversation_log: list[dict[str, Any]] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
