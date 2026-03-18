"""Tests for strategy learning from historical sessions."""

import pytest
from datetime import datetime
from assessment_engine.engine.strategy_learner import (
    StrategyLearner,
    StrategyStats,
    StrategyEffectiveness,
)
from assessment_engine.core.session import AssessmentSession
from assessment_engine.core.evidence import Evidence, DimensionMapping


class TestStrategyStats:
    """Tests for StrategyStats dataclass."""

    def test_initial_stats(self):
        """Should initialize with zero values."""
        stats = StrategyStats()
        assert stats.times_used == 0
        assert stats.high_confidence_evidence == 0
        assert stats.total_confidence == 0.0
        assert stats.avg_response_length == 0.0
        assert stats.detailed_responses == 0

    def test_effectiveness_calculation(self):
        """Should calculate effectiveness correctly."""
        stats = StrategyStats(
            times_used=10,
            high_confidence_evidence=7,
            total_confidence=6.5,
        )
        assert stats.effectiveness == 0.7  # 7/10
        assert stats.avg_confidence == 0.65  # 6.5/10

    def test_effectiveness_zero_division(self):
        """Should return 0 effectiveness when never used."""
        stats = StrategyStats()
        assert stats.effectiveness == 0.0
        assert stats.avg_confidence == 0.0


class TestStrategyEffectiveness:
    """Tests for StrategyEffectiveness dataclass."""

    def test_initial_effectiveness(self):
        """Should initialize with empty stats."""
        eff = StrategyEffectiveness()
        assert eff.overall == {}
        assert eff.by_user_type == {}
        assert eff.by_dimension == {}

    def test_get_strategy_score_existing(self):
        """Should return score for existing strategy."""
        eff = StrategyEffectiveness()
        eff.overall["ask_recent_example"] = StrategyStats(
            times_used=10, high_confidence_evidence=8
        )
        assert eff.get_strategy_score("ask_recent_example") == 0.8

    def test_get_strategy_score_missing(self):
        """Should return 0 for missing strategy."""
        eff = StrategyEffectiveness()
        assert eff.get_strategy_score("unknown_strategy") == 0.0


class TestStrategyLearnerInitialization:
    """Tests for StrategyLearner initialization."""

    def test_default_initialization(self):
        """Should initialize with default strategies."""
        learner = StrategyLearner()
        assert "ask_recent_example" in learner.effectiveness.overall
        assert "ask_clarification" in learner.effectiveness.overall
        assert "ask_counterexample" in learner.effectiveness.overall
        assert "ask_context_boundary" in learner.effectiveness.overall

    def test_custom_strategies(self):
        """Should accept custom strategy list."""
        learner = StrategyLearner(strategies=["custom_strategy"])
        assert "custom_strategy" in learner.effectiveness.overall
        assert "ask_recent_example" not in learner.effectiveness.overall


class TestAnalyzeSession:
    """Tests for analyzing individual sessions."""

    def test_analyze_session_with_evidence(self):
        """Should extract strategy effectiveness from session."""
        learner = StrategyLearner()

        session = AssessmentSession(
            session_id="test-1",
            protocol_id="test-protocol",
            status="completed",
            user_context={"user_type": "analytical"},
            conversation_log=[
                {
                    "round_index": 1,
                    "strategy": "ask_recent_example",
                    "question": "Tell me about a recent situation...",
                    "response": "I was working on a project last week...",
                    "evidence": [
                        {
                            "id": "ev1",
                            "round_index": 1,
                            "source_text": "I was working...",
                            "evidence_type": "behavioral",
                            "normalized_claim": "Works on projects",
                            "mapped_dimensions": [
                                {
                                    "dimension_id": "conscientiousness",
                                    "direction": 1,
                                    "weight": 0.8,
                                    "confidence": 0.9,
                                }
                            ],
                        }
                    ],
                }
            ],
        )

        result = learner.analyze_session(session)

        assert "ask_recent_example" in result
        assert result["ask_recent_example"]["times_used"] == 1
        assert result["ask_recent_example"]["high_confidence_evidence"] == 1
        assert result["ask_recent_example"]["total_confidence"] == 0.9

    def test_analyze_session_with_low_confidence_evidence(self):
        """Should not count low confidence evidence as high confidence."""
        learner = StrategyLearner()

        session = AssessmentSession(
            session_id="test-1",
            protocol_id="test-protocol",
            status="completed",
            user_context={},
            conversation_log=[
                {
                    "round_index": 1,
                    "strategy": "ask_clarification",
                    "question": "Can you clarify?",
                    "response": "Short answer.",
                    "evidence": [
                        {
                            "id": "ev1",
                            "round_index": 1,
                            "source_text": "Short answer.",
                            "evidence_type": "behavioral",
                            "normalized_claim": "Short",
                            "mapped_dimensions": [
                                {
                                    "dimension_id": "dim1",
                                    "direction": 1,
                                    "weight": 0.5,
                                    "confidence": 0.3,  # Low confidence
                                }
                            ],
                        }
                    ],
                }
            ],
        )

        result = learner.analyze_session(session)

        assert result["ask_clarification"]["times_used"] == 1
        assert result["ask_clarification"]["high_confidence_evidence"] == 0
        assert result["ask_clarification"]["total_confidence"] == 0.3

    def test_analyze_session_no_evidence(self):
        """Should track strategy use even without evidence."""
        learner = StrategyLearner()

        session = AssessmentSession(
            session_id="test-1",
            protocol_id="test-protocol",
            status="completed",
            user_context={},
            conversation_log=[
                {
                    "round_index": 1,
                    "strategy": "ask_recent_example",
                    "question": "Tell me...",
                    "response": "I don't know.",
                    "evidence": [],
                }
            ],
        )

        result = learner.analyze_session(session)

        assert result["ask_recent_example"]["times_used"] == 1
        assert result["ask_recent_example"]["high_confidence_evidence"] == 0

    def test_analyze_session_response_length_tracking(self):
        """Should track response length patterns."""
        learner = StrategyLearner()

        session = AssessmentSession(
            session_id="test-1",
            protocol_id="test-protocol",
            status="completed",
            user_context={},
            conversation_log=[
                {
                    "round_index": 1,
                    "strategy": "ask_recent_example",
                    "question": "Tell me...",
                    "response": "This is a very detailed response with many words explaining the situation in great depth and detail with lots of information...",
                    "evidence": [],
                }
            ],
        )

        result = learner.analyze_session(session)

        assert result["ask_recent_example"]["avg_response_length"] > 0
        assert result["ask_recent_example"]["detailed_responses"] == 1


class TestGetStrategyScore:
    """Tests for getting strategy effectiveness scores."""

    def test_get_strategy_score_after_learning(self):
        """Should return effectiveness score after learning."""
        learner = StrategyLearner()

        session = AssessmentSession(
            session_id="test-1",
            protocol_id="test-protocol",
            status="completed",
            user_context={},
            conversation_log=[
                {
                    "round_index": 1,
                    "strategy": "ask_recent_example",
                    "question": "Tell me...",
                    "response": "Detailed answer...",
                    "evidence": [
                        {
                            "id": "ev1",
                            "round_index": 1,
                            "source_text": "Detailed...",
                            "evidence_type": "behavioral",
                            "normalized_claim": "Detailed",
                            "mapped_dimensions": [
                                {
                                    "dimension_id": "dim1",
                                    "direction": 1,
                                    "weight": 0.8,
                                    "confidence": 0.9,
                                }
                            ],
                        }
                    ],
                }
            ],
        )

        learner.update_from_history([session])

        assert learner.get_strategy_score("ask_recent_example") == 1.0

    def test_get_strategy_score_unknown(self):
        """Should return 0 for unknown strategy."""
        learner = StrategyLearner()
        assert learner.get_strategy_score("unknown_strategy") == 0.0


class TestRecommendStrategies:
    """Tests for strategy recommendation."""

    def test_recommend_strategies_ranked(self):
        """Should return strategies ranked by effectiveness."""
        learner = StrategyLearner()

        # Simulate learning with different effectiveness
        learner.effectiveness.overall["ask_recent_example"] = StrategyStats(
            times_used=10, high_confidence_evidence=8  # 0.8 effectiveness
        )
        learner.effectiveness.overall["ask_clarification"] = StrategyStats(
            times_used=10, high_confidence_evidence=5  # 0.5 effectiveness
        )
        learner.effectiveness.overall["ask_counterexample"] = StrategyStats(
            times_used=10, high_confidence_evidence=9  # 0.9 effectiveness
        )

        recommendations = learner.recommend_strategies()

        assert len(recommendations) == 4
        assert recommendations[0][0] == "ask_counterexample"  # Highest effectiveness
        assert recommendations[1][0] == "ask_recent_example"

    def test_recommend_strategies_with_limit(self):
        """Should return only top N strategies."""
        learner = StrategyLearner()

        learner.effectiveness.overall["ask_recent_example"] = StrategyStats(
            times_used=10, high_confidence_evidence=8
        )
        learner.effectiveness.overall["ask_clarification"] = StrategyStats(
            times_used=10, high_confidence_evidence=5
        )

        recommendations = learner.recommend_strategies(top_n=2)

        assert len(recommendations) == 2

    def test_recommend_strategies_by_user_type(self):
        """Should consider user type in recommendations."""
        learner = StrategyLearner()

        # Set up user-type specific stats
        learner.effectiveness.by_user_type["analytical"] = {
            "ask_recent_example": StrategyStats(times_used=10, high_confidence_evidence=9),
            "ask_clarification": StrategyStats(times_used=10, high_confidence_evidence=3),
        }

        recommendations = learner.recommend_strategies(user_type="analytical")

        assert recommendations[0][0] == "ask_recent_example"

    def test_recommend_strategies_by_dimension(self):
        """Should consider dimension in recommendations."""
        learner = StrategyLearner()

        # Set up dimension-specific stats
        learner.effectiveness.by_dimension["conscientiousness"] = {
            "ask_recent_example": StrategyStats(times_used=10, high_confidence_evidence=4),
            "ask_clarification": StrategyStats(times_used=10, high_confidence_evidence=8),
        }

        recommendations = learner.recommend_strategies(dimension="conscientiousness")

        assert recommendations[0][0] == "ask_clarification"

    def test_recommend_strategies_combined_context(self):
        """Should combine user type and dimension context."""
        learner = StrategyLearner()

        learner.effectiveness.by_user_type["analytical"] = {
            "ask_recent_example": StrategyStats(times_used=10, high_confidence_evidence=7),
        }
        learner.effectiveness.by_dimension["conscientiousness"] = {
            "ask_clarification": StrategyStats(times_used=10, high_confidence_evidence=9),
        }

        recommendations = learner.recommend_strategies(
            user_type="analytical", dimension="conscientiousness"
        )

        # Both strategies should be in recommendations
        strategies = [s[0] for s in recommendations]
        assert "ask_recent_example" in strategies
        assert "ask_clarification" in strategies


class TestUpdateFromHistory:
    """Tests for learning from multiple sessions."""

    def test_update_from_multiple_sessions(self):
        """Should aggregate stats from multiple sessions."""
        learner = StrategyLearner()

        sessions = [
            AssessmentSession(
                session_id=f"test-{i}",
                protocol_id="test-protocol",
                status="completed",
                user_context={"user_type": "analytical"},
                conversation_log=[
                    {
                        "round_index": 1,
                        "strategy": "ask_recent_example",
                        "question": "Tell me...",
                        "response": "Answer...",
                        "evidence": [
                            {
                                "id": f"ev{i}",
                                "round_index": 1,
                                "source_text": "Answer...",
                                "evidence_type": "behavioral",
                                "normalized_claim": "Answer",
                                "mapped_dimensions": [
                                    {
                                        "dimension_id": "dim1",
                                        "direction": 1,
                                        "weight": 0.8,
                                        "confidence": 0.9 if i < 3 else 0.3,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            )
            for i in range(5)
        ]

        learner.update_from_history(sessions)

        stats = learner.effectiveness.overall["ask_recent_example"]
        assert stats.times_used == 5
        assert stats.high_confidence_evidence == 3  # First 3 have high confidence

    def test_update_tracks_user_type(self):
        """Should track stats by user type."""
        learner = StrategyLearner()

        sessions = [
            AssessmentSession(
                session_id="test-1",
                protocol_id="test-protocol",
                status="completed",
                user_context={"user_type": "analytical"},
                conversation_log=[
                    {
                        "round_index": 1,
                        "strategy": "ask_recent_example",
                        "question": "Tell me...",
                        "response": "Answer...",
                        "evidence": [
                            {
                                "id": "ev1",
                                "round_index": 1,
                                "source_text": "Answer...",
                                "evidence_type": "behavioral",
                                "normalized_claim": "Answer",
                                "mapped_dimensions": [
                                    {
                                        "dimension_id": "dim1",
                                        "direction": 1,
                                        "weight": 0.8,
                                        "confidence": 0.9,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            ),
            AssessmentSession(
                session_id="test-2",
                protocol_id="test-protocol",
                status="completed",
                user_context={"user_type": "intuitive"},
                conversation_log=[
                    {
                        "round_index": 1,
                        "strategy": "ask_recent_example",
                        "question": "Tell me...",
                        "response": "Answer...",
                        "evidence": [
                            {
                                "id": "ev2",
                                "round_index": 1,
                                "source_text": "Answer...",
                                "evidence_type": "behavioral",
                                "normalized_claim": "Answer",
                                "mapped_dimensions": [
                                    {
                                        "dimension_id": "dim1",
                                        "direction": 1,
                                        "weight": 0.8,
                                        "confidence": 0.4,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            ),
        ]

        learner.update_from_history(sessions)

        # Check user type specific stats
        assert "analytical" in learner.effectiveness.by_user_type
        assert "intuitive" in learner.effectiveness.by_user_type

        analytical_stats = learner.effectiveness.by_user_type["analytical"]["ask_recent_example"]
        assert analytical_stats.effectiveness == 1.0

        intuitive_stats = learner.effectiveness.by_user_type["intuitive"]["ask_recent_example"]
        assert intuitive_stats.effectiveness == 0.0

    def test_update_tracks_dimensions(self):
        """Should track stats by dimension."""
        learner = StrategyLearner()

        sessions = [
            AssessmentSession(
                session_id="test-1",
                protocol_id="test-protocol",
                status="completed",
                user_context={},
                conversation_log=[
                    {
                        "round_index": 1,
                        "strategy": "ask_recent_example",
                        "question": "Tell me...",
                        "response": "Answer...",
                        "evidence": [
                            {
                                "id": "ev1",
                                "round_index": 1,
                                "source_text": "Answer...",
                                "evidence_type": "behavioral",
                                "normalized_claim": "Answer",
                                "mapped_dimensions": [
                                    {
                                        "dimension_id": "conscientiousness",
                                        "direction": 1,
                                        "weight": 0.8,
                                        "confidence": 0.9,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            ),
        ]

        learner.update_from_history(sessions)

        assert "conscientiousness" in learner.effectiveness.by_dimension


class TestUserTypeAdaptation:
    """Tests for adapting strategy selection based on user type."""

    def test_adaptation_prefers_user_type_specific(self):
        """Should prefer strategies that work for specific user type."""
        learner = StrategyLearner()

        # Overall, ask_recent_example is better
        learner.effectiveness.overall["ask_recent_example"] = StrategyStats(
            times_used=100, high_confidence_evidence=90  # 0.9
        )
        learner.effectiveness.overall["ask_clarification"] = StrategyStats(
            times_used=100, high_confidence_evidence=50  # 0.5
        )

        # But for "analytical" users, ask_clarification is better
        learner.effectiveness.by_user_type["analytical"] = {
            "ask_recent_example": StrategyStats(times_used=10, high_confidence_evidence=3),
            "ask_clarification": StrategyStats(times_used=10, high_confidence_evidence=9),
        }

        # Without user type, ask_recent_example should be first
        general_rec = learner.recommend_strategies()
        assert general_rec[0][0] == "ask_recent_example"

        # With analytical user type, ask_clarification should be first
        analytical_rec = learner.recommend_strategies(user_type="analytical")
        assert analytical_rec[0][0] == "ask_clarification"

    def test_falls_back_to_overall_when_no_user_type_data(self):
        """Should fall back to overall stats when no user type data."""
        learner = StrategyLearner()

        learner.effectiveness.overall["ask_recent_example"] = StrategyStats(
            times_used=10, high_confidence_evidence=8
        )

        recommendations = learner.recommend_strategies(user_type="unknown_type")

        # Should still return recommendations based on overall stats
        assert len(recommendations) > 0


class TestPersistence:
    """Tests for persisting and loading effectiveness data."""

    def test_to_dict(self):
        """Should convert effectiveness to dictionary."""
        learner = StrategyLearner()
        learner.effectiveness.overall["ask_recent_example"] = StrategyStats(
            times_used=10, high_confidence_evidence=8, total_confidence=7.5
        )

        data = learner.to_dict()

        assert "effectiveness" in data
        assert "strategies" in data
        assert data["effectiveness"]["overall"]["ask_recent_example"]["times_used"] == 10

    def test_from_dict(self):
        """Should load effectiveness from dictionary."""
        data = {
            "strategies": ["ask_recent_example", "ask_clarification"],
            "effectiveness": {
                "overall": {
                    "ask_recent_example": {
                        "times_used": 10,
                        "high_confidence_evidence": 8,
                        "total_confidence": 7.5,
                        "avg_response_length": 100.0,
                        "detailed_responses": 5,
                    }
                },
                "by_user_type": {},
                "by_dimension": {},
            },
        }

        learner = StrategyLearner.from_dict(data)

        stats = learner.effectiveness.overall["ask_recent_example"]
        assert stats.times_used == 10
        assert stats.high_confidence_evidence == 8
        assert stats.total_confidence == 7.5

    def test_round_trip_persistence(self):
        """Should preserve data through save/load cycle."""
        learner = StrategyLearner()
        learner.effectiveness.overall["ask_recent_example"] = StrategyStats(
            times_used=10, high_confidence_evidence=8, total_confidence=7.5
        )
        learner.effectiveness.by_user_type["analytical"] = {
            "ask_recent_example": StrategyStats(times_used=5, high_confidence_evidence=4)
        }

        data = learner.to_dict()
        restored = StrategyLearner.from_dict(data)

        assert restored.effectiveness.overall["ask_recent_example"].times_used == 10
        assert restored.effectiveness.by_user_type["analytical"]["ask_recent_example"].times_used == 5

    def test_from_dict_flat_format(self):
        """Should load from flat dictionary format (backward compatibility)."""
        data = {
            "strategies": ["ask_recent_example"],
            "overall": {
                "ask_recent_example": {
                    "times_used": 10,
                    "high_confidence_evidence": 8,
                    "total_confidence": 7.5,
                    "avg_response_length": 100.0,
                    "detailed_responses": 5,
                }
            },
            "by_user_type": {},
            "by_dimension": {},
        }

        learner = StrategyLearner.from_dict(data)

        stats = learner.effectiveness.overall["ask_recent_example"]
        assert stats.times_used == 10
        assert stats.high_confidence_evidence == 8


class TestIntegrationWithProbePlanner:
    """Tests for integration with ProbePlanner."""

    def test_learner_informs_strategy_selection(self):
        """Should be able to inform ProbePlanner strategy selection."""
        from assessment_engine.core.protocol import AssessmentProtocol, Dimension, StoppingRules

        learner = StrategyLearner()

        # Set up effectiveness data
        learner.effectiveness.overall["ask_context_boundary"] = StrategyStats(
            times_used=10, high_confidence_evidence=9  # 0.9 effectiveness
        )
        learner.effectiveness.overall["ask_recent_example"] = StrategyStats(
            times_used=10, high_confidence_evidence=5  # 0.5 effectiveness
        )

        # Get top recommendation
        recommendations = learner.recommend_strategies(top_n=1)
        top_strategy = recommendations[0][0]

        # This should be the strategy ProbePlanner would want to use
        assert top_strategy == "ask_context_boundary"

    def test_recommendations_include_scores(self):
        """Should include effectiveness scores in recommendations."""
        learner = StrategyLearner()

        learner.effectiveness.overall["ask_recent_example"] = StrategyStats(
            times_used=10, high_confidence_evidence=8
        )

        recommendations = learner.recommend_strategies()

        # Each recommendation should be a tuple of (strategy, score)
        assert len(recommendations[0]) == 2
        assert isinstance(recommendations[0][1], float)
        assert recommendations[0][1] == 0.8
