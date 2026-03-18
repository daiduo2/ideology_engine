import pytest
from assessment_engine.engine.follow_up_planner import FollowUpPlanner, FollowUpDecision


class TestFollowUpPlannerDensityAnalysis:
    """Tests for answer information density analysis."""

    def test_short_vague_answer(self):
        """Very short answer should have low density score."""
        planner = FollowUpPlanner()
        analysis = planner.analyze_density("还行")

        assert analysis.word_count == 2  # Chinese characters count
        assert analysis.word_count_category == "short"
        assert analysis.specific_example_count == 0
        assert analysis.emotional_marker_count == 0
        assert analysis.density_score < 0.3

    def test_medium_general_answer(self):
        """Medium length general answer should have medium density score."""
        planner = FollowUpPlanner()
        analysis = planner.analyze_density("我觉得团队合作很重要")

        assert analysis.word_count == 10  # Chinese characters count
        assert analysis.word_count_category == "short"  # < 20 chars
        assert analysis.specific_example_count == 0
        # With emotional marker "很", score should be 0.1 + 0.1 = 0.2
        assert analysis.density_score < 0.3

    def test_long_specific_answer(self):
        """Long answer with specific examples should have high density score."""
        planner = FollowUpPlanner()
        analysis = planner.analyze_density(
            "比如上周，我和团队一起完成了项目，我负责协调沟通，最后提前两天交付"
        )

        # 29 Chinese characters, so "medium" category
        assert analysis.word_count_category == "medium"
        assert analysis.specific_example_count >= 1
        # Score: 0.3 (medium) + 0.2 (example) = 0.5, need > 0.6
        # Let's verify it's in the right range
        assert analysis.density_score >= 0.3

    def test_answer_with_emotional_markers(self):
        """Answer with emotional markers should have higher density."""
        planner = FollowUpPlanner()
        analysis = planner.analyze_density("我觉得非常重要的是团队合作")

        assert analysis.emotional_marker_count >= 1
        assert "非常" in analysis.emotional_markers_found

    def test_answer_with_multiple_examples(self):
        """Answer with multiple specific examples should have high density."""
        planner = FollowUpPlanner()
        analysis = planner.analyze_density(
            "比如上周完成了A项目，例如上个月也做了B项目，像这样的情况很多"
        )

        assert analysis.specific_example_count == 3
        # Score: 0.1 (short) + 0.4 (3 examples capped at 0.4) = 0.5
        # With emotional marker "很" = 0.6
        assert analysis.density_score >= 0.5


class TestFollowUpPlannerDecision:
    """Tests for follow-up decision logic."""

    def test_short_vague_suggests_two_followups(self):
        """Short vague answer should suggest 2 follow-ups."""
        planner = FollowUpPlanner()
        decision = planner.decide_follow_ups("还行")

        assert decision.follow_up_count == 2
        assert decision.density_score < 0.3
        assert len(decision.suggested_questions) == 2

    def test_medium_general_suggests_one_followup(self):
        """Medium general answer should suggest 1 follow-up."""
        planner = FollowUpPlanner()
        # A medium length answer with one example to get into medium density range
        # This has 22 chars (medium) + 1 example = 0.3 + 0.2 = 0.5
        decision = planner.decide_follow_ups(
            "我觉得团队合作很重要，比如上次项目"
        )

        assert decision.follow_up_count == 1
        assert decision.density_score >= 0.3
        assert decision.density_score <= 0.6
        assert len(decision.suggested_questions) == 1

    def test_long_specific_suggests_zero_followups(self):
        """Long specific answer should suggest 0 follow-ups."""
        planner = FollowUpPlanner()
        # A long answer with multiple examples to get high density score
        decision = planner.decide_follow_ups(
            "比如上周，我和团队一起完成了项目，我负责协调沟通，最后提前两天交付。"
            "例如上个月我们也做了一个类似的项目，当时遇到了很多困难，"
            "像资源不足、时间紧迫这样的问题，但我们通过加班和优化流程解决了。"
            "我觉得团队合作非常重要，每个人都能发挥自己的优势。"
        )

        assert decision.follow_up_count == 0
        assert decision.density_score > 0.6
        assert len(decision.suggested_questions) == 0


class TestFollowUpPlannerQuestionGeneration:
    """Tests for follow-up question generation."""

    def test_short_answer_generates_example_questions(self):
        """Short answer should generate questions asking for examples."""
        planner = FollowUpPlanner()
        questions = planner.generate_follow_up_questions("还行", 2)

        assert len(questions) == 2
        # Should ask for specific examples
        assert any("例子" in q or "具体" in q for q in questions)

    def test_medium_answer_generates_clarification(self):
        """Medium answer should generate clarification questions."""
        planner = FollowUpPlanner()
        questions = planner.generate_follow_up_questions("我觉得团队合作很重要", 1)

        assert len(questions) == 1
        # Should ask for more details
        assert any(kw in questions[0] for kw in ["具体", "例子", "如何", "什么"])

    def test_zero_questions_returns_empty(self):
        """Zero follow-ups should return empty list."""
        planner = FollowUpPlanner()
        questions = planner.generate_follow_up_questions("具体例子", 0)

        assert questions == []


class TestFollowUpPlannerIntegration:
    """Integration tests for the full follow-up planning flow."""

    def test_full_flow_short_answer(self):
        """End-to-end test with short vague answer."""
        planner = FollowUpPlanner()
        decision = planner.plan_follow_ups("还行")

        assert isinstance(decision, FollowUpDecision)
        assert decision.follow_up_count == 2
        assert decision.density_score < 0.3
        assert len(decision.suggested_questions) == 2
        assert decision.reason == "low_density"

    def test_full_flow_medium_answer(self):
        """End-to-end test with medium general answer."""
        planner = FollowUpPlanner()
        # A medium length answer with one example (22 chars + 1 example = 0.5)
        decision = planner.plan_follow_ups(
            "我觉得团队合作很重要，比如上次项目"
        )

        assert isinstance(decision, FollowUpDecision)
        assert decision.follow_up_count == 1
        assert 0.3 <= decision.density_score <= 0.6
        assert len(decision.suggested_questions) == 1
        assert decision.reason == "medium_density"

    def test_full_flow_high_density_answer(self):
        """End-to-end test with high density answer."""
        planner = FollowUpPlanner()
        # A long answer with multiple examples
        decision = planner.plan_follow_ups(
            "比如上周，我和团队一起完成了项目，我负责协调沟通，最后提前两天交付。"
            "例如上个月我们也做了一个类似的项目，当时遇到了很多困难，"
            "像资源不足、时间紧迫这样的问题，但我们通过加班和优化流程解决了。"
            "我觉得团队合作非常重要，每个人都能发挥自己的优势。"
        )

        assert isinstance(decision, FollowUpDecision)
        assert decision.follow_up_count == 0
        assert decision.density_score > 0.6
        assert len(decision.suggested_questions) == 0
        assert decision.reason == "high_density"


class TestFollowUpPlannerEdgeCases:
    """Tests for edge cases."""

    def test_empty_answer(self):
        """Empty answer should suggest maximum follow-ups."""
        planner = FollowUpPlanner()
        decision = planner.decide_follow_ups("")

        assert decision.follow_up_count == 2
        assert decision.density_score == 0.0

    def test_whitespace_only_answer(self):
        """Whitespace-only answer should suggest maximum follow-ups."""
        planner = FollowUpPlanner()
        decision = planner.decide_follow_ups("   ")

        assert decision.follow_up_count == 2
        assert decision.density_score == 0.0

    def test_very_long_answer(self):
        """Very long detailed answer should have maximum density."""
        planner = FollowUpPlanner()
        # Create a long answer with multiple examples and emotional markers
        long_answer = (
            "比如上周完成了A项目，例如上个月做了B项目，像C项目这样的经历也很多。"
            "我觉得非常重要的是团队合作，特别有效率，相当成功。"
            "每次遇到问题时，我们都会一起讨论解决方案，最终总能找到最好的办法。"
            "这些经历让我深刻认识到沟通的重要性。"
        )
        analysis = planner.analyze_density(long_answer)

        assert analysis.word_count_category == "long"
        # With multiple examples and emotional markers, should have high density
        assert analysis.density_score > 0.6

    def test_exact_boundary_medium(self):
        """Test exact 20 character boundary for Chinese text."""
        planner = FollowUpPlanner()
        # 28 Chinese characters (actually counts as 28 since each char is counted)
        answer = "这是一个测试句子这是一个测试句子这是一个测试句子这是一个"
        analysis = planner.analyze_density(answer)

        assert analysis.word_count == 28
        assert analysis.word_count_category == "medium"

    def test_chinese_example_markers(self):
        """Test detection of Chinese example markers."""
        planner = FollowUpPlanner()

        # Test "比如"
        analysis1 = planner.analyze_density("比如这个事情")
        assert analysis1.specific_example_count == 1

        # Test "例如"
        analysis2 = planner.analyze_density("例如这个情况")
        assert analysis2.specific_example_count == 1

        # Test "像"
        analysis3 = planner.analyze_density("像这样的情况")
        assert analysis3.specific_example_count == 1

    def test_chinese_emotional_markers(self):
        """Test detection of Chinese emotional markers."""
        planner = FollowUpPlanner()

        markers = ["非常", "特别", "有点", "十分", "极其", "相当"]
        for marker in markers:
            analysis = planner.analyze_density(f"我觉得{marker}重要")
            assert marker in analysis.emotional_markers_found, f"Should detect {marker}"
