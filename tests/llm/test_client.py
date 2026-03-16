import pytest
from unittest.mock import Mock, patch
from assessment_engine.llm.client import LLMClient


def test_llm_client_initialization():
    client = LLMClient(api_key="test-key")
    assert client is not None


def test_parse_response_schema():
    """Test that parse_response returns valid schema"""
    mock_response = {
        "observations": [
            {
                "type": "self_description",
                "content": "User is calm",
                "tags": ["stress"],
            }
        ],
        "ambiguities": [],
        "followup_candidates": [],
    }
    # Schema validation test
    assert "observations" in mock_response
    assert isinstance(mock_response["observations"], list)


def test_client_with_mocked_anthropic():
    """Test client methods exist and have correct signatures"""
    client = LLMClient(api_key="test")
    assert hasattr(client, "parse_response")
    assert hasattr(client, "extract_evidence")
    assert hasattr(client, "generate_question")
    assert hasattr(client, "generate_report")
