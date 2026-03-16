import pytest
from assessment_engine.core.protocol import (
    Scale,
    Dimension,
    StoppingRules,
    AssessmentProtocol,
)


class TestScale:
    def test_default_values(self):
        scale = Scale()
        assert scale.min == 0
        assert scale.max == 1
        assert scale.default == 0.5

    def test_custom_values(self):
        scale = Scale(min=0.2, max=0.8, default=0.5)
        assert scale.min == 0.2
        assert scale.max == 0.8
        assert scale.default == 0.5

    def test_validation_min_ge_zero(self):
        with pytest.raises(ValueError):
            Scale(min=-0.1)

    def test_validation_max_le_one(self):
        with pytest.raises(ValueError):
            Scale(max=1.1)


class TestDimension:
    def test_dimension_creation(self):
        dimension = Dimension(
            id="test_dim",
            name="Test Dimension",
            description="A test dimension",
        )
        assert dimension.id == "test_dim"
        assert dimension.name == "Test Dimension"
        assert dimension.description == "A test dimension"
        assert isinstance(dimension.scale, Scale)

    def test_dimension_with_custom_scale(self):
        scale = Scale(min=0.1, max=0.9, default=0.5)
        dimension = Dimension(
            id="test_dim",
            name="Test Dimension",
            description="A test dimension",
            scale=scale,
        )
        assert dimension.scale.min == 0.1
        assert dimension.scale.max == 0.9
        assert dimension.scale.default == 0.5


class TestStoppingRules:
    def test_default_values(self):
        rules = StoppingRules()
        assert rules.min_rounds == 6
        assert rules.max_rounds == 15
        assert rules.target_confidence == 0.72
        assert rules.min_coverage_ratio == 0.8

    def test_validation_min_rounds_ge_one(self):
        with pytest.raises(ValueError):
            StoppingRules(min_rounds=0)

    def test_validation_max_rounds_ge_one(self):
        with pytest.raises(ValueError):
            StoppingRules(max_rounds=0)

    def test_validation_confidence_range(self):
        with pytest.raises(ValueError):
            StoppingRules(target_confidence=1.1)
        with pytest.raises(ValueError):
            StoppingRules(target_confidence=-0.1)

    def test_validation_coverage_ratio_range(self):
        with pytest.raises(ValueError):
            StoppingRules(min_coverage_ratio=1.1)
        with pytest.raises(ValueError):
            StoppingRules(min_coverage_ratio=-0.1)


class TestAssessmentProtocol:
    def test_protocol_creation(self):
        dimensions = [
            Dimension(id="dim1", name="Dimension 1", description="First dimension"),
            Dimension(id="dim2", name="Dimension 2", description="Second dimension"),
        ]
        protocol = AssessmentProtocol(
            id="test_protocol",
            name="Test Protocol",
            description="A test protocol",
            dimensions=dimensions,
            coverage_targets=["target1", "target2"],
            question_strategies=["strategy1"],
            stopping_rules=StoppingRules(),
            report_template="default",
        )
        assert protocol.id == "test_protocol"
        assert protocol.name == "Test Protocol"
        assert len(protocol.dimensions) == 2
        assert protocol.coverage_targets == ["target1", "target2"]

    def test_empty_dimensions(self):
        protocol = AssessmentProtocol(
            id="test_protocol",
            name="Test Protocol",
            description="A test protocol",
            dimensions=[],
            coverage_targets=[],
            question_strategies=[],
            stopping_rules=StoppingRules(),
            report_template="default",
        )
        assert protocol.dimensions == []
