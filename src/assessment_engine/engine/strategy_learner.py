"""Strategy learning from historical assessment sessions.

This module provides functionality to learn which question strategies work best
for different user types and assessment contexts by analyzing historical session data.
"""

from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

from assessment_engine.core.session import AssessmentSession


@dataclass
class StrategyStats:
    """Statistics for a single strategy's effectiveness.

    Attributes:
        times_used: Number of times the strategy was used
        high_confidence_evidence: Count of evidence with confidence >= 0.7
        total_confidence: Sum of all evidence confidence scores
        avg_response_length: Average length of user responses
        detailed_responses: Count of responses considered "detailed"
    """

    times_used: int = 0
    high_confidence_evidence: int = 0
    total_confidence: float = 0.0
    avg_response_length: float = 0.0
    detailed_responses: int = 0
    _total_response_length: int = field(default=0, repr=False)
    _response_count: int = field(default=0, repr=False)

    @property
    def effectiveness(self) -> float:
        """Calculate effectiveness as ratio of high-confidence evidence to uses."""
        if self.times_used == 0:
            return 0.0
        return self.high_confidence_evidence / self.times_used

    @property
    def avg_confidence(self) -> float:
        """Calculate average confidence of evidence generated."""
        if self.times_used == 0:
            return 0.0
        return self.total_confidence / self.times_used

    def add_response(self, response: str) -> None:
        """Track a user response for length analysis."""
        length = len(response.split()) if response else 0
        self._total_response_length += length
        self._response_count += 1
        self.avg_response_length = self._total_response_length / self._response_count

        # Consider response "detailed" if > 20 words
        if length > 20:
            self.detailed_responses += 1

    def merge(self, other: "StrategyStats") -> "StrategyStats":
        """Merge another StrategyStats into this one."""
        merged = StrategyStats(
            times_used=self.times_used + other.times_used,
            high_confidence_evidence=self.high_confidence_evidence + other.high_confidence_evidence,
            total_confidence=self.total_confidence + other.total_confidence,
            _total_response_length=self._total_response_length + other._total_response_length,
            _response_count=self._response_count + other._response_count,
        )
        merged.detailed_responses = self.detailed_responses + other.detailed_responses
        if merged._response_count > 0:
            merged.avg_response_length = merged._total_response_length / merged._response_count
        return merged

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "times_used": self.times_used,
            "high_confidence_evidence": self.high_confidence_evidence,
            "total_confidence": self.total_confidence,
            "avg_response_length": self.avg_response_length,
            "detailed_responses": self.detailed_responses,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StrategyStats":
        """Create StrategyStats from dictionary."""
        stats = cls(
            times_used=data.get("times_used", 0),
            high_confidence_evidence=data.get("high_confidence_evidence", 0),
            total_confidence=data.get("total_confidence", 0.0),
        )
        stats.avg_response_length = data.get("avg_response_length", 0.0)
        stats.detailed_responses = data.get("detailed_responses", 0)
        return stats


@dataclass
class StrategyEffectiveness:
    """Container for strategy effectiveness data across different contexts.

    Tracks effectiveness overall, by user type, and by dimension.
    """

    overall: dict[str, StrategyStats] = field(default_factory=dict)
    by_user_type: dict[str, dict[str, StrategyStats]] = field(default_factory=dict)
    by_dimension: dict[str, dict[str, StrategyStats]] = field(default_factory=dict)

    def get_strategy_score(self, strategy_name: str) -> float:
        """Get effectiveness score for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Effectiveness score (0-1), or 0 if strategy not found
        """
        if strategy_name in self.overall:
            return self.overall[strategy_name].effectiveness
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "overall": {name: stats.to_dict() for name, stats in self.overall.items()},
            "by_user_type": {
                user_type: {name: stats.to_dict() for name, stats in strategies.items()}
                for user_type, strategies in self.by_user_type.items()
            },
            "by_dimension": {
                dim: {name: stats.to_dict() for name, stats in strategies.items()}
                for dim, strategies in self.by_dimension.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StrategyEffectiveness":
        """Create StrategyEffectiveness from dictionary."""
        effectiveness = cls()

        if "overall" in data:
            effectiveness.overall = {
                name: StrategyStats.from_dict(stats) for name, stats in data["overall"].items()
            }

        if "by_user_type" in data:
            effectiveness.by_user_type = {
                user_type: {
                    name: StrategyStats.from_dict(stats) for name, stats in strategies.items()
                }
                for user_type, strategies in data.get("by_user_type", {}).items()
            }

        if "by_dimension" in data:
            effectiveness.by_dimension = {
                dim: {name: StrategyStats.from_dict(stats) for name, stats in strategies.items()}
                for dim, strategies in data.get("by_dimension", {}).items()
            }

        return effectiveness


class StrategyLearner:
    """Learn which question strategies work best from historical sessions.

    Analyzes historical assessment sessions to calculate strategy effectiveness
    and provide recommendations for strategy selection based on context.

    Attributes:
        effectiveness: StrategyEffectiveness data container
        strategies: List of strategy names being tracked
    """

    DEFAULT_STRATEGIES: ClassVar[list[str]] = [
        "ask_recent_example",
        "ask_clarification",
        "ask_counterexample",
        "ask_context_boundary",
    ]

    HIGH_CONFIDENCE_THRESHOLD = 0.7
    DETAILED_RESPONSE_THRESHOLD = 20

    def __init__(self, strategies: Optional[list[str]] = None):
        """Initialize the strategy learner.

        Args:
            strategies: List of strategy names to track. Uses defaults if None.
        """
        self.strategies = strategies or self.DEFAULT_STRATEGIES.copy()
        self.effectiveness = StrategyEffectiveness()

        # Initialize stats for all strategies
        for strategy in self.strategies:
            self.effectiveness.overall[strategy] = StrategyStats()

    def analyze_session(self, session: AssessmentSession) -> dict[str, dict[str, Any]]:
        """Extract strategy effectiveness data from a single session.

        Args:
            session: AssessmentSession to analyze

        Returns:
            Dictionary mapping strategy names to their stats from this session
        """
        results: dict[str, dict[str, Any]] = {}

        for entry in session.conversation_log:
            strategy = entry.get("strategy")
            if not strategy:
                continue

            if strategy not in results:
                results[strategy] = {
                    "times_used": 0,
                    "high_confidence_evidence": 0,
                    "total_confidence": 0.0,
                    "avg_response_length": 0.0,
                    "detailed_responses": 0,
                }

            results[strategy]["times_used"] += 1

            # Track response length
            response = entry.get("response", "")
            response_length = len(response.split()) if response else 0
            results[strategy]["avg_response_length"] = response_length

            if response_length > self.DETAILED_RESPONSE_THRESHOLD:
                results[strategy]["detailed_responses"] += 1

            # Analyze evidence
            evidence_list = entry.get("evidence", [])
            for evidence_data in evidence_list:
                mapped_dimensions = evidence_data.get("mapped_dimensions", [])
                for mapping in mapped_dimensions:
                    confidence = mapping.get("confidence", 0.0)
                    results[strategy]["total_confidence"] += confidence

                    if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                        results[strategy]["high_confidence_evidence"] += 1

        return results

    def get_strategy_score(self, strategy_name: str) -> float:
        """Get the effectiveness score for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Effectiveness score between 0 and 1
        """
        return self.effectiveness.get_strategy_score(strategy_name)

    def recommend_strategies(
        self,
        user_type: Optional[str] = None,
        dimension: Optional[str] = None,
        top_n: Optional[int] = None,
    ) -> list[tuple[str, float]]:
        """Get ranked strategy recommendations for a given context.

        Ranks strategies by effectiveness, considering user type and dimension
        context when available.

        Args:
            user_type: Optional user type for context-specific recommendations
            dimension: Optional dimension ID for context-specific recommendations
            top_n: Optional limit on number of recommendations

        Returns:
            List of (strategy_name, effectiveness_score) tuples, ranked by score
        """
        scores: dict[str, float] = {}

        # Start with overall scores
        for strategy in self.strategies:
            scores[strategy] = self.effectiveness.overall.get(
                strategy, StrategyStats()
            ).effectiveness

        # Boost scores based on user type data if available
        if user_type and user_type in self.effectiveness.by_user_type:
            user_type_stats = self.effectiveness.by_user_type[user_type]
            for strategy, stats in user_type_stats.items():
                if strategy in scores:
                    # Weight user-type specific data higher
                    scores[strategy] = scores[strategy] * 0.3 + stats.effectiveness * 0.7

        # Boost scores based on dimension data if available
        if dimension and dimension in self.effectiveness.by_dimension:
            dim_stats = self.effectiveness.by_dimension[dimension]
            for strategy, stats in dim_stats.items():
                if strategy in scores:
                    # Combine with dimension-specific data
                    scores[strategy] = scores[strategy] * 0.5 + stats.effectiveness * 0.5

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if top_n:
            ranked = ranked[:top_n]

        return ranked

    def update_from_history(self, sessions: list[AssessmentSession]) -> None:
        """Learn from multiple historical sessions.

        Analyzes all sessions and updates effectiveness statistics.

        Args:
            sessions: List of AssessmentSession objects to learn from
        """
        for session in sessions:
            session_stats = self.analyze_session(session)
            user_type = session.user_context.get("user_type")

            for strategy, stats_data in session_stats.items():
                # Ensure strategy exists in overall
                if strategy not in self.effectiveness.overall:
                    self.effectiveness.overall[strategy] = StrategyStats()
                    if strategy not in self.strategies:
                        self.strategies.append(strategy)

                # Update overall stats
                new_stats = StrategyStats(
                    times_used=stats_data["times_used"],
                    high_confidence_evidence=stats_data["high_confidence_evidence"],
                    total_confidence=stats_data["total_confidence"],
                )
                new_stats.avg_response_length = stats_data["avg_response_length"]
                new_stats.detailed_responses = stats_data["detailed_responses"]

                self.effectiveness.overall[strategy] = self.effectiveness.overall[strategy].merge(
                    new_stats
                )

                # Update user type specific stats
                if user_type:
                    if user_type not in self.effectiveness.by_user_type:
                        self.effectiveness.by_user_type[user_type] = {}
                    if strategy not in self.effectiveness.by_user_type[user_type]:
                        self.effectiveness.by_user_type[user_type][strategy] = StrategyStats()

                    self.effectiveness.by_user_type[user_type][strategy] = (
                        self.effectiveness.by_user_type[user_type][strategy].merge(new_stats)
                    )

                # Update dimension specific stats
                for entry in session.conversation_log:
                    if entry.get("strategy") != strategy:
                        continue

                    for evidence_data in entry.get("evidence", []):
                        for mapping in evidence_data.get("mapped_dimensions", []):
                            dim_id = mapping.get("dimension_id")
                            if dim_id:
                                if dim_id not in self.effectiveness.by_dimension:
                                    self.effectiveness.by_dimension[dim_id] = {}
                                if strategy not in self.effectiveness.by_dimension[dim_id]:
                                    self.effectiveness.by_dimension[dim_id][strategy] = (
                                        StrategyStats()
                                    )

                                # Create dimension-specific stats
                                dim_stats = StrategyStats(
                                    times_used=1,
                                    high_confidence_evidence=1
                                    if mapping.get("confidence", 0)
                                    >= self.HIGH_CONFIDENCE_THRESHOLD
                                    else 0,
                                    total_confidence=mapping.get("confidence", 0.0),
                                )

                                self.effectiveness.by_dimension[dim_id][strategy] = (
                                    self.effectiveness.by_dimension[dim_id][strategy].merge(
                                        dim_stats
                                    )
                                )

    def to_dict(self) -> dict[str, Any]:
        """Convert learner state to dictionary for persistence.

        Returns:
            Dictionary containing all effectiveness data
        """
        return {
            "strategies": self.strategies,
            "effectiveness": self.effectiveness.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StrategyLearner":
        """Create StrategyLearner from dictionary.

        Args:
            data: Dictionary from to_dict()

        Returns:
            Restored StrategyLearner instance
        """
        strategies = data.get("strategies", cls.DEFAULT_STRATEGIES)
        learner = cls(strategies=strategies)

        if "effectiveness" in data:
            learner.effectiveness = StrategyEffectiveness.from_dict(data["effectiveness"])
        elif "overall" in data:
            # Support flat format for backward compatibility
            learner.effectiveness = StrategyEffectiveness.from_dict(data)

        return learner
