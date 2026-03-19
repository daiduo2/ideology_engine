"""Cross-dimension correlation analysis for the Assessment Engine.

This module provides functionality to detect relationships between dimensions,
analyze correlations, detect contradictions, and group related dimensions.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from assessment_engine.core.evidence import Evidence
from assessment_engine.core.state import AssessmentState


class DimensionCorrelation(BaseModel):
    """Represents correlation between two dimensions.

    Attributes:
        dimension_a: First dimension ID
        dimension_b: Second dimension ID
        coefficient: Correlation coefficient (-1 to +1)
        shared_evidence_ids: List of evidence IDs affecting both dimensions
        confidence: Overall confidence in the correlation
    """

    dimension_a: str
    dimension_b: str
    coefficient: float = Field(..., ge=-1, le=1)
    shared_evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)

    @property
    def dimension_pair(self) -> tuple[str, str]:
        """Return sorted dimension pair for consistent lookup."""
        return tuple(sorted([self.dimension_a, self.dimension_b]))


class CorrelationMatrix(BaseModel):
    """Matrix of correlations between all dimension pairs.

    Attributes:
        dimension_ids: List of all dimension IDs in the matrix
        correlations: Dictionary mapping dimension pairs to correlations
    """

    dimension_ids: list[str]
    correlations: dict[tuple[str, str], DimensionCorrelation] = Field(default_factory=dict)

    def get_correlation(self, dim_a: str, dim_b: str) -> Optional[DimensionCorrelation]:
        """Get correlation between two dimensions."""
        pair_key = tuple(sorted([dim_a, dim_b]))
        return self.correlations.get(pair_key)

    def get_correlations_for_dimension(self, dim_id: str) -> list[DimensionCorrelation]:
        """Get all correlations involving a specific dimension."""
        return [corr for pair, corr in self.correlations.items() if dim_id in pair]


class EvidenceContradiction(BaseModel):
    """Represents a contradiction found within a single evidence.

    Attributes:
        evidence_id: ID of the evidence containing contradiction
        dimension_pair: Tuple of dimension IDs with opposing effects
        contradiction_type: Type of contradiction detected
        description: Human-readable description of the contradiction
    """

    evidence_id: str
    dimension_pair: tuple[str, str]
    contradiction_type: str  # e.g., "opposing_effects"
    description: str = ""


class CorrelationAnalyzer:
    """Analyzes correlations between assessment dimensions.

    This class provides methods to:
    - Calculate correlation coefficients between dimension pairs
    - Detect contradictions (same evidence supporting/opposing different dimensions)
    - Group dimensions into clusters based on correlation strength
    - Generate insights for reports
    """

    def __init__(self, correlation_threshold: float = 0.3):
        """Initialize the correlation analyzer.

        Args:
            correlation_threshold: Minimum correlation coefficient to consider significant
        """
        self.correlation_threshold = correlation_threshold

    def analyze_correlations(
        self, state: AssessmentState, evidence_list: list[Evidence]
    ) -> CorrelationMatrix:
        """Analyze correlations between dimensions based on evidence.

        This method examines evidence that affects multiple dimensions and
        calculates correlation coefficients based on the direction and strength
        of effects.

        Args:
            state: Current assessment state with dimension information
            evidence_list: List of evidence to analyze

        Returns:
            CorrelationMatrix containing all pairwise correlations
        """
        dimension_ids = list(state.dimensions.keys())
        correlations: dict[tuple[str, str], DimensionCorrelation] = {}

        # Track evidence effects per dimension pair
        pair_evidence: dict[tuple[str, str], list[tuple[str, float, float]]] = {}

        for evidence in evidence_list:
            if len(evidence.mapped_dimensions) < 2:
                continue

            # Get all dimension pairs from this evidence
            for i, mapping_a in enumerate(evidence.mapped_dimensions):
                for mapping_b in evidence.mapped_dimensions[i + 1 :]:
                    dim_a = mapping_a.dimension_id
                    dim_b = mapping_b.dimension_id

                    if dim_a not in dimension_ids or dim_b not in dimension_ids:
                        continue

                    pair_key = tuple(sorted([dim_a, dim_b]))

                    # Calculate the correlation contribution from this evidence
                    # Positive if both directions agree, negative if they oppose
                    correlation_sign = mapping_a.direction * mapping_b.direction
                    weight = min(mapping_a.weight, mapping_b.weight)
                    confidence = min(mapping_a.confidence, mapping_b.confidence)
                    correlation_contribution = correlation_sign * weight * confidence

                    if pair_key not in pair_evidence:
                        pair_evidence[pair_key] = []
                    pair_evidence[pair_key].append(
                        (evidence.id, correlation_contribution, confidence)
                    )

        # Calculate final correlation coefficients
        for pair_key, evidence_data in pair_evidence.items():
            dim_a, dim_b = pair_key

            # Calculate weighted average correlation contribution
            total_weight = sum(conf for _, _, conf in evidence_data)
            if total_weight == 0:
                continue

            weighted_sum = sum(contrib * conf for _, contrib, conf in evidence_data)
            base_coefficient = weighted_sum / total_weight

            # Scale coefficient based on agreement among evidence
            # When multiple evidence items agree, the correlation is stronger
            if len(evidence_data) > 1:
                # Calculate agreement factor: how consistent are the contributions?
                contributions = [contrib for _, contrib, _ in evidence_data]
                signs = [1 if c > 0 else -1 if c < 0 else 0 for c in contributions]
                sign_agreement = abs(sum(signs)) / len(signs)  # 0 to 1, 1 = perfect agreement

                # Boost coefficient based on agreement and evidence count
                # More evidence with high agreement = stronger correlation
                agreement_boost = 1.0 + (sign_agreement * min(0.5, (len(evidence_data) - 1) * 0.15))
                coefficient = base_coefficient * agreement_boost
            else:
                coefficient = base_coefficient

            # Clamp to [-1, 1]
            coefficient = max(-1.0, min(1.0, coefficient))

            # Calculate overall confidence based on evidence count and quality
            avg_confidence = sum(conf for _, _, conf in evidence_data) / len(evidence_data)
            evidence_boost = min(
                0.3, len(evidence_data) * 0.05
            )  # More evidence = higher confidence
            confidence = min(1.0, avg_confidence + evidence_boost)

            correlations[pair_key] = DimensionCorrelation(
                dimension_a=dim_a,
                dimension_b=dim_b,
                coefficient=coefficient,
                shared_evidence_ids=[eid for eid, _, _ in evidence_data],
                confidence=confidence,
            )

        return CorrelationMatrix(dimension_ids=dimension_ids, correlations=correlations)

    def detect_contradictions(self, evidence_list: list[Evidence]) -> list[EvidenceContradiction]:
        """Detect contradictions within evidence.

        A contradiction occurs when the same evidence supports one dimension
        but contradicts another (opposite directions).

        Args:
            evidence_list: List of evidence to analyze

        Returns:
            List of detected contradictions
        """
        contradictions: list[EvidenceContradiction] = []

        for evidence in evidence_list:
            if len(evidence.mapped_dimensions) < 2:
                continue

            # Check all pairs of dimensions in this evidence
            for i, mapping_a in enumerate(evidence.mapped_dimensions):
                for mapping_b in evidence.mapped_dimensions[i + 1 :]:
                    # Check for opposing effects
                    if mapping_a.direction * mapping_b.direction < 0:
                        dim_a = mapping_a.dimension_id
                        dim_b = mapping_b.dimension_id

                        contradiction = EvidenceContradiction(
                            evidence_id=evidence.id,
                            dimension_pair=tuple(sorted([dim_a, dim_b])),
                            contradiction_type="opposing_effects",
                            description=(
                                f"Evidence '{evidence.id}' positively affects "
                                f"{dim_a if mapping_a.direction > 0 else dim_b} "
                                f"but negatively affects "
                                f"{dim_b if mapping_a.direction > 0 else dim_a}"
                            ),
                        )
                        contradictions.append(contradiction)

        return contradictions

    def get_dimension_clusters(self, matrix: CorrelationMatrix) -> list[list[str]]:
        """Group dimensions into clusters based on positive correlations.

        Dimensions with strong positive correlations are grouped together.
        Uses a simple connected-components approach.

        Args:
            matrix: Correlation matrix to analyze

        Returns:
            List of dimension clusters (each cluster is a list of dimension IDs)
        """
        # Build adjacency list for positive correlations above threshold
        adjacency: dict[str, set[str]] = {dim: set() for dim in matrix.dimension_ids}

        for pair_key, correlation in matrix.correlations.items():
            if (
                correlation.coefficient >= self.correlation_threshold
                and correlation.coefficient > 0
            ):
                dim_a, dim_b = pair_key
                adjacency[dim_a].add(dim_b)
                adjacency[dim_b].add(dim_a)

        # Find connected components using BFS
        visited: set[str] = set()
        clusters: list[list[str]] = []

        for dim in matrix.dimension_ids:
            if dim in visited:
                continue

            # BFS to find all connected dimensions
            cluster: list[str] = []
            queue = [dim]
            visited.add(dim)

            while queue:
                current = queue.pop(0)
                cluster.append(current)

                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            # Only include clusters with 2+ dimensions
            if len(cluster) >= 2:
                clusters.append(cluster)

        return clusters

    def get_strong_correlations(
        self, matrix: CorrelationMatrix, threshold: float = 0.5
    ) -> list[DimensionCorrelation]:
        """Get correlations above a specified threshold.

        Args:
            matrix: Correlation matrix to analyze
            threshold: Minimum absolute correlation coefficient

        Returns:
            List of strong correlations
        """
        return [corr for corr in matrix.correlations.values() if abs(corr.coefficient) >= threshold]

    def generate_correlation_insights(self, matrix: CorrelationMatrix) -> str:
        """Generate human-readable insights about correlations.

        Args:
            matrix: Correlation matrix to analyze

        Returns:
            String containing correlation insights
        """
        if not matrix.correlations:
            return "No correlations detected between dimensions."

        strong_positive = [corr for corr in matrix.correlations.values() if corr.coefficient >= 0.5]
        strong_negative = [
            corr for corr in matrix.correlations.values() if corr.coefficient <= -0.5
        ]

        insights_parts: list[str] = []

        if strong_positive:
            insights_parts.append(
                f"Found {len(strong_positive)} strong positive correlation(s): "
                + ", ".join(
                    f"{c.dimension_a}-{c.dimension_b} ({c.coefficient:.2f})"
                    for c in strong_positive
                )
            )

        if strong_negative:
            insights_parts.append(
                f"Found {len(strong_negative)} strong negative correlation(s): "
                + ", ".join(
                    f"{c.dimension_a}-{c.dimension_b} ({c.coefficient:.2f})"
                    for c in strong_negative
                )
            )

        if not insights_parts:
            insights_parts.append(
                "No strong correlations detected. Dimension relationships are moderate or weak."
            )

        return " ".join(insights_parts)

    def update_state_with_correlations(
        self, state: AssessmentState, evidence_list: list[Evidence]
    ) -> AssessmentState:
        """Update assessment state with correlation data.

        This method analyzes correlations and adds the correlation matrix
        to the state's coverage field for later access.

        Args:
            state: Current assessment state
            evidence_list: List of evidence to analyze

        Returns:
            Updated assessment state with correlation data
        """
        matrix = self.analyze_correlations(state, evidence_list)

        # Create new coverage with correlation data
        coverage_data = state.coverage.model_dump()
        coverage_data["correlation_matrix"] = matrix.model_dump()
        coverage_data["dimension_clusters"] = self.get_dimension_clusters(matrix)

        new_coverage = state.coverage.model_copy(update=coverage_data)

        return AssessmentState(
            dimensions=state.dimensions,
            coverage=new_coverage,
            evidence_ids=state.evidence_ids,
            contradiction_ids=state.contradiction_ids,
            open_questions=state.open_questions,
            recommended_next_target=state.recommended_next_target,
            termination=state.termination,
        )

    def get_report_context(self, matrix: CorrelationMatrix) -> dict[str, Any]:
        """Generate report context with correlation information.

        Args:
            matrix: Correlation matrix to analyze

        Returns:
            Dictionary with correlation data for report generation
        """
        clusters = self.get_dimension_clusters(matrix)
        strong_correlations = self.get_strong_correlations(matrix)

        return {
            "correlations": [
                {
                    "dimensions": list(pair),
                    "coefficient": corr.coefficient,
                    "confidence": corr.confidence,
                    "evidence_count": len(corr.shared_evidence_ids),
                }
                for pair, corr in matrix.correlations.items()
            ],
            "clusters": clusters,
            "strong_correlations": [
                {
                    "dimensions": corr.dimension_pair,
                    "coefficient": corr.coefficient,
                    "interpretation": self._interpret_correlation(corr.coefficient),
                }
                for corr in strong_correlations
            ],
            "contradictions": self._find_correlation_contradictions(matrix),
        }

    def _interpret_correlation(self, coefficient: float) -> str:
        """Provide human-readable interpretation of correlation coefficient."""
        abs_coef = abs(coefficient)
        direction = "positive" if coefficient > 0 else "negative"

        if abs_coef >= 0.8:
            strength = "very strong"
        elif abs_coef >= 0.6:
            strength = "strong"
        elif abs_coef >= 0.4:
            strength = "moderate"
        elif abs_coef >= 0.2:
            strength = "weak"
        else:
            strength = "very weak"

        return f"{strength} {direction}"

    def _find_correlation_contradictions(self, matrix: CorrelationMatrix) -> list[dict[str, Any]]:
        """Find dimensions with conflicting correlation patterns."""
        contradictions: list[dict[str, Any]] = []

        # Look for dimensions that have both positive and negative correlations
        for dim in matrix.dimension_ids:
            related = matrix.get_correlations_for_dimension(dim)
            positive = [c for c in related if c.coefficient > 0.3]
            negative = [c for c in related if c.coefficient < -0.3]

            if positive and negative:
                contradictions.append(
                    {
                        "dimension": dim,
                        "positive_with": [
                            c.dimension_b if c.dimension_a == dim else c.dimension_a
                            for c in positive
                        ],
                        "negative_with": [
                            c.dimension_b if c.dimension_a == dim else c.dimension_a
                            for c in negative
                        ],
                        "description": f"{dim} shows both positive and negative correlations with other dimensions",
                    }
                )

        return contradictions
