"""Tests for preset protocol templates."""

import pytest
from assessment_engine.storage.protocol_repo import ProtocolRepository
from assessment_engine.core.protocol import AssessmentProtocol


class TestPresetProtocols:
    """Test suite for preset protocol templates."""

    @pytest.fixture
    def protocol_repo(self):
        """Create protocol repository for testing."""
        from pathlib import Path
        # Use project root relative to test file
        project_root = Path(__file__).parent.parent
        return ProtocolRepository(base_path=project_root)

    @pytest.fixture
    def preset_protocol_ids(self):
        """List of preset protocol IDs to test."""
        return [
            "mbti-assessment",
            "disc-assessment",
            "communication-style",
            "leadership-style"
        ]

    def test_all_protocols_load_correctly(self, protocol_repo, preset_protocol_ids):
        """Verify all preset protocols can be loaded."""
        for protocol_id in preset_protocol_ids:
            protocol = protocol_repo.load(protocol_id)
            assert protocol is not None, f"Protocol {protocol_id} should exist"
            assert isinstance(protocol, AssessmentProtocol)

    def test_mbti_protocol_structure(self, protocol_repo):
        """Verify MBTI protocol has correct structure."""
        protocol = protocol_repo.load("mbti-assessment")

        # Check dimensions
        assert len(protocol.dimensions) == 4
        dimension_ids = [d.id for d in protocol.dimensions]
        assert "extraversion_introversion" in dimension_ids
        assert "sensing_intuition" in dimension_ids
        assert "thinking_feeling" in dimension_ids
        assert "judging_perceiving" in dimension_ids

        # Check scale (-1 to +1)
        for dim in protocol.dimensions:
            assert dim.scale.min == -1.0
            assert dim.scale.max == 1.0
            assert dim.scale.default == 0.0

        # Check coverage targets
        expected_targets = [
            "self_description",
            "work_scenario",
            "social_interaction",
            "decision_making"
        ]
        for target in expected_targets:
            assert target in protocol.coverage_targets

    def test_disc_protocol_structure(self, protocol_repo):
        """Verify DISC protocol has correct structure."""
        protocol = protocol_repo.load("disc-assessment")

        # Check dimensions
        assert len(protocol.dimensions) == 4
        dimension_ids = [d.id for d in protocol.dimensions]
        assert "dominance" in dimension_ids
        assert "influence" in dimension_ids
        assert "steadiness" in dimension_ids
        assert "conscientiousness" in dimension_ids

        # Check scale (0 to 1)
        for dim in protocol.dimensions:
            assert dim.scale.min == 0.0
            assert dim.scale.max == 1.0
            assert dim.scale.default == 0.5

        # Check coverage targets
        expected_targets = [
            "work_pressure",
            "team_collaboration",
            "change_adaptation",
            "rule_following"
        ]
        for target in expected_targets:
            assert target in protocol.coverage_targets

    def test_communication_style_protocol_structure(self, protocol_repo):
        """Verify Communication Style protocol has correct structure."""
        protocol = protocol_repo.load("communication-style")

        # Check dimensions
        assert len(protocol.dimensions) == 3
        dimension_ids = [d.id for d in protocol.dimensions]
        assert "directness" in dimension_ids
        assert "empathy" in dimension_ids
        assert "assertiveness" in dimension_ids

        # Check scale (0 to 1)
        for dim in protocol.dimensions:
            assert dim.scale.min == 0.0
            assert dim.scale.max == 1.0
            assert dim.scale.default == 0.5

        # Check coverage targets
        expected_targets = [
            "feedback_giving",
            "conflict_handling",
            "active_listening",
            "clarity_expression"
        ]
        for target in expected_targets:
            assert target in protocol.coverage_targets

    def test_leadership_style_protocol_structure(self, protocol_repo):
        """Verify Leadership Style protocol has correct structure."""
        protocol = protocol_repo.load("leadership-style")

        # Check dimensions
        assert len(protocol.dimensions) == 3
        dimension_ids = [d.id for d in protocol.dimensions]
        assert "visionary" in dimension_ids
        assert "coaching" in dimension_ids
        assert "commanding" in dimension_ids

        # Check scale (0 to 1)
        for dim in protocol.dimensions:
            assert dim.scale.min == 0.0
            assert dim.scale.max == 1.0
            assert dim.scale.default == 0.5

        # Check coverage targets
        expected_targets = [
            "team_motivation",
            "delegation",
            "crisis_management",
            "development_focus"
        ]
        for target in expected_targets:
            assert target in protocol.coverage_targets

    def test_stopping_rules_are_reasonable(self, protocol_repo, preset_protocol_ids):
        """Verify all protocols have reasonable stopping rules."""
        for protocol_id in preset_protocol_ids:
            protocol = protocol_repo.load(protocol_id)

            # Min rounds should be at least 6
            assert protocol.stopping_rules.min_rounds >= 6, \
                f"{protocol_id}: min_rounds should be >= 6"

            # Max rounds should be at least min_rounds
            assert protocol.stopping_rules.max_rounds >= protocol.stopping_rules.min_rounds, \
                f"{protocol_id}: max_rounds should be >= min_rounds"

            # Max rounds should not exceed 20
            assert protocol.stopping_rules.max_rounds <= 20, \
                f"{protocol_id}: max_rounds should be <= 20"

            # Target confidence should be between 0.5 and 0.95
            assert 0.5 <= protocol.stopping_rules.target_confidence <= 0.95, \
                f"{protocol_id}: target_confidence should be between 0.5 and 0.95"

            # Min coverage ratio should be between 0.5 and 1.0
            assert 0.5 <= protocol.stopping_rules.min_coverage_ratio <= 1.0, \
                f"{protocol_id}: min_coverage_ratio should be between 0.5 and 1.0"

    def test_report_templates_exist(self, protocol_repo, preset_protocol_ids):
        """Verify all protocols reference a report template."""
        for protocol_id in preset_protocol_ids:
            protocol = protocol_repo.load(protocol_id)

            assert protocol.report_template is not None
            assert len(protocol.report_template) > 0

    def test_question_strategies_exist(self, protocol_repo, preset_protocol_ids):
        """Verify all protocols have question strategies."""
        for protocol_id in preset_protocol_ids:
            protocol = protocol_repo.load(protocol_id)

            assert len(protocol.question_strategies) > 0, \
                f"{protocol_id}: should have at least one question strategy"

    def test_protocols_have_descriptions(self, protocol_repo, preset_protocol_ids):
        """Verify all protocols have meaningful descriptions."""
        for protocol_id in preset_protocol_ids:
            protocol = protocol_repo.load(protocol_id)

            assert protocol.description is not None
            assert len(protocol.description) > 10, \
                f"{protocol_id}: description should be meaningful"

    def test_all_dimensions_have_descriptions(self, protocol_repo, preset_protocol_ids):
        """Verify all dimensions in all protocols have descriptions."""
        for protocol_id in preset_protocol_ids:
            protocol = protocol_repo.load(protocol_id)

            for dim in protocol.dimensions:
                assert dim.description is not None, \
                    f"{protocol_id}.{dim.id}: dimension should have description"
                assert len(dim.description) > 5, \
                    f"{protocol_id}.{dim.id}: dimension description should be meaningful"

    def test_protocol_ids_match_filenames(self, protocol_repo, preset_protocol_ids):
        """Verify protocol IDs match their filenames."""
        for protocol_id in preset_protocol_ids:
            protocol = protocol_repo.load(protocol_id)
            assert protocol.id == protocol_id, \
                f"Protocol ID {protocol.id} should match filename {protocol_id}"
