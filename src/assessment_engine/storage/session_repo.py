import json
from pathlib import Path
from typing import List, Optional
from assessment_engine.core.session import AssessmentSession


class SessionRepository:
    """File-based repository for assessment sessions."""

    def __init__(self, base_path: str = "sessions"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, session_id: str) -> Path:
        """Get file path for a session."""
        return self.base_path / f"{session_id}.json"

    def save(self, session: AssessmentSession) -> None:
        """Save session to file."""
        file_path = self._get_file_path(session.session_id)

        # Update timestamp
        from datetime import datetime
        session.updated_at = datetime.utcnow()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(), f, indent=2, default=str)

    def load(self, session_id: str) -> Optional[AssessmentSession]:
        """Load session from file."""
        file_path = self._get_file_path(session_id)

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return AssessmentSession.model_validate(data)

    def list_all(self) -> List[AssessmentSession]:
        """List all sessions."""
        sessions = []

        for file_path in self.base_path.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append(AssessmentSession.model_validate(data))

        return sessions

    def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return self._get_file_path(session_id).exists()

    def delete(self, session_id: str) -> None:
        """Delete a session."""
        file_path = self._get_file_path(session_id)
        if file_path.exists():
            file_path.unlink()
