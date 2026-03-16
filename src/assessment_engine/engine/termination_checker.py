from typing import List, Optional
from assessment_engine.core.protocol import StoppingRules
from assessment_engine.core.state import AssessmentState, TerminationStatus
from assessment_engine.core.contradiction import Contradiction


class TerminationChecker:
    """Check if assessment should terminate based on stopping rules."""

    def __init__(self, stopping_rules: StoppingRules):
        self.rules = stopping_rules

    def check(
        self,
        state: AssessmentState,
        round_index: int,
        coverage_targets: Optional[List[str]] = None,
        unresolved_contradictions: Optional[List[Contradiction]] = None,
    ) -> TerminationStatus:
        """Check if termination conditions are met."""
        reasons = []
        eligible = True

        # Check min rounds
        if round_index < self.rules.min_rounds:
            eligible = False
            reasons.append(f"min_rounds not met: {round_index} < {self.rules.min_rounds}")

        # Check max rounds (forced termination)
        if round_index >= self.rules.max_rounds:
            return TerminationStatus(
                eligible=True,
                reasons=[f"max_rounds reached: {round_index}"],
            )

        # Check coverage
        if coverage_targets:
            coverage_ratio = self._calculate_coverage_ratio(state, coverage_targets)
            if coverage_ratio < self.rules.min_coverage_ratio:
                eligible = False
                reasons.append(
                    f"coverage_ratio too low: {coverage_ratio:.2f} < {self.rules.min_coverage_ratio}"
                )

        # Check average confidence
        avg_confidence = self._calculate_average_confidence(state)
        if avg_confidence < self.rules.target_confidence:
            eligible = False
            reasons.append(
                f"avg_confidence too low: {avg_confidence:.2f} < {self.rules.target_confidence}"
            )

        # Check unresolved contradictions
        if unresolved_contradictions:
            severe = [c for c in unresolved_contradictions if c.severity == "high" and c.needs_followup]
            if severe:
                eligible = False
                reasons.append(f"unresolved severe contradictions: {len(severe)}")

        if eligible and not reasons:
            reasons.append("all stopping conditions met")

        return TerminationStatus(eligible=eligible, reasons=reasons)

    def _calculate_coverage_ratio(self, state: AssessmentState, targets: List[str]) -> float:
        """Calculate ratio of covered targets."""
        if not targets:
            return 1.0

        covered = sum(1 for t in targets if getattr(state.coverage, t, False))
        return covered / len(targets)

    def _calculate_average_confidence(self, state: AssessmentState) -> float:
        """Calculate average confidence across dimensions."""
        if not state.dimensions:
            return 0.0

        confidences = [d.confidence for d in state.dimensions.values()]
        return sum(confidences) / len(confidences)
