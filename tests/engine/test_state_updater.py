"""Tests for StateUpdater."""
import pytest
from assessment_engine.core.state import AssessmentState, DimensionState, Coverage
from assessment_engine.core.evidence import Evidence, DimensionMapping
from assessment_engine.engine.state_updater import StateUpdater


def test_state_updater_initialization():
    updater = StateUpdater(learning_rate=0.1)
    assert updater.learning_rate == 0.1


def test_update_dimension_score():
    updater = StateUpdater(learning_rate=0.1)

    state = AssessmentState(
        dimensions={"dim_1": DimensionState(score=0.5, confidence=0.0, evidence_count=0, last_updated_at_round=0)},
        coverage=Coverage(),
    )

    evidence = Evidence(
        id="e1",
        round_index=1,
        source_text="test",
        evidence_type="test",
        normalized_claim="test",
        mapped_dimensions=[DimensionMapping(dimension_id="dim_1", direction=1, weight=0.5, confidence=0.8)],
    )

    new_state = updater.update_state(state, [evidence], round_index=1)

    # Score should move from 0.5 toward positive
    assert new_state.dimensions["dim_1"].score > 0.5
    assert new_state.dimensions["dim_1"].evidence_count == 1
    assert new_state.dimensions["dim_1"].last_updated_at_round == 1


def test_confidence_increases_with_evidence():
    updater = StateUpdater()

    state = AssessmentState(
        dimensions={"dim_1": DimensionState(score=0.5, confidence=0.0, evidence_count=0, last_updated_at_round=0)},
        coverage=Coverage(),
    )

    evidence = Evidence(
        id="e1",
        round_index=1,
        source_text="test",
        evidence_type="test",
        normalized_claim="test",
        mapped_dimensions=[DimensionMapping(dimension_id="dim_1", direction=1, weight=0.5, confidence=0.8)],
    )

    new_state = updater.update_state(state, [evidence], round_index=1)
    assert new_state.dimensions["dim_1"].confidence > 0


def test_coverage_tracking():
    updater = StateUpdater()

    state = AssessmentState(
        dimensions={},
        coverage=Coverage(),
    )

    evidence = Evidence(
        id="e1",
        round_index=1,
        source_text="test",
        evidence_type="test",
        normalized_claim="test",
        mapped_dimensions=[],
        tags=["self_description"],
    )

    new_state = updater.update_state(state, [evidence], round_index=1, coverage_targets=["self_description"])
    assert getattr(new_state.coverage, "self_description", False) is True
