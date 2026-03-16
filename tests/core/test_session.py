import pytest
from datetime import datetime
from assessment_engine.core.session import AssessmentSession


class TestAssessmentSession:
    def test_session_creation(self):
        session = AssessmentSession(
            session_id="session_123",
            protocol_id="protocol_456",
            status="active",
        )
        assert session.session_id == "session_123"
        assert session.protocol_id == "protocol_456"
        assert session.status == "active"
        assert session.round_index == 0
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
        assert session.user_context == {}
        assert session.conversation_log == []
        assert session.state == {}

    def test_session_with_round_index(self):
        session = AssessmentSession(
            session_id="session_123",
            protocol_id="protocol_456",
            status="active",
            round_index=5,
        )
        assert session.round_index == 5

    def test_session_completed_status(self):
        session = AssessmentSession(
            session_id="session_123",
            protocol_id="protocol_456",
            status="completed",
        )
        assert session.status == "completed"

    def test_session_abandoned_status(self):
        session = AssessmentSession(
            session_id="session_123",
            protocol_id="protocol_456",
            status="abandoned",
        )
        assert session.status == "abandoned"

    def test_validation_invalid_status(self):
        with pytest.raises(ValueError):
            AssessmentSession(
                session_id="session_123",
                protocol_id="protocol_456",
                status="invalid_status",
            )

    def test_validation_round_index_ge_zero(self):
        with pytest.raises(ValueError):
            AssessmentSession(
                session_id="session_123",
                protocol_id="protocol_456",
                status="active",
                round_index=-1,
            )

    def test_session_with_user_context(self):
        session = AssessmentSession(
            session_id="session_123",
            protocol_id="protocol_456",
            status="active",
            user_context={"user_id": "user_789", "language": "en"},
        )
        assert session.user_context == {"user_id": "user_789", "language": "en"}

    def test_session_with_conversation_log(self):
        log = [
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Hi there"},
        ]
        session = AssessmentSession(
            session_id="session_123",
            protocol_id="protocol_456",
            status="active",
            conversation_log=log,
        )
        assert session.conversation_log == log

    def test_session_with_state(self):
        state = {"dimensions": {"dim1": {"score": 0.8}}}
        session = AssessmentSession(
            session_id="session_123",
            protocol_id="protocol_456",
            status="active",
            state=state,
        )
        assert session.state == state

    def test_session_custom_timestamps(self):
        created = datetime(2024, 1, 1, 12, 0, 0)
        updated = datetime(2024, 1, 1, 13, 0, 0)
        session = AssessmentSession(
            session_id="session_123",
            protocol_id="protocol_456",
            status="active",
            created_at=created,
            updated_at=updated,
        )
        assert session.created_at == created
        assert session.updated_at == updated
