#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MBTI Personality Assessment Demo - OPTIMIZED VERSION.

Optimizations:
- Scheme 2: Merged parse+extract (single LLM call instead of 2)
- Scheme 3: Pregenerate questions (0 wait time for next question)
- Scheme 5: Cache responses (avoid duplicate LLM calls)

Usage:
    python demo_mbti_optimized.py
"""
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from assessment_engine.storage.protocol_repo import ProtocolRepository
from assessment_engine.engine.optimized_parallel_engine import OptimizedParallelAssessmentEngine
from assessment_engine.llm import LLMConfig, create_llm_client

# Kimi API 配置
API_KEY = "sk-kimi-Rw4b3DY6vWKSby9dtqvFGufBTsOUSSVbd7n0pgajJzxI9imDCqHqQg3VmaUCp6gM"
BASE_URL = "https://api.kimi.com/coding/"


def get_mbti_type(scores: dict) -> str:
    """Convert dimension scores to MBTI type code."""
    ei = "E" if scores.get("extraversion_introversion", 0) > 0 else "I"
    sn = "S" if scores.get("sensing_intuition", 0) > 0 else "N"
    tf = "T" if scores.get("thinking_feeling", 0) > 0 else "F"
    jp = "J" if scores.get("judging_perceiving", 0) > 0 else "P"
    return f"{ei}{sn}{tf}{jp}"


def print_dimension_bar(name: str, score: float, width: int = 30):
    """Print a visual bar for dimension score (-1 to +1)."""
    center = width // 2
    position = int((score + 1) / 2 * width)
    position = max(0, min(width, position))

    bar = ["░"] * width
    bar[center] = "│"

    if position < center:
        for i in range(position, center):
            bar[i] = "█"
    elif position > center:
        for i in range(center + 1, position + 1):
            bar[i] = "█"
    else:
        bar[position] = "█"

    print(f"  {name:20s} {''.join(bar)} {score:+.2f}")


async def get_input_claude_style():
    """Claude Code级别的输入体验（异步版本）。"""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.styles import Style

        session = PromptSession(multiline=True)
        kb = KeyBindings()

        @kb.add('c-c')
        @kb.add('c-d')
        def _(event):
            event.app.exit(result=None)

        @kb.add('enter')
        def _(event):
            buffer = event.current_buffer
            if buffer.text.strip():
                buffer.validate_and_handle()

        @kb.add('escape', 'enter')
        def _(event):
            event.current_buffer.insert_text('\n')

        style = Style.from_dict({'prompt': '#00aa00 bold'})

        print("💭 你的回答 (按 Enter 提交，Esc+Enter 换行，Ctrl+C 退出):")

        result = await session.prompt_async(
            "   » ",
            key_bindings=kb,
            style=style,
            multiline=True,
            prompt_continuation="   · ",
        )

        return result.strip() if result else None

    except ImportError:
        print("\n💭 你的回答: ", end='', flush=True)
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, sys.stdin.readline)
        except (EOFError, KeyboardInterrupt):
            return None


async def main():
    print("=" * 70)
    print("🧠 MBTI 人格评估 - 优化版 (方案2+3+5)")
    print("=" * 70)
    print("\n⚡ 优化特性:")
    print("   • 合并解析+提取: 单次LLM调用 (省50%时间)")
    print("   • 预生成问题: 问题提前准备 (省~1.5s)")
    print("   • 智能缓存: 相似回答直接复用")

    # Load MBTI protocol
    base_path = Path(__file__).parent.resolve()
    repo = ProtocolRepository(base_path=base_path)
    protocol = repo.load("mbti-assessment")

    if not protocol:
        print("❌ 错误：无法加载 mbti-assessment 协议")
        sys.exit(1)

    print(f"\n📋 评估协议: {protocol.name}")
    print(f"\n维度说明:")
    print("  • E/I (外向/内向): 能量来源偏好")
    print("  • S/N (感觉/直觉): 信息收集偏好")
    print("  • T/F (思考/情感): 决策方式偏好")
    print("  • J/P (判断/知觉): 生活方式偏好")

    # Create Kimi LLM client
    print(f"\n🔌 连接 Kimi API...")
    config = LLMConfig(
        provider="anthropic",
        api_key=API_KEY,
        base_url=BASE_URL,
        model="claude-opus-4-6"
    )

    try:
        llm_client = create_llm_client(config)
        print("✅ 已连接到 Kimi API")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        sys.exit(1)

    # Initialize OPTIMIZED parallel engine
    engine = OptimizedParallelAssessmentEngine(
        protocol=protocol,
        llm_client=llm_client,
        max_workers=3
    )

    # Start session
    session = engine.start_session()
    print(f"\n🆔 会话ID: {session.session_id}")
    print("\n" + "-" * 70)
    print("💬 评估开始！体验优化后的响应速度。")
    print("   输入 'quit' 可随时退出。")
    print("-" * 70)

    # Run assessment loop
    max_rounds = 8
    round_times = []

    try:
        for round_num in range(max_rounds):
            # Get next question
            q_start = time.time()
            result = await engine.get_next_question_async()
            q_elapsed = time.time() - q_start
            round_times.append(q_elapsed)

            if result["status"] == "complete":
                print(f"\n✅ 评估完成！")
                break

            question = result["question"]
            print(f"\n[第 {result['round_index'] + 1} 轮/{max_rounds}] ⏱️ 获取问题耗时: {q_elapsed:.2f}s")
            print(f"🤖 {question}")

            # Get user input
            answer = await get_input_claude_style()

            if answer is None:
                print("\n\n👋 用户中断")
                break

            if answer.lower() == 'quit':
                print("\n👋 退出评估...")
                break

            if not answer:
                print("(空回答，跳过)")
                continue

            # Submit answer (returns immediately, evidence processed in background)
            print("⏳ 提交回答并启动后台分析...")
            a_start = time.time()
            await engine.submit_answer_async(answer)
            a_elapsed = time.time() - a_start
            print(f"✅ 回答已提交 (处理耗时: {a_elapsed:.2f}s, 证据提取在后台运行)")

        # Finalize
        print("\n" + "=" * 70)
        print("📊 生成评估报告...")

        final = await engine.finalize_async()
        report = final.get("report", {})
        final_state = final.get("final_state", {})
        dimensions = final_state.get("dimensions", {})

        # Extract scores
        scores = {}
        for dim_id, dim_state in dimensions.items():
            scores[dim_id] = dim_state.get("score", 0)

        # Calculate MBTI type
        mbti_type = get_mbti_type(scores)

        print(f"\n🎯 你的 MBTI 类型: {mbti_type}")
        print()

        # Print dimension bars
        dimension_names = {
            "extraversion_introversion": "E (外向) ←→ I (内向)",
            "sensing_intuition": "S (感觉) ←→ N (直觉)",
            "thinking_feeling": "T (思考) ←→ F (情感)",
            "judging_perceiving": "J (判断) ←→ P (知觉)",
        }

        print("维度得分 (-1 到 +1):")
        print()
        for dim_id, name in dimension_names.items():
            score = scores.get(dim_id, 0)
            print_dimension_bar(name, score)

        # Type description
        type_descriptions = {
            "ISTJ": "检查员：务实、负责、注重细节",
            "ISFJ": "保护者：温和、体贴、忠诚可靠",
            "INFJ": "提倡者：洞察力强、有理想、富有同情心",
            "INTJ": "建筑师：独立、战略性思维、追求卓越",
            "ISTP": "鉴赏家：灵活、理性、善于解决问题",
            "ISFP": "探险家：艺术气质、敏感、活在当下",
            "INFP": "调停者：理想主义、善解人意、追求意义",
            "INTP": "逻辑学家：好奇、分析能力强、客观理性",
            "ESTP": "企业家：活力充沛、务实、善于应变",
            "ESFP": "表演者：热情、社交能力强、享受当下",
            "ENFP": "竞选者：充满热情、创意丰富、善于激励他人",
            "ENTP": "辩论家：机智、创新、喜欢智力挑战",
            "ESTJ": "总经理：组织能力强、务实、重视传统",
            "ESFJ": "执政官：热心、善于合作、重视和谐",
            "ENFJ": "主人公：魅力四射、有领导力、关心他人成长",
            "ENTJ": "指挥官：果断、战略眼光、天生的领导者",
        }

        description = type_descriptions.get(mbti_type, "独特的人格类型组合")
        print(f"\n📖 类型描述: {description}")

        # Confidence info
        print("\n📈 置信度:")
        for dim_id, name in dimension_names.items():
            dim_state = dimensions.get(dim_id, {})
            confidence = dim_state.get("confidence", 0)
            evidence = dim_state.get("evidence_count", 0)
            print(f"  {name.split('(')[0].strip():10s} 置信度: {confidence:.2f}  (证据: {evidence} 条)")

        # Report summary if available
        if "human_readable" in report:
            hr = report["human_readable"]
            print(f"\n📝 AI 分析摘要:")
            print(f"   {hr.get('summary', '暂无')}")

        # Performance summary
        if round_times:
            avg_time = sum(round_times) / len(round_times)
            print(f"\n⏱️ 性能统计:")
            print(f"   平均每轮耗时: {avg_time:.2f}s")
            print(f"   总评估轮数: {len(round_times)}")

        print("\n" + "=" * 70)
        print("🎉 MBTI 评估完成！")
        print("=" * 70)
        print(f"\n💡 提示: MBTI 类型反映的是偏好倾向，而非能力高低。")
        print(f"   每种类型都有其独特的优势和贡献。")

    finally:
        # Shutdown executor
        engine.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
