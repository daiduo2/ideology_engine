"""Tests for TerminationChecker."""
import pytest
from assessment_engine.core.protocol import StoppingRules
from assessment_engine.core.state import AssessmentState, DimensionState, Coverage, TerminationStatus
from assessment_engine.core.contradiction import Contradiction
from assessment_engine.engine.termination_checker import TerminationChecker


def test_min_rounds_not_met():
    """Test that termination is not eligible when min_rounds is not met."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    state = AssessmentState(
        dimensions={"dim_1": DimensionState(score=0.5, confidence=0.8, evidence_count=1, last_updated_at_round=1)},
        coverage=Coverage(),
    )

    result = checker.check(state, round_index=3)

    assert result.eligible is False
    assert len(result.reasons) == 1
    assert "min_rounds not met: 3 < 6" in result.reasons


def test_max_rounds_reached():
    """Test that termination is forced when max_rounds is reached."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    state = AssessmentState(
        dimensions={},
        coverage=Coverage(),
    )

    result = checker.check(state, round_index=15)

    assert result.eligible is True
    assert len(result.reasons) == 1
    assert "max_rounds reached: 15" in result.reasons


def test_max_rounds_exceeded():
    """Test that termination is forced when max_rounds is exceeded."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    state = AssessmentState(
        dimensions={},
        coverage=Coverage(),
    )

    result = checker.check(state, round_index=20)

    assert result.eligible is True
    assert "max_rounds reached: 20" in result.reasons


def test_all_conditions_met():
    """Test that termination is eligible when all conditions are met."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    # Create coverage with targets met (pass extra fields during construction)
    coverage = Coverage(target_a=True, target_b=True)

    state = AssessmentState(
        dimensions={
            "dim_1": DimensionState(score=0.5, confidence=0.8, evidence_count=1, last_updated_at_round=1),
            "dim_2": DimensionState(score=0.6, confidence=0.75, evidence_count=1, last_updated_at_round=1),
        },
        coverage=coverage,
    )

    result = checker.check(
        state,
        round_index=10,
        coverage_targets=["target_a", "target_b"],
        unresolved_contradictions=[],
    )

    assert result.eligible is True
    assert "all stopping conditions met" in result.reasons


def test_coverage_not_met():
    """Test that termination is not eligible when coverage ratio is too low."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    # Create coverage with only one target met (pass extra fields during construction)
    coverage = Coverage(target_a=True, target_b=False)

    state = AssessmentState(
        dimensions={
            "dim_1": DimensionState(score=0.5, confidence=0.8, evidence_count=1, last_updated_at_round=1),
        },
        coverage=coverage,
    )

    result = checker.check(
        state,
        round_index=10,
        coverage_targets=["target_a", "target_b"],
    )

    assert result.eligible is False
    assert any("coverage_ratio too low: 0.50 < 0.8" in r for r in result.reasons)


def test_confidence_not_met():
    """Test that termination is not eligible when average confidence is too low."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    state = AssessmentState(
        dimensions={
            "dim_1": DimensionState(score=0.5, confidence=0.5, evidence_count=1, last_updated_at_round=1),
            "dim_2": DimensionState(score=0.6, confidence=0.6, evidence_count=1, last_updated_at_round=1),
        },
        coverage=Coverage(),
    )

    result = checker.check(state, round_index=10)

    assert result.eligible is False
    assert any("avg_confidence too low: 0.55 < 0.72" in r for r in result.reasons)


def test_unresolved_severe_contradictions():
    """Test that termination is not eligible when there are unresolved severe contradictions."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    state = AssessmentState(
        dimensions={
            "dim_1": DimensionState(score=0.5, confidence=0.8, evidence_count=1, last_updated_at_round=1),
        },
        coverage=Coverage(),
    )

    contradictions = [
        Contradiction(
            id="c1",
            round_index=1,
            description="test contradiction",
            related_dimension_ids=["dim_1"],
            evidence_ids=["e1", "e2"],
            severity="high",
            needs_followup=True,
        )
    ]

    result = checker.check(state, round_index=10, unresolved_contradictions=contradictions)

    assert result.eligible is False
    assert any("unresolved severe contradictions: 1" in r for r in result.reasons)


def test_resolved_contradictions_allowed():
    """Test that low severity contradictions don't block termination."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    # Create coverage with targets met (pass extra fields during construction)
    coverage = Coverage(target_a=True)

    state = AssessmentState(
        dimensions={
            "dim_1": DimensionState(score=0.5, confidence=0.8, evidence_count=1, last_updated_at_round=1),
        },
        coverage=coverage,
    )

    # Low severity contradictions should not block
    contradictions = [
        Contradiction(
            id="c1",
            round_index=1,
            description="low severity",
            related_dimension_ids=["dim_1"],
            evidence_ids=["e1"],
            severity="low",
            needs_followup=True,
        ),
        Contradiction(
            id="c2",
            round_index=1,
            description="medium severity",
            related_dimension_ids=["dim_1"],
            evidence_ids=["e2"],
            severity="medium",
            needs_followup=True,
        ),
    ]

    result = checker.check(
        state,
        round_index=10,
        coverage_targets=["target_a"],
        unresolved_contradictions=contradictions,
    )

    assert result.eligible is True
    assert "all stopping conditions met" in result.reasons


def test_no_coverage_targets():
    """Test that empty coverage targets list returns full coverage."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    state = AssessmentState(
        dimensions={
            "dim_1": DimensionState(score=0.5, confidence=0.8, evidence_count=1, last_updated_at_round=1),
        },
        coverage=Coverage(),
    )

    result = checker.check(state, round_index=10, coverage_targets=[])

    assert result.eligible is True
    assert "all stopping conditions met" in result.reasons


def test_no_dimensions():
    """Test behavior when state has no dimensions."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    state = AssessmentState(
        dimensions={},
        coverage=Coverage(),
    )

    result = checker.check(state, round_index=10)

    assert result.eligible is False
    assert any("avg_confidence too low: 0.00 < 0.72" in r for r in result.reasons)


def test_multiple_failure_reasons():
    """Test that multiple failure reasons are collected."""
    rules = StoppingRules(min_rounds=6, max_rounds=15, target_confidence=0.72, min_coverage_ratio=0.8)
    checker = TerminationChecker(rules)

    # Pass extra fields during construction
    coverage = Coverage(target_a=False)

    state = AssessmentState(
        dimensions={
            "dim_1": DimensionState(score=0.5, confidence=0.5, evidence_count=1, last_updated_at_round=1),
        },
        coverage=coverage,
    )

    contradictions = [
        Contradiction(
            id="c1",
            round_index=1,
            description="severe",
            related_dimension_ids=["dim_1"],
            evidence_ids=["e1"],
            severity="high",
            needs_followup=True,
        )
    ]

    result = checker.check(
        state,
        round_index=10,
        coverage_targets=["target_a"],
        unresolved_contradictions=contradictions,
    )

    assert result.eligible is False
    assert len(result.reasons) == 3
    assert any("coverage_ratio" in r for r in result.reasons)
    assert any("avg_confidence" in r for r in result.reasons)
    assert any("unresolved severe contradictions" in r for r in result.reasons)
