import pytest
from assessment_engine.core.evidence import DimensionMapping, Evidence


class TestDimensionMapping:
    def test_valid_mapping(self):
        mapping = DimensionMapping(
            dimension_id="dim1",
            direction=1,
            weight=0.8,
            confidence=0.9,
        )
        assert mapping.dimension_id == "dim1"
        assert mapping.direction == 1
        assert mapping.weight == 0.8
        assert mapping.confidence == 0.9

    def test_direction_zero(self):
        mapping = DimensionMapping(
            dimension_id="dim1",
            direction=0,
            weight=0.5,
            confidence=0.7,
        )
        assert mapping.direction == 0

    def test_direction_negative(self):
        mapping = DimensionMapping(
            dimension_id="dim1",
            direction=-1,
            weight=0.5,
            confidence=0.7,
        )
        assert mapping.direction == -1

    def test_validation_direction_range(self):
        with pytest.raises(ValueError):
            DimensionMapping(
                dimension_id="dim1",
                direction=2,
                weight=0.5,
                confidence=0.7,
            )
        with pytest.raises(ValueError):
            DimensionMapping(
                dimension_id="dim1",
                direction=-2,
                weight=0.5,
                confidence=0.7,
            )

    def test_validation_weight_range(self):
        with pytest.raises(ValueError):
            DimensionMapping(
                dimension_id="dim1",
                direction=1,
                weight=1.1,
                confidence=0.7,
            )
        with pytest.raises(ValueError):
            DimensionMapping(
                dimension_id="dim1",
                direction=1,
                weight=-0.1,
                confidence=0.7,
            )

    def test_validation_confidence_range(self):
        with pytest.raises(ValueError):
            DimensionMapping(
                dimension_id="dim1",
                direction=1,
                weight=0.5,
                confidence=1.1,
            )
        with pytest.raises(ValueError):
            DimensionMapping(
                dimension_id="dim1",
                direction=1,
                weight=0.5,
                confidence=-0.1,
            )


class TestEvidence:
    def test_evidence_creation(self):
        mapping = DimensionMapping(
            dimension_id="dim1",
            direction=1,
            weight=0.8,
            confidence=0.9,
        )
        evidence = Evidence(
            id="ev1",
            round_index=0,
            source_text="The user said something important",
            evidence_type="statement",
            normalized_claim="User made a claim",
            mapped_dimensions=[mapping],
        )
        assert evidence.id == "ev1"
        assert evidence.round_index == 0
        assert evidence.source_text == "The user said something important"
        assert evidence.evidence_type == "statement"
        assert evidence.normalized_claim == "User made a claim"
        assert len(evidence.mapped_dimensions) == 1
        assert evidence.tags == []

    def test_evidence_with_tags(self):
        mapping = DimensionMapping(
            dimension_id="dim1",
            direction=1,
            weight=0.8,
            confidence=0.9,
        )
        evidence = Evidence(
            id="ev1",
            round_index=1,
            source_text="Text",
            evidence_type="statement",
            normalized_claim="Claim",
            mapped_dimensions=[mapping],
            tags=["important", "verified"],
        )
        assert evidence.tags == ["important", "verified"]

    def test_validation_round_index_ge_zero(self):
        mapping = DimensionMapping(
            dimension_id="dim1",
            direction=1,
            weight=0.8,
            confidence=0.9,
        )
        with pytest.raises(ValueError):
            Evidence(
                id="ev1",
                round_index=-1,
                source_text="Text",
                evidence_type="statement",
                normalized_claim="Claim",
                mapped_dimensions=[mapping],
            )

    def test_multiple_mappings(self):
        mappings = [
            DimensionMapping(
                dimension_id="dim1",
                direction=1,
                weight=0.8,
                confidence=0.9,
            ),
            DimensionMapping(
                dimension_id="dim2",
                direction=-1,
                weight=0.6,
                confidence=0.7,
            ),
        ]
        evidence = Evidence(
            id="ev1",
            round_index=0,
            source_text="Text",
            evidence_type="statement",
            normalized_claim="Claim",
            mapped_dimensions=mappings,
        )
        assert len(evidence.mapped_dimensions) == 2
