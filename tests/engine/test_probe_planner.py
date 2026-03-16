import pytest
from assessment_engine.core.protocol import AssessmentProtocol, Dimension, Scale, StoppingRules
from assessment_engine.core.state import AssessmentState, DimensionState, Coverage
from assessment_engine.core.contradiction import Contradiction
from assessment_engine.engine.probe_planner import ProbePlanner


@pytest.fixture
def protocol():
    return AssessmentProtocol(
        id="test-protocol",
        name="Test Protocol",
        description="A test protocol",
        dimensions=[
            Dimension(id="dim1", name="Dimension 1", description="First dimension"),
            Dimension(id="dim2", name="Dimension 2", description="Second dimension"),
        ],
        coverage_targets=["self_description", "recent_example", "decision_process"],
        question_strategies=["ask_recent_example", "ask_clarification", "ask_counterexample", "ask_context_boundary"],
        stopping_rules=StoppingRules(),
        report_template="Test template",
    )


@pytest.fixture
def planner(protocol):
    return ProbePlanner(protocol)


class TestProbePlannerCoverageGap:
    """Tests for coverage gap detection."""

    def test_finds_coverage_gap(self, planner):
        """Should find uncovered coverage target."""
        state = AssessmentState(
            dimensions={"dim1": DimensionState()},
            coverage=Coverage(self_description=True, recent_example=False),
        )

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
        )

        assert result.type == "coverage_gap"
        assert result.target == "recent_example"
        assert "not yet covered" in result.reason
        assert result.recommended_strategy == "ask_recent_example"

    def test_no_coverage_gap_when_all_covered(self, planner):
        """Should not return coverage gap when all targets covered."""
        state = AssessmentState(
            dimensions={"dim1": DimensionState(confidence=0.8)},
            coverage=Coverage(self_description=True, recent_example=True, decision_process=True),
        )

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
        )

        # Should fall through to default (no low confidence dims either)
        assert result.type == "coverage_gap"
        assert result.target == "self_description"  # First in list


class TestProbePlannerContradiction:
    """Tests for contradiction prioritization."""

    def test_prioritizes_severe_contradiction(self, planner):
        """Should prioritize high severity contradictions needing followup."""
        state = AssessmentState(
            dimensions={"dim1": DimensionState()},
            coverage=Coverage(self_description=True, recent_example=True, decision_process=True),
        )
        contradictions = [
            Contradiction(
                id="contradiction-1",
                round_index=1,
                description="Test contradiction",
                related_dimension_ids=["dim1"],
                evidence_ids=["ev1", "ev2"],
                severity="high",
                needs_followup=True,
            )
        ]

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
            unresolved_contradictions=contradictions,
        )

        assert result.type == "contradiction"
        assert result.target == "contradiction-1"
        assert result.recommended_strategy == "ask_clarification"

    def test_ignores_low_severity_contradiction(self, planner):
        """Should not prioritize low severity contradictions."""
        state = AssessmentState(
            dimensions={"dim1": DimensionState(confidence=0.3)},
            coverage=Coverage(self_description=True, recent_example=True, decision_process=True),
        )
        contradictions = [
            Contradiction(
                id="contradiction-1",
                round_index=1,
                description="Test contradiction",
                related_dimension_ids=["dim1"],
                evidence_ids=["ev1", "ev2"],
                severity="low",
                needs_followup=True,
            )
        ]

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
            unresolved_contradictions=contradictions,
        )

        # Should skip to low confidence dimension
        assert result.type == "dimension_uncertainty"

    def test_ignores_contradiction_not_needing_followup(self, planner):
        """Should not prioritize contradictions that don't need followup."""
        state = AssessmentState(
            dimensions={"dim1": DimensionState(confidence=0.3)},
            coverage=Coverage(self_description=True, recent_example=True, decision_process=True),
        )
        contradictions = [
            Contradiction(
                id="contradiction-1",
                round_index=1,
                description="Test contradiction",
                related_dimension_ids=["dim1"],
                evidence_ids=["ev1", "ev2"],
                severity="high",
                needs_followup=False,
            )
        ]

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
            unresolved_contradictions=contradictions,
        )

        # Should skip to low confidence dimension
        assert result.type == "dimension_uncertainty"


class TestProbePlannerLowConfidence:
    """Tests for low confidence dimension detection."""

    def test_finds_low_confidence_dimension(self, planner):
        """Should find dimension with low confidence."""
        state = AssessmentState(
            dimensions={
                "dim1": DimensionState(confidence=0.3),
                "dim2": DimensionState(confidence=0.8),
            },
            coverage=Coverage(self_description=True, recent_example=True, decision_process=True),
        )

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
        )

        assert result.type == "dimension_uncertainty"
        assert result.target == "dim1"
        assert "0.30" in result.reason
        assert result.recommended_strategy == "ask_recent_example"

    def test_picks_lowest_confidence(self, planner):
        """Should pick the dimension with lowest confidence."""
        state = AssessmentState(
            dimensions={
                "dim1": DimensionState(confidence=0.4),
                "dim2": DimensionState(confidence=0.2),
                "dim3": DimensionState(confidence=0.3),
            },
            coverage=Coverage(self_description=True, recent_example=True, decision_process=True),
        )

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
        )

        assert result.type == "dimension_uncertainty"
        assert result.target == "dim2"
        assert "0.20" in result.reason

    def test_no_low_confidence_when_all_high(self, planner):
        """Should not return low confidence when all dimensions have high confidence."""
        state = AssessmentState(
            dimensions={
                "dim1": DimensionState(confidence=0.8),
                "dim2": DimensionState(confidence=0.9),
            },
            coverage=Coverage(self_description=True, recent_example=True, decision_process=True),
        )

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
        )

        # Should fall through to default
        assert result.type == "coverage_gap"


class TestProbePlannerAmbiguity:
    """Tests for ambiguity detection from open questions."""

    def test_finds_ambiguity_from_open_questions(self, planner):
        """Should return ambiguity target when open questions exist."""
        state = AssessmentState(
            dimensions={
                "dim1": DimensionState(confidence=0.8),
            },
            coverage=Coverage(self_description=True, recent_example=True, decision_process=True),
            open_questions=["What did you mean by that?"],
        )

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
        )

        assert result.type == "ambiguity"
        assert result.target == "general"
        assert result.reason == "What did you mean by that?"
        assert result.recommended_strategy == "ask_clarification"


class TestProbePlannerDefault:
    """Tests for default behavior."""

    def test_default_with_coverage_targets(self, planner):
        """Should return first coverage target as default when targets provided."""
        state = AssessmentState(
            dimensions={"dim1": DimensionState(confidence=0.8)},
            coverage=Coverage(self_description=True, recent_example=True, decision_process=True),
        )

        result = planner.plan_next(
            state,
            coverage_targets=["self_description", "recent_example", "decision_process"],
        )

        assert result.type == "coverage_gap"
        assert result.target == "self_description"
        assert result.reason == "Continuing exploration"

    def test_default_without_coverage_targets(self, planner):
        """Should return 'general' as default when no coverage targets."""
        state = AssessmentState(
            dimensions={"dim1": DimensionState(confidence=0.8)},
            coverage=Coverage(),
        )

        result = planner.plan_next(state)

        assert result.type == "coverage_gap"
        assert result.target == "general"
        assert result.reason == "Continuing exploration"


class TestProbePlannerStrategySelection:
    """Tests for strategy selection based on coverage target."""

    def test_strategy_for_self_description(self, planner):
        """Should return ask_context_boundary for self_description."""
        strategy = planner._select_strategy_for_coverage("self_description")
        assert strategy == "ask_context_boundary"

    def test_strategy_for_recent_example(self, planner):
        """Should return ask_recent_example for recent_example."""
        strategy = planner._select_strategy_for_coverage("recent_example")
        assert strategy == "ask_recent_example"

    def test_strategy_for_decision_process(self, planner):
        """Should return ask_recent_example for decision_process."""
        strategy = planner._select_strategy_for_coverage("decision_process")
        assert strategy == "ask_recent_example"

    def test_strategy_for_social_context(self, planner):
        """Should return ask_context_boundary for social_context."""
        strategy = planner._select_strategy_for_coverage("social_context")
        assert strategy == "ask_context_boundary"

    def test_strategy_for_conflict_response(self, planner):
        """Should return ask_counterexample for conflict_response."""
        strategy = planner._select_strategy_for_coverage("conflict_response")
        assert strategy == "ask_counterexample"

    def test_strategy_for_unknown_target(self, planner):
        """Should return ask_recent_example for unknown target."""
        strategy = planner._select_strategy_for_coverage("unknown_target")
        assert strategy == "ask_recent_example"
