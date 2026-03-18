"""API integration tests."""
import pytest
from fastapi.testclient import TestClient

from assessment_engine.api import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestHealth:
    """Health check endpoint tests."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestProtocols:
    """Protocol endpoint tests."""

    def test_list_protocols(self, client):
        """Test listing protocols."""
        response = client.get("/protocols")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_protocol_not_found(self, client):
        """Test getting non-existent protocol."""
        response = client.get("/protocols/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_create_protocol_validation_error(self, client):
        """Test protocol creation with invalid data."""
        response = client.post("/protocols", json={})
        assert response.status_code == 422


class TestSessions:
    """Session endpoint tests."""

    def test_get_session_not_found(self, client):
        """Test getting non-existent session."""
        response = client.get("/sessions/nonexistent")
        assert response.status_code == 404

    def test_create_session_validation_error(self, client):
        """Test session creation with invalid data."""
        response = client.post("/sessions", json={})
        assert response.status_code == 422

    def test_submit_answer_validation_error(self, client):
        """Test answer submission with invalid data."""
        response = client.post("/sessions/test-session/answers", json={})
        assert response.status_code == 422

    def test_get_next_question_not_found(self, client):
        """Test getting question for non-existent session."""
        response = client.get("/sessions/nonexistent/next-question")
        assert response.status_code == 404

    def test_finalize_not_found(self, client):
        """Test finalizing non-existent session."""
        response = client.post("/sessions/nonexistent/finalize")
        assert response.status_code == 404

    def test_get_report_not_found(self, client):
        """Test getting report for non-existent session."""
        response = client.get("/sessions/nonexistent/report")
        assert response.status_code == 404
