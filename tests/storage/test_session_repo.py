import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from assessment_engine.core.session import AssessmentSession
from assessment_engine.storage.session_repo import SessionRepository


class TestSessionRepository:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)

    @pytest.fixture
    def repo(self, temp_dir):
        """Create a SessionRepository with temp directory."""
        return SessionRepository(base_path=temp_dir)

    @pytest.fixture
    def sample_session(self):
        """Create a sample session for testing."""
        return AssessmentSession(
            session_id="test_session_123",
            protocol_id="protocol_456",
            status="active",
            round_index=3,
            user_context={"user_id": "user_789"},
            conversation_log=[{"role": "assistant", "content": "Hello"}],
            state={"dimensions": {"dim1": {"score": 0.8}}},
        )

    def test_init_creates_directory(self, temp_dir):
        """Test that initialization creates the base directory."""
        new_dir = Path(temp_dir) / "new_sessions"
        repo = SessionRepository(base_path=str(new_dir))
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_get_file_path(self, repo):
        """Test file path generation."""
        path = repo._get_file_path("session_abc")
        assert path.name == "session_abc.json"
        assert path.suffix == ".json"

    def test_save_session(self, repo, sample_session):
        """Test saving a session."""
        repo.save(sample_session)

        file_path = repo._get_file_path(sample_session.session_id)
        assert file_path.exists()

    def test_save_updates_timestamp(self, repo, sample_session):
        """Test that save updates the updated_at timestamp."""
        original_updated_at = sample_session.updated_at

        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.01)

        repo.save(sample_session)

        assert sample_session.updated_at > original_updated_at

    def test_load_session(self, repo, sample_session):
        """Test loading a saved session."""
        repo.save(sample_session)

        loaded = repo.load(sample_session.session_id)

        assert loaded is not None
        assert loaded.session_id == sample_session.session_id
        assert loaded.protocol_id == sample_session.protocol_id
        assert loaded.status == sample_session.status
        assert loaded.round_index == sample_session.round_index
        assert loaded.user_context == sample_session.user_context
        assert loaded.conversation_log == sample_session.conversation_log
        assert loaded.state == sample_session.state

    def test_load_nonexistent_session(self, repo):
        """Test loading a session that doesn't exist."""
        loaded = repo.load("nonexistent_session")
        assert loaded is None

    def test_list_all_empty(self, repo):
        """Test listing sessions when none exist."""
        sessions = repo.list_all()
        assert sessions == []

    def test_list_all_multiple_sessions(self, repo):
        """Test listing multiple sessions."""
        session1 = AssessmentSession(
            session_id="session_1",
            protocol_id="protocol_1",
            status="active",
        )
        session2 = AssessmentSession(
            session_id="session_2",
            protocol_id="protocol_2",
            status="completed",
        )

        repo.save(session1)
        repo.save(session2)

        sessions = repo.list_all()

        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert session_ids == {"session_1", "session_2"}

    def test_exists_true(self, repo, sample_session):
        """Test exists returns True for existing session."""
        repo.save(sample_session)
        assert repo.exists(sample_session.session_id) is True

    def test_exists_false(self, repo):
        """Test exists returns False for non-existent session."""
        assert repo.exists("nonexistent_session") is False

    def test_delete_session(self, repo, sample_session):
        """Test deleting a session."""
        repo.save(sample_session)
        assert repo.exists(sample_session.session_id) is True

        repo.delete(sample_session.session_id)
        assert repo.exists(sample_session.session_id) is False

    def test_delete_nonexistent_session(self, repo):
        """Test deleting a session that doesn't exist (should not raise)."""
        # Should not raise an exception
        repo.delete("nonexistent_session")

    def test_round_trip_with_complex_state(self, repo):
        """Test saving and loading a session with complex state."""
        complex_session = AssessmentSession(
            session_id="complex_session",
            protocol_id="protocol_complex",
            status="active",
            round_index=10,
            user_context={
                "nested": {"deep": {"value": 123}},
                "list": [1, 2, 3],
                "string": "test",
                "number": 42,
                "boolean": True,
            },
            conversation_log=[
                {"role": "assistant", "content": "Hello", "timestamp": "2024-01-01T00:00:00"},
                {"role": "user", "content": "Hi", "metadata": {"confidence": 0.9}},
            ],
            state={
                "dimensions": {
                    "dim1": {"score": 0.8, "confidence": 0.9},
                    "dim2": {"score": 0.3, "confidence": 0.7},
                },
                "coverage": {"target1": True, "target2": False},
            },
        )

        repo.save(complex_session)
        loaded = repo.load(complex_session.session_id)

        assert loaded is not None
        assert loaded.user_context == complex_session.user_context
        assert loaded.conversation_log == complex_session.conversation_log
        assert loaded.state == complex_session.state

    def test_session_timestamps_preserved(self, repo):
        """Test that created_at timestamp is preserved on load."""
        created = datetime(2024, 1, 15, 10, 30, 0)
        session = AssessmentSession(
            session_id="timestamp_session",
            protocol_id="protocol_1",
            status="active",
            created_at=created,
            updated_at=created,
        )

        repo.save(session)
        loaded = repo.load(session.session_id)

        assert loaded is not None
        assert loaded.created_at.year == 2024
        assert loaded.created_at.month == 1
        assert loaded.created_at.day == 15
