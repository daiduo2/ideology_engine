from typing import Optional

from assessment_engine.core.contradiction import Contradiction
from assessment_engine.core.evidence import Evidence
from assessment_engine.core.state import AssessmentState, Coverage, DimensionState


class StateUpdater:
    """Pure code implementation of state updates. No LLM calls here."""

    def __init__(self, learning_rate: float = 0.1):
        self.learning_rate = learning_rate

    def update_state(
        self,
        state: AssessmentState,
        new_evidence: list[Evidence],
        round_index: int,
        coverage_targets: Optional[list[str]] = None,
        new_contradictions: Optional[list[Contradiction]] = None,
    ) -> AssessmentState:
        """Update assessment state based on new evidence."""
        # Update dimensions
        new_dimensions = dict(state.dimensions)

        for evidence in new_evidence:
            for mapping in evidence.mapped_dimensions:
                dim_id = mapping.dimension_id

                if dim_id not in new_dimensions:
                    new_dimensions[dim_id] = DimensionState()

                dim_state = new_dimensions[dim_id]

                # Calculate delta
                delta = mapping.direction * mapping.weight * self.learning_rate * mapping.confidence

                # Update score with bounds checking
                new_score = max(0.0, min(1.0, dim_state.score + delta))

                # Update confidence based on evidence quality
                confidence_delta = 0.1 * mapping.confidence
                new_confidence = min(1.0, dim_state.confidence + confidence_delta)

                new_dimensions[dim_id] = DimensionState(
                    score=new_score,
                    confidence=new_confidence,
                    evidence_count=dim_state.evidence_count + 1,
                    last_updated_at_round=round_index,
                )

        # Update coverage
        new_coverage = state.coverage.model_copy()
        if coverage_targets:
            for target in coverage_targets:
                for evidence in new_evidence:
                    if target in evidence.tags:
                        setattr(new_coverage, target, True)

        # Update evidence IDs
        new_evidence_ids = state.evidence_ids + [e.id for e in new_evidence]

        # Update contradiction IDs
        new_contradiction_ids = list(state.contradiction_ids)
        if new_contradictions:
            new_contradiction_ids.extend([c.id for c in new_contradictions])

        # Generate open questions based on state
        open_questions = self._generate_open_questions(
            new_dimensions, new_coverage, coverage_targets or []
        )

        return AssessmentState(
            dimensions=new_dimensions,
            coverage=new_coverage,
            evidence_ids=new_evidence_ids,
            contradiction_ids=new_contradiction_ids,
            open_questions=open_questions,
            recommended_next_target=None,  # Set by ProbePlanner
            termination=state.termination,
        )

    def _generate_open_questions(
        self,
        dimensions: dict,
        coverage: Coverage,
        coverage_targets: list[str],
    ) -> list[str]:
        """Generate list of open questions based on current state."""
        open_questions = []

        # Check for low confidence dimensions
        for dim_id, dim_state in dimensions.items():
            if dim_state.confidence < 0.5:
                open_questions.append(f"{dim_id} needs more evidence")

        # Check for uncovered targets
        for target in coverage_targets:
            if not getattr(coverage, target, False):
                open_questions.append(f"{target} not yet covered")

        return open_questions

    def calculate_coverage_ratio(self, coverage: Coverage, targets: list[str]) -> float:
        """Calculate coverage ratio."""
        if not targets:
            return 1.0

        covered = sum(1 for t in targets if getattr(coverage, t, False))
        return covered / len(targets)

    def calculate_average_confidence(self, state: AssessmentState) -> float:
        """Calculate average confidence across all dimensions."""
        if not state.dimensions:
            return 0.0

        confidences = [d.confidence for d in state.dimensions.values()]
        return sum(confidences) / len(confidences)
