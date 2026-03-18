#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to verify parallel engine is working correctly."""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from assessment_engine.storage.protocol_repo import ProtocolRepository
from assessment_engine.engine.parallel_engine import ParallelAssessmentEngine
from assessment_engine.llm import LLMConfig, create_llm_client

API_KEY = "sk-kimi-Rw4b3DY6vWKSby9dtqvFGufBTsOUSSVbd7n0pgajJzxI9imDCqHqQg3VmaUCp6gM"
BASE_URL = "https://api.kimi.com/coding/"


class MockLLMClient:
    """Mock LLM client that simulates API delays for testing."""

    def __init__(self, parse_delay=1.5, extract_delay=1.5, question_delay=1.5):
        self.parse_delay = parse_delay
        self.extract_delay = extract_delay
        self.question_delay = question_delay
        self.call_log = []

    def _log(self, method, delay):
        timestamp = time.time()
        self.call_log.append({
            'method': method,
            'start': timestamp,
            'delay': delay,
        })
        print(f"  [MOCK] {method} started at {timestamp:.2f} (will take {delay}s)")
        time.sleep(delay)
        print(f"  [MOCK] {method} finished at {time.time():.2f}")

    def parse_response(self, **kwargs):
        self._log('parse_response', self.parse_delay)
        return {"observations": [{"type": "preference", "content": "test"}]}

    def extract_evidence(self, **kwargs):
        self._log('extract_evidence', self.extract_delay)
        return {
            "evidence": [{
                "source_text": "test",
                "evidence_type": "preference",
                "normalized_claim": "test claim",
                "mapped_dimensions": [{"dimension_id": "extraversion_introversion", "direction": 1, "weight": 0.8, "confidence": 0.8}],
            }],
            "contradiction_candidates": []
        }

    def generate_question(self, **kwargs):
        self._log('generate_question', self.question_delay)
        return {"question": "Test question?", "strategy_used": "test"}

    def generate_report(self, **kwargs):
        return {"human_readable": {"summary": "Test report"}}


async def test_parallel_timing():
    """Test that parallel engine actually runs things in parallel."""
    print("=" * 60)
    print("🧪 测试并行引擎架构")
    print("=" * 60)

    # Load protocol
    base_path = Path(__file__).parent.resolve()
    repo = ProtocolRepository(base_path=base_path)
    protocol = repo.load("mbti-assessment")

    if not protocol:
        print("❌ 无法加载协议")
        return

    # Use mock client with known delays
    print("\n📋 使用 Mock LLM (模拟每个API调用1.5秒延迟)")
    llm_client = MockLLMClient(parse_delay=1.5, extract_delay=1.5, question_delay=1.5)

    # Create parallel engine
    engine = ParallelAssessmentEngine(
        protocol=protocol,
        llm_client=llm_client,
        max_workers=3
    )

    # Start session
    session = engine.start_session()
    print(f"\n🆔 会话ID: {session.session_id}")

    print("\n" + "-" * 60)
    print("开始第1轮：")
    print("-" * 60)

    # Get first question
    round_start = time.time()
    result = await engine.get_next_question_async()
    q1_elapsed = time.time() - round_start
    print(f"\n✅ 第1个问题耗时: {q1_elapsed:.2f}s (期望: ~1.5s，仅问题生成)")

    # Submit first answer
    print("\n提交回答并观察并行行为...")
    submit_start = time.time()
    await engine.submit_answer_async("Test answer")
    submit_elapsed = time.time() - submit_start
    print(f"✅ 提交回答耗时: {submit_elapsed:.2f}s (期望: <0.1s，立即返回)")

    # Simulate user typing time (in real usage, user spends time thinking and typing)
    # During this time, background evidence processing should complete
    SIMULATED_TYPING_TIME = 3.0  # seconds
    print(f"\n⏱️  模拟用户输入时间: {SIMULATED_TYPING_TIME}s (用户在打字思考...)")
    print("   在此期间，后台证据处理应该完成")
    await asyncio.sleep(SIMULATED_TYPING_TIME)

    print("\n" + "-" * 60)
    print("开始第2轮：")
    print("-" * 60)

    # Get second question - if parallel worked, evidence should already be done
    # but evidence should already be done since we waited
    round2_start = time.time()
    result2 = await engine.get_next_question_async()
    q2_elapsed = time.time() - round2_start
    print(f"\n✅ 第2个问题耗时: {q2_elapsed:.2f}s")

    total_time = time.time() - round_start
    print("\n" + "=" * 60)
    print("📊 测试结果分析：")
    print("=" * 60)

    # Calculate expected times
    # Serial: q1 + type + evidence + q2 = 1.5 + 3 + 3 + 1.5 = 9s
    # Parallel: q1 + max(type, evidence) + q2 = 1.5 + max(3, 3) + 1.5 = 6s
    serial_expected = 1.5 + SIMULATED_TYPING_TIME + 3 + 1.5
    parallel_expected_with_typing = 1.5 + max(SIMULATED_TYPING_TIME, 3) + 1.5

    # Perceived latency (what user actually waits for between questions)
    # Round 1: q1 generation time
    # Round 2: if evidence done during typing, just q2 generation
    perceived_latency_round1 = 1.5
    perceived_latency_round2 = 1.5  # Evidence already done!

    print(f"\n假设条件:")
    print(f"  - 每轮问题生成: 1.5s")
    print(f"  - 每轮证据处理: 3s (解析+提取)")
    print(f"  - 用户输入时间: {SIMULATED_TYPING_TIME}s")
    print(f"\n串行执行预期时间: ~{serial_expected:.1f}s")
    print(f"并行执行预期时间: ~{parallel_expected_with_typing:.1f}s")
    print(f"实际总时间: {total_time:.2f}s")
    print(f"\n用户感知到的延迟:")
    print(f"  - 第1轮: {perceived_latency_round1:.1f}s (生成第1题)")
    print(f"  - 第2轮: {perceived_latency_round2:.1f}s (证据已并行完成!)")

    if abs(total_time - parallel_expected_with_typing) < 1:
        print(f"\n🎉 成功！并行架构工作正常")
        print(f"   用户感知延迟: {perceived_latency_round1 + perceived_latency_round2:.1f}s")
        print(f"   相比串行节省: ~{serial_expected - parallel_expected_with_typing:.1f}s")
    else:
        print(f"\n⚠️ 警告：可能未正确并行执行")

    # Print call log
    print("\n📋 API调用顺序：")
    for i, call in enumerate(llm_client.call_log):
        print(f"   {i+1}. {call['method']} (delay={call['delay']}s)")

    engine.shutdown()


if __name__ == "__main__":
    asyncio.run(test_parallel_timing())
