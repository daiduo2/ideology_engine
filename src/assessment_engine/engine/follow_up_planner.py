from dataclasses import dataclass
from typing import List, Literal
import re


@dataclass
class DensityAnalysis:
    """Analysis of answer information density."""

    word_count: int
    word_count_category: Literal["short", "medium", "long"]
    specific_example_count: int
    emotional_marker_count: int
    emotional_markers_found: List[str]
    density_score: float


@dataclass
class FollowUpDecision:
    """Decision about follow-up questions."""

    follow_up_count: int
    density_score: float
    reason: Literal["low_density", "medium_density", "high_density"]
    suggested_questions: List[str]


class FollowUpPlanner:
    """Plan follow-up questions based on answer quality."""

    # Chinese example markers
    EXAMPLE_MARKERS = ["比如", "例如", "像", "举例来说", "拿...来说", "就如"]

    # Chinese emotional markers (程度副词)
    EMOTIONAL_MARKERS = [
        "非常",
        "特别",
        "有点",
        "十分",
        "极其",
        "相当",
        "很",
        "太",
        "最",
        "更",
        "比较",
        "稍微",
        "略微",
        "格外",
        "分外",
        "尤其",
        "越发",
        "更加",
        "越来越",
    ]

    # Question templates for different follow-up types
    EXAMPLE_QUESTIONS = [
        "能否举一个具体的例子？",
        "最近有相关的经历可以分享吗？",
        "能描述一下具体的情况吗？",
        "当时发生了什么具体的事情？",
    ]

    CLARIFICATION_QUESTIONS = [
        "能详细说说你的想法吗？",
        "为什么会有这样的感受？",
        "具体是指哪方面呢？",
        "能否再多说一些细节？",
    ]

    def __init__(self):
        pass

    def analyze_density(self, answer: str) -> DensityAnalysis:
        """
        Analyze the information density of an answer.

        Args:
            answer: The user's answer text

        Returns:
            DensityAnalysis with computed metrics
        """
        if not answer or not answer.strip():
            return DensityAnalysis(
                word_count=0,
                word_count_category="short",
                specific_example_count=0,
                emotional_marker_count=0,
                emotional_markers_found=[],
                density_score=0.0,
            )

        # Word count (for Chinese, count characters; for English, count words)
        # Remove punctuation but keep Chinese characters and alphanumeric
        cleaned_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', answer)

        # Count Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', cleaned_text))

        # Count English words (sequences of alphanumeric)
        english_words = len(re.findall(r'[a-zA-Z0-9]+', cleaned_text))

        # Total word count: Chinese characters + English words
        word_count = chinese_chars + english_words

        # Determine word count category
        if word_count < 20:
            word_count_category: Literal["short", "medium", "long"] = "short"
        elif word_count <= 100:
            word_count_category = "medium"
        else:
            word_count_category = "long"

        # Count specific examples
        specific_example_count = 0
        for marker in self.EXAMPLE_MARKERS:
            specific_example_count += answer.count(marker)

        # Count emotional markers
        emotional_markers_found = []
        for marker in self.EMOTIONAL_MARKERS:
            if marker in answer:
                emotional_markers_found.append(marker)
        emotional_marker_count = len(emotional_markers_found)

        # Calculate density score (0-1)
        density_score = self._calculate_density_score(
            word_count=word_count,
            word_count_category=word_count_category,
            specific_example_count=specific_example_count,
            emotional_marker_count=emotional_marker_count,
        )

        return DensityAnalysis(
            word_count=word_count,
            word_count_category=word_count_category,
            specific_example_count=specific_example_count,
            emotional_marker_count=emotional_marker_count,
            emotional_markers_found=emotional_markers_found,
            density_score=density_score,
        )

    def _calculate_density_score(
        self,
        word_count: int,
        word_count_category: Literal["short", "medium", "long"],
        specific_example_count: int,
        emotional_marker_count: int,
    ) -> float:
        """
        Calculate overall density score based on multiple factors.

        Scoring:
        - Word count: up to 0.4 (short=0.1, medium=0.3, long=0.4)
        - Specific examples: up to 0.4 (0.2 per example, max 2 examples)
        - Emotional markers: up to 0.2 (0.1 per marker, max 2 markers)
        """
        # Base score from word count
        if word_count_category == "short":
            word_score = 0.1
        elif word_count_category == "medium":
            word_score = 0.3
        else:
            word_score = 0.4

        # Bonus for specific examples (cap at 0.4)
        example_score = min(0.2 * specific_example_count, 0.4)

        # Bonus for emotional markers (cap at 0.2)
        emotional_score = min(0.1 * emotional_marker_count, 0.2)

        total_score = word_score + example_score + emotional_score

        # Normalize to 0-1 range
        return min(1.0, max(0.0, total_score))

    def decide_follow_ups(self, answer: str) -> FollowUpDecision:
        """
        Decide how many follow-up questions are needed.

        Args:
            answer: The user's answer text

        Returns:
            FollowUpDecision with count and suggested questions
        """
        analysis = self.analyze_density(answer)

        # Determine follow-up count based on density score
        if analysis.density_score < 0.3:
            follow_up_count = 2
            reason: Literal["low_density", "medium_density", "high_density"] = "low_density"
        elif analysis.density_score <= 0.6:
            follow_up_count = 1
            reason = "medium_density"
        else:
            follow_up_count = 0
            reason = "high_density"

        # Generate suggested questions
        suggested_questions = self.generate_follow_up_questions(answer, follow_up_count)

        return FollowUpDecision(
            follow_up_count=follow_up_count,
            density_score=analysis.density_score,
            reason=reason,
            suggested_questions=suggested_questions,
        )

    def generate_follow_up_questions(self, answer: str, count: int) -> List[str]:
        """
        Generate appropriate follow-up questions based on answer quality.

        Args:
            answer: The user's answer text
            count: Number of questions to generate

        Returns:
            List of suggested follow-up questions
        """
        if count <= 0:
            return []

        analysis = self.analyze_density(answer)

        questions = []

        # Select question type based on answer characteristics
        if analysis.word_count_category == "short":
            # Short answers need example-based questions
            question_pool = self.EXAMPLE_QUESTIONS
        else:
            # Medium answers need clarification questions
            question_pool = self.CLARIFICATION_QUESTIONS

        # Select questions (avoid duplicates)
        for i in range(min(count, len(question_pool))):
            questions.append(question_pool[i])

        return questions

    def plan_follow_ups(self, answer: str) -> FollowUpDecision:
        """
        Main entry point: analyze answer and plan follow-ups.

        Args:
            answer: The user's answer text

        Returns:
            FollowUpDecision with complete follow-up plan
        """
        return self.decide_follow_ups(answer)
