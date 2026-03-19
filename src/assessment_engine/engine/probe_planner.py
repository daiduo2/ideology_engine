from typing import Optional

from assessment_engine.core.contradiction import Contradiction
from assessment_engine.core.protocol import AssessmentProtocol
from assessment_engine.core.state import AssessmentState, NextTarget


class ProbePlanner:
    """Determine what to probe next based on current state."""

    def __init__(self, protocol: AssessmentProtocol):
        self.protocol = protocol

    def plan_next(
        self,
        state: AssessmentState,
        coverage_targets: Optional[list[str]] = None,
        unresolved_contradictions: Optional[list[Contradiction]] = None,
    ) -> NextTarget:
        """
        Determine the next probing target.

        Priority:
        1. Coverage gaps
        2. Severe contradictions
        3. Low confidence dimensions
        4. Ambiguities
        """
        # Priority 1: Coverage gaps
        if coverage_targets:
            for target in coverage_targets:
                if not getattr(state.coverage, target, False):
                    return NextTarget(
                        type="coverage_gap",
                        target=target,
                        reason=f"{target} not yet covered",
                        recommended_strategy=self._select_strategy_for_coverage(target),
                    )

        # Priority 2: Severe contradictions
        if unresolved_contradictions:
            severe = [
                c for c in unresolved_contradictions if c.severity == "high" and c.needs_followup
            ]
            if severe:
                return NextTarget(
                    type="contradiction",
                    target=severe[0].id,
                    reason=f"Unresolved severe contradiction in {severe[0].related_dimension_ids}",
                    recommended_strategy="ask_clarification",
                )

        # Priority 3: Low confidence dimensions
        low_confidence_dims = [
            (dim_id, dim_state)
            for dim_id, dim_state in state.dimensions.items()
            if dim_state.confidence < 0.5
        ]

        if low_confidence_dims:
            # Pick the one with lowest confidence
            dim_id, dim_state = min(low_confidence_dims, key=lambda x: x[1].confidence)
            return NextTarget(
                type="dimension_uncertainty",
                target=dim_id,
                reason=f"Low confidence: {dim_state.confidence:.2f}",
                recommended_strategy="ask_recent_example",
            )

        # Priority 4: Ambiguities from open questions
        if state.open_questions:
            return NextTarget(
                type="ambiguity",
                target="general",
                reason=state.open_questions[0],
                recommended_strategy="ask_clarification",
            )

        # Default: continue with general exploration
        return NextTarget(
            type="coverage_gap",
            target=coverage_targets[0] if coverage_targets else "general",
            reason="Continuing exploration",
            recommended_strategy="ask_recent_example",
        )

    def _select_strategy_for_coverage(self, target: str) -> str:
        """Select appropriate question strategy for coverage target."""
        strategy_map = {
            "self_description": "ask_context_boundary",
            "recent_example": "ask_recent_example",
            "decision_process": "ask_recent_example",
            "social_context": "ask_context_boundary",
            "conflict_response": "ask_counterexample",
        }
        return strategy_map.get(target, "ask_recent_example")
