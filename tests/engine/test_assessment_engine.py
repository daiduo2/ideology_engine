"""Tests for AssessmentEngine."""
import pytest
from assessment_engine.core.protocol import AssessmentProtocol, Dimension, Scale, StoppingRules
from assessment_engine.core.session import AssessmentSession
from assessment_engine.core.state import AssessmentState, DimensionState, Coverage
from assessment_engine.engine.assessment_engine import AssessmentEngine


def test_engine_initialization():
    protocol = AssessmentProtocol(
        id="test",
        name="Test",
        description="Test",
        dimensions=[Dimension(id="dim_1", name="Test", description="Test", scale=Scale())],
        coverage_targets=["self_description"],
        question_strategies=["ask_recent_example"],
        stopping_rules=StoppingRules(min_rounds=2, max_rounds=5, target_confidence=0.5, min_coverage_ratio=0.5),
        report_template="test",
    )

    engine = AssessmentEngine(protocol=protocol)
    assert engine.protocol == protocol
    assert engine.session is None


def test_start_session():
    protocol = AssessmentProtocol(
        id="test",
        name="Test",
        description="Test",
        dimensions=[Dimension(id="dim_1", name="Test", description="Test", scale=Scale())],
        coverage_targets=["self_description"],
        question_strategies=["ask_recent_example"],
        stopping_rules=StoppingRules(min_rounds=2, max_rounds=5, target_confidence=0.5, min_coverage_ratio=0.5),
        report_template="test",
    )

    engine = AssessmentEngine(protocol=protocol)
    session = engine.start_session()

    assert session is not None
    assert session.protocol_id == "test"
    assert session.status == "active"
    assert session.round_index == 0
    assert "dim_1" in session.state.get("dimensions", {})


def test_get_next_question_before_start():
    protocol = AssessmentProtocol(
        id="test",
        name="Test",
        description="Test",
        dimensions=[],
        coverage_targets=[],
        question_strategies=[],
        stopping_rules=StoppingRules(min_rounds=1, max_rounds=5, target_confidence=0.5, min_coverage_ratio=0.5),
        report_template="test",
    )

    engine = AssessmentEngine(protocol=protocol)

    with pytest.raises(RuntimeError, match="No active session"):
        engine.get_next_question()


def test_full_pipeline_without_llm():
    """Test complete pipeline without LLM calls."""
    protocol = AssessmentProtocol(
        id="test_pipeline",
        name="Test Pipeline",
        description="Integration test",
        dimensions=[
            Dimension(id="dim_1", name="Dimension 1", description="Test", scale=Scale()),
        ],
        coverage_targets=["self_description"],
        question_strategies=["ask_recent_example"],
        stopping_rules=StoppingRules(min_rounds=2, max_rounds=5, target_confidence=0.5, min_coverage_ratio=0.5),
        report_template="test",
    )

    engine = AssessmentEngine(protocol=protocol, llm_client=None)

    # Start session
    session = engine.start_session()
    assert session.status == "active"

    # Get first question
    q1 = engine.get_next_question()
    assert q1["status"] == "active"
    assert "question" in q1

    # Submit answer
    result1 = engine.submit_answer("I am a calm person under pressure.")
    assert result1["status"] == "active"

    # Get second question
    q2 = engine.get_next_question()
    assert q2["round_index"] == 1

    # Submit second answer
    result2 = engine.submit_answer("I prefer planning ahead rather than being spontaneous.")

    # Check state has been updated
    assert session.round_index == 2

    # Finalize
    final = engine.finalize()
    assert final["status"] == "completed"
    assert "report" in final


def test_pipeline_reaches_max_rounds():
    """Test that pipeline terminates at max_rounds."""
    protocol = AssessmentProtocol(
        id="test_max_rounds",
        name="Test Max Rounds",
        description="Test",
        dimensions=[Dimension(id="dim_1", name="Test", description="Test", scale=Scale())],
        coverage_targets=[],
        question_strategies=[],
        stopping_rules=StoppingRules(min_rounds=1, max_rounds=3, target_confidence=0.9, min_coverage_ratio=0.9),
        report_template="test",
    )

    engine = AssessmentEngine(protocol=protocol, llm_client=None)
    engine.start_session()

    # Run to max rounds
    for i in range(3):
        q = engine.get_next_question()
        if q["status"] == "complete":
            break
        engine.submit_answer(f"Answer {i}")

    # Should be complete now
    final_q = engine.get_next_question()
    assert final_q["status"] == "complete"
