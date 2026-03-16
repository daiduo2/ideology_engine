from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal
from datetime import datetime


class AssessmentSession(BaseModel):
    session_id: str
    protocol_id: str
    status: Literal["active", "completed", "abandoned"]
    round_index: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_context: Dict[str, Any] = Field(default_factory=dict)
    conversation_log: List[Dict[str, Any]] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)
