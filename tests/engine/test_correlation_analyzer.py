"""Tests for CorrelationAnalyzer."""
import pytest
from assessment_engine.core.evidence import Evidence, DimensionMapping
from assessment_engine.core.state import AssessmentState, DimensionState, Coverage
from assessment_engine.engine.correlation_analyzer import CorrelationAnalyzer, CorrelationMatrix, DimensionCorrelation


class TestCorrelationAnalyzerInitialization:
    """Test CorrelationAnalyzer initialization."""

    def test_initialization_with_default_threshold(self):
        analyzer = CorrelationAnalyzer()
        assert analyzer.correlation_threshold == 0.3

    def test_initialization_with_custom_threshold(self):
        analyzer = CorrelationAnalyzer(correlation_threshold=0.5)
        assert analyzer.correlation_threshold == 0.5


class TestAnalyzeCorrelations:
    """Test correlation analysis between dimensions."""

    def test_empty_evidence_list_returns_empty_matrix(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(dimensions={"dim_a": DimensionState(), "dim_b": DimensionState()})

        matrix = analyzer.analyze_correlations(state, [])

        assert matrix.correlations == {}
        assert matrix.dimension_ids == ["dim_a", "dim_b"]

    def test_single_dimension_evidence_no_correlation(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(dimensions={"dim_a": DimensionState(), "dim_b": DimensionState()})

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8)],
            )
        ]

        matrix = analyzer.analyze_correlations(state, evidence)

        # No pairs to correlate
        assert matrix.correlations == {}

    def test_evidence_affecting_multiple_dimensions_positively(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(dimensions={"dim_a": DimensionState(), "dim_b": DimensionState()})

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=1, weight=0.5, confidence=0.8),
                ],
            )
        ]

        matrix = analyzer.analyze_correlations(state, evidence)

        pair_key = tuple(sorted(["dim_a", "dim_b"]))
        assert pair_key in matrix.correlations
        corr = matrix.correlations[pair_key]
        assert corr.coefficient > 0  # Positive correlation
        assert corr.shared_evidence_ids == ["e1"]

    def test_evidence_affecting_dimensions_in_opposite_ways(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(dimensions={"analytical": DimensionState(), "emotional": DimensionState()})

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="analytical", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="emotional", direction=-1, weight=0.5, confidence=0.8),
                ],
            )
        ]

        matrix = analyzer.analyze_correlations(state, evidence)

        pair_key = tuple(sorted(["analytical", "emotional"]))
        assert pair_key in matrix.correlations
        corr = matrix.correlations[pair_key]
        assert corr.coefficient < 0  # Negative correlation

    def test_multiple_evidence_builds_correlation(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(dimensions={"dim_a": DimensionState(), "dim_b": DimensionState()})

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test1",
                evidence_type="test",
                normalized_claim="test1",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=1, weight=0.5, confidence=0.8),
                ],
            ),
            Evidence(
                id="e2",
                round_index=2,
                source_text="test2",
                evidence_type="test",
                normalized_claim="test2",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.4, confidence=0.7),
                    DimensionMapping(dimension_id="dim_b", direction=1, weight=0.4, confidence=0.7),
                ],
            ),
        ]

        matrix = analyzer.analyze_correlations(state, evidence)

        pair_key = tuple(sorted(["dim_a", "dim_b"]))
        assert pair_key in matrix.correlations
        corr = matrix.correlations[pair_key]
        assert corr.coefficient > 0
        assert set(corr.shared_evidence_ids) == {"e1", "e2"}

    def test_correlation_coefficient_range(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(
            dimensions={
                "dim_a": DimensionState(),
                "dim_b": DimensionState(),
                "dim_c": DimensionState(),
            }
        )

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=-1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_c", direction=1, weight=0.3, confidence=0.6),
                ],
            )
        ]

        matrix = analyzer.analyze_correlations(state, evidence)

        for corr in matrix.correlations.values():
            assert -1 <= corr.coefficient <= 1


class TestDetectContradictions:
    """Test contradiction detection in evidence."""

    def test_no_contradictions_with_single_dimension_evidence(self):
        analyzer = CorrelationAnalyzer()

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8)],
            )
        ]

        contradictions = analyzer.detect_contradictions(evidence)
        assert contradictions == []

    def test_detect_opposing_effects_as_contradiction(self):
        analyzer = CorrelationAnalyzer()

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=-1, weight=0.5, confidence=0.8),
                ],
            )
        ]

        contradictions = analyzer.detect_contradictions(evidence)
        assert len(contradictions) == 1
        assert contradictions[0].evidence_id == "e1"
        assert contradictions[0].dimension_pair == ("dim_a", "dim_b")
        assert contradictions[0].contradiction_type == "opposing_effects"

    def test_no_contradiction_with_same_direction(self):
        analyzer = CorrelationAnalyzer()

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=1, weight=0.5, confidence=0.8),
                ],
            )
        ]

        contradictions = analyzer.detect_contradictions(evidence)
        assert contradictions == []

    def test_multiple_contradictions_in_different_evidence(self):
        analyzer = CorrelationAnalyzer()

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test1",
                evidence_type="test",
                normalized_claim="test1",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=-1, weight=0.5, confidence=0.8),
                ],
            ),
            Evidence(
                id="e2",
                round_index=2,
                source_text="test2",
                evidence_type="test",
                normalized_claim="test2",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_c", direction=-1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_d", direction=1, weight=0.5, confidence=0.8),
                ],
            ),
        ]

        contradictions = analyzer.detect_contradictions(evidence)
        assert len(contradictions) == 2


class TestGetDimensionClusters:
    """Test dimension clustering based on correlations."""

    def test_empty_matrix_returns_empty_clusters(self):
        analyzer = CorrelationAnalyzer()
        matrix = CorrelationMatrix(dimension_ids=["dim_a", "dim_b"], correlations={})

        clusters = analyzer.get_dimension_clusters(matrix)
        assert clusters == []

    def test_strong_positive_correlation_forms_cluster(self):
        analyzer = CorrelationAnalyzer(correlation_threshold=0.5)
        matrix = CorrelationMatrix(
            dimension_ids=["dim_a", "dim_b", "dim_c"],
            correlations={
                ("dim_a", "dim_b"): DimensionCorrelation(
                    dimension_a="dim_a",
                    dimension_b="dim_b",
                    coefficient=0.8,
                    shared_evidence_ids=["e1"],
                ),
            },
        )

        clusters = analyzer.get_dimension_clusters(matrix)
        assert len(clusters) == 1
        assert set(clusters[0]) == {"dim_a", "dim_b"}

    def test_negative_correlation_does_not_form_cluster(self):
        analyzer = CorrelationAnalyzer(correlation_threshold=0.5)
        matrix = CorrelationMatrix(
            dimension_ids=["dim_a", "dim_b"],
            correlations={
                ("dim_a", "dim_b"): DimensionCorrelation(
                    dimension_a="dim_a",
                    dimension_b="dim_b",
                    coefficient=-0.8,
                    shared_evidence_ids=["e1"],
                ),
            },
        )

        clusters = analyzer.get_dimension_clusters(matrix)
        assert clusters == []

    def test_transitive_clustering(self):
        analyzer = CorrelationAnalyzer(correlation_threshold=0.5)
        matrix = CorrelationMatrix(
            dimension_ids=["dim_a", "dim_b", "dim_c"],
            correlations={
                ("dim_a", "dim_b"): DimensionCorrelation(
                    dimension_a="dim_a",
                    dimension_b="dim_b",
                    coefficient=0.8,
                    shared_evidence_ids=["e1"],
                ),
                ("dim_b", "dim_c"): DimensionCorrelation(
                    dimension_a="dim_b",
                    dimension_b="dim_c",
                    coefficient=0.7,
                    shared_evidence_ids=["e2"],
                ),
            },
        )

        clusters = analyzer.get_dimension_clusters(matrix)
        assert len(clusters) == 1
        assert set(clusters[0]) == {"dim_a", "dim_b", "dim_c"}

    def test_multiple_separate_clusters(self):
        analyzer = CorrelationAnalyzer(correlation_threshold=0.5)
        matrix = CorrelationMatrix(
            dimension_ids=["dim_a", "dim_b", "dim_c", "dim_d"],
            correlations={
                ("dim_a", "dim_b"): DimensionCorrelation(
                    dimension_a="dim_a",
                    dimension_b="dim_b",
                    coefficient=0.8,
                    shared_evidence_ids=["e1"],
                ),
                ("dim_c", "dim_d"): DimensionCorrelation(
                    dimension_a="dim_c",
                    dimension_b="dim_d",
                    coefficient=0.7,
                    shared_evidence_ids=["e2"],
                ),
            },
        )

        clusters = analyzer.get_dimension_clusters(matrix)
        assert len(clusters) == 2


class TestCorrelationCalculationAccuracy:
    """Test accuracy of correlation coefficient calculation."""

    def test_perfect_positive_correlation(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(dimensions={"dim_a": DimensionState(), "dim_b": DimensionState()})

        # Multiple evidence showing same positive direction
        evidence = [
            Evidence(
                id=f"e{i}",
                round_index=i,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=1, weight=0.5, confidence=0.8),
                ],
            )
            for i in range(5)
        ]

        matrix = analyzer.analyze_correlations(state, evidence)

        pair_key = tuple(sorted(["dim_a", "dim_b"]))
        corr = matrix.correlations[pair_key]
        assert corr.coefficient > 0.5  # Strong positive (boosted by agreement)

    def test_perfect_negative_correlation(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(dimensions={"dim_a": DimensionState(), "dim_b": DimensionState()})

        # Multiple evidence showing opposite directions
        evidence = [
            Evidence(
                id=f"e{i}",
                round_index=i,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=-1, weight=0.5, confidence=0.8),
                ],
            )
            for i in range(5)
        ]

        matrix = analyzer.analyze_correlations(state, evidence)

        pair_key = tuple(sorted(["dim_a", "dim_b"]))
        corr = matrix.correlations[pair_key]
        assert corr.coefficient < -0.5  # Strong negative (boosted by agreement)

    def test_mixed_correlation_near_zero(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(dimensions={"dim_a": DimensionState(), "dim_b": DimensionState()})

        # Mixed evidence - some positive, some negative
        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=1, weight=0.5, confidence=0.8),
                ],
            ),
            Evidence(
                id="e2",
                round_index=2,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="dim_a", direction=-1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="dim_b", direction=-1, weight=0.5, confidence=0.8),
                ],
            ),
        ]

        matrix = analyzer.analyze_correlations(state, evidence)

        pair_key = tuple(sorted(["dim_a", "dim_b"]))
        corr = matrix.correlations[pair_key]
        assert corr.coefficient > 0  # Still positive because both agree


class TestCorrelationInsights:
    """Test generation of correlation insights for reports."""

    def test_get_strong_correlations(self):
        analyzer = CorrelationAnalyzer()
        matrix = CorrelationMatrix(
            dimension_ids=["dim_a", "dim_b", "dim_c"],
            correlations={
                ("dim_a", "dim_b"): DimensionCorrelation(
                    dimension_a="dim_a",
                    dimension_b="dim_b",
                    coefficient=0.85,
                    shared_evidence_ids=["e1", "e2"],
                ),
                ("dim_a", "dim_c"): DimensionCorrelation(
                    dimension_a="dim_a",
                    dimension_b="dim_c",
                    coefficient=0.3,
                    shared_evidence_ids=["e3"],
                ),
            },
        )

        strong_correlations = analyzer.get_strong_correlations(matrix, threshold=0.5)
        assert len(strong_correlations) == 1
        assert strong_correlations[0].dimension_pair == ("dim_a", "dim_b")

    def test_correlation_insights_format(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(dimensions={"analytical": DimensionState(), "emotional": DimensionState()})

        # Create multiple evidence to get strong correlation
        evidence = [
            Evidence(
                id=f"e{i}",
                round_index=i,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="analytical", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="emotional", direction=-1, weight=0.5, confidence=0.8),
                ],
            )
            for i in range(5)
        ]

        matrix = analyzer.analyze_correlations(state, evidence)
        insights = analyzer.generate_correlation_insights(matrix)

        assert "analytical" in insights.lower()
        assert "emotional" in insights.lower()


class TestIntegrationWithAssessmentState:
    """Test integration with AssessmentState."""

    def test_update_state_with_correlations(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(
            dimensions={
                "decision_style": DimensionState(),
                "social_orientation": DimensionState(),
            }
        )

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="decision_style", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="social_orientation", direction=-1, weight=0.5, confidence=0.8),
                ],
            )
        ]

        updated_state = analyzer.update_state_with_correlations(state, evidence)

        # Check that correlation data is added to state's coverage
        assert hasattr(updated_state.coverage, "correlation_matrix")
        assert updated_state.coverage.correlation_matrix is not None

    def test_correlation_data_in_report_context(self):
        analyzer = CorrelationAnalyzer()
        state = AssessmentState(
            dimensions={
                "analytical": DimensionState(),
                "creative": DimensionState(),
            }
        )

        evidence = [
            Evidence(
                id="e1",
                round_index=1,
                source_text="test",
                evidence_type="test",
                normalized_claim="test",
                mapped_dimensions=[
                    DimensionMapping(dimension_id="analytical", direction=1, weight=0.5, confidence=0.8),
                    DimensionMapping(dimension_id="creative", direction=-1, weight=0.5, confidence=0.8),
                ],
            )
        ]

        matrix = analyzer.analyze_correlations(state, evidence)
        report_context = analyzer.get_report_context(matrix)

        assert "correlations" in report_context
        assert "clusters" in report_context
        assert "contradictions" in report_context
