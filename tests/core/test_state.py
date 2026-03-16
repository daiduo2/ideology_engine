import pytest
from assessment_engine.core.state import (
    DimensionState,
    Coverage,
    NextTarget,
    TerminationStatus,
    AssessmentState,
)


class TestDimensionState:
    def test_default_values(self):
        state = DimensionState()
        assert state.score == 0.5
        assert state.confidence == 0.0
        assert state.evidence_count == 0
        assert state.last_updated_at_round == 0

    def test_custom_values(self):
        state = DimensionState(
            score=0.8,
            confidence=0.9,
            evidence_count=3,
            last_updated_at_round=2,
        )
        assert state.score == 0.8
        assert state.confidence == 0.9
        assert state.evidence_count == 3
        assert state.last_updated_at_round == 2

    def test_validation_score_range(self):
        with pytest.raises(ValueError):
            DimensionState(score=1.1)
        with pytest.raises(ValueError):
            DimensionState(score=-0.1)

    def test_validation_confidence_range(self):
        with pytest.raises(ValueError):
            DimensionState(confidence=1.1)
        with pytest.raises(ValueError):
            DimensionState(confidence=-0.1)

    def test_validation_evidence_count_ge_zero(self):
        with pytest.raises(ValueError):
            DimensionState(evidence_count=-1)

    def test_validation_last_updated_ge_zero(self):
        with pytest.raises(ValueError):
            DimensionState(last_updated_at_round=-1)


class TestCoverage:
    def test_coverage_creation(self):
        coverage = Coverage()
        assert coverage is not None

    def test_coverage_extra_fields(self):
        coverage = Coverage(target1=True, target2=False)
        assert coverage.target1 is True
        assert coverage.target2 is False


class TestNextTarget:
    def test_next_target_coverage_gap(self):
        target = NextTarget(
            type="coverage_gap",
            target="target1",
            reason="Missing coverage for target1",
            recommended_strategy="direct_question",
        )
        assert target.type == "coverage_gap"
        assert target.target == "target1"
        assert target.reason == "Missing coverage for target1"
        assert target.recommended_strategy == "direct_question"

    def test_next_target_dimension_uncertainty(self):
        target = NextTarget(
            type="dimension_uncertainty",
            target="dim1",
        )
        assert target.type == "dimension_uncertainty"
        assert target.target == "dim1"
        assert target.reason is None
        assert target.recommended_strategy is None

    def test_next_target_contradiction(self):
        target = NextTarget(
            type="contradiction",
            target="contradiction_1",
            reason="Needs clarification",
        )
        assert target.type == "contradiction"

    def test_next_target_ambiguity(self):
        target = NextTarget(
            type="ambiguity",
            target="ambiguous_statement",
            reason="Multiple interpretations possible",
        )
        assert target.type == "ambiguity"

    def test_validation_invalid_type(self):
        with pytest.raises(ValueError):
            NextTarget(
                type="invalid_type",
                target="something",
            )


class TestTerminationStatus:
    def test_default_values(self):
        status = TerminationStatus()
        assert status.eligible is False
        assert status.reasons == []

    def test_custom_values(self):
        status = TerminationStatus(
            eligible=True,
            reasons=["max_rounds_reached", "target_confidence_achieved"],
        )
        assert status.eligible is True
        assert status.reasons == ["max_rounds_reached", "target_confidence_achieved"]


class TestAssessmentState:
    def test_assessment_state_creation(self):
        dimensions = {
            "dim1": DimensionState(score=0.7, confidence=0.8),
            "dim2": DimensionState(score=0.5, confidence=0.6),
        }
        state = AssessmentState(dimensions=dimensions)
        assert state.dimensions == dimensions
        assert state.evidence_ids == []
        assert state.contradiction_ids == []
        assert state.open_questions == []
        assert state.recommended_next_target is None
        assert state.termination.eligible is False

    def test_assessment_state_with_evidence(self):
        dimensions = {"dim1": DimensionState()}
        state = AssessmentState(
            dimensions=dimensions,
            evidence_ids=["ev1", "ev2"],
        )
        assert state.evidence_ids == ["ev1", "ev2"]

    def test_assessment_state_with_contradictions(self):
        dimensions = {"dim1": DimensionState()}
        state = AssessmentState(
            dimensions=dimensions,
            contradiction_ids=["contradiction_1"],
        )
        assert state.contradiction_ids == ["contradiction_1"]

    def test_assessment_state_with_open_questions(self):
        dimensions = {"dim1": DimensionState()}
        state = AssessmentState(
            dimensions=dimensions,
            open_questions=["What about X?", "How does Y work?"],
        )
        assert state.open_questions == ["What about X?", "How does Y work?"]

    def test_assessment_state_with_next_target(self):
        dimensions = {"dim1": DimensionState()}
        next_target = NextTarget(
            type="coverage_gap",
            target="target1",
        )
        state = AssessmentState(
            dimensions=dimensions,
            recommended_next_target=next_target,
        )
        assert state.recommended_next_target == next_target

    def test_assessment_state_with_termination(self):
        dimensions = {"dim1": DimensionState()}
        state = AssessmentState(
            dimensions=dimensions,
            termination=TerminationStatus(
                eligible=True,
                reasons=["target_confidence_achieved"],
            ),
        )
        assert state.termination.eligible is True
