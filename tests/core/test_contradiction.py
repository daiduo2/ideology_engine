import pytest
from assessment_engine.core.contradiction import Contradiction


class TestContradiction:
    def test_contradiction_creation(self):
        contradiction = Contradiction(
            id="contradiction_1",
            round_index=2,
            description="User contradicted previous statement",
            related_dimension_ids=["dim1", "dim2"],
            evidence_ids=["ev1", "ev2"],
            severity="medium",
        )
        assert contradiction.id == "contradiction_1"
        assert contradiction.round_index == 2
        assert contradiction.description == "User contradicted previous statement"
        assert contradiction.related_dimension_ids == ["dim1", "dim2"]
        assert contradiction.evidence_ids == ["ev1", "ev2"]
        assert contradiction.severity == "medium"
        assert contradiction.needs_followup is True

    def test_contradiction_severity_low(self):
        contradiction = Contradiction(
            id="contradiction_1",
            round_index=0,
            description="Minor inconsistency",
            related_dimension_ids=["dim1"],
            evidence_ids=["ev1"],
            severity="low",
        )
        assert contradiction.severity == "low"

    def test_contradiction_severity_high(self):
        contradiction = Contradiction(
            id="contradiction_1",
            round_index=1,
            description="Major contradiction",
            related_dimension_ids=["dim1", "dim2", "dim3"],
            evidence_ids=["ev1", "ev2"],
            severity="high",
            needs_followup=False,
        )
        assert contradiction.severity == "high"
        assert contradiction.needs_followup is False

    def test_validation_severity_invalid(self):
        with pytest.raises(ValueError):
            Contradiction(
                id="contradiction_1",
                round_index=0,
                description="Test",
                related_dimension_ids=["dim1"],
                evidence_ids=["ev1"],
                severity="invalid",
            )

    def test_validation_round_index_ge_zero(self):
        with pytest.raises(ValueError):
            Contradiction(
                id="contradiction_1",
                round_index=-1,
                description="Test",
                related_dimension_ids=["dim1"],
                evidence_ids=["ev1"],
                severity="low",
            )

    def test_empty_dimension_ids(self):
        contradiction = Contradiction(
            id="contradiction_1",
            round_index=0,
            description="Test",
            related_dimension_ids=[],
            evidence_ids=["ev1"],
            severity="low",
        )
        assert contradiction.related_dimension_ids == []

    def test_empty_evidence_ids(self):
        contradiction = Contradiction(
            id="contradiction_1",
            round_index=0,
            description="Test",
            related_dimension_ids=["dim1"],
            evidence_ids=[],
            severity="low",
        )
        assert contradiction.evidence_ids == []
