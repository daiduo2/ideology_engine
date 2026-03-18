#!/usr/bin/env python3
"""
Demo using Kimi API with custom base URL.

Usage:
    python demo_kimi.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from assessment_engine.storage.protocol_repo import ProtocolRepository
from assessment_engine.engine.assessment_engine import AssessmentEngine
from assessment_engine.llm import LLMConfig, create_llm_client

# Kimi API 配置
API_KEY = "sk-kimi-Rw4b3DY6vWKSby9dtqvFGufBTsOUSSVbd7n0pgajJzxI9imDCqHqQg3VmaUCp6gM"
BASE_URL = "https://api.kimi.com/coding/"


def main():
    print("=" * 60)
    print("Natural Language Assessment Engine - Kimi API Demo")
    print("=" * 60)

    # Load protocol
    base_path = Path(__file__).parent.resolve()
    repo = ProtocolRepository(base_path=base_path)
    protocol = repo.load("generic-assessment-v1")

    if not protocol:
        print("Error: Could not load protocol")
        sys.exit(1)

    print(f"\nLoaded protocol: {protocol.name}")
    print(f"Dimensions: {[d.name for d in protocol.dimensions]}")

    # Create Kimi LLM client
    print(f"\nConnecting to Kimi API...")
    config = LLMConfig(
        provider="anthropic",
        api_key=API_KEY,
        base_url=BASE_URL,
        model="claude-opus-4-6"
    )

    try:
        llm_client = create_llm_client(config)
        print("✓ Connected to Kimi API")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)

    # Initialize engine with LLM
    engine = AssessmentEngine(protocol=protocol, llm_client=llm_client)

    # Start session
    session = engine.start_session()
    print(f"\nStarted session: {session.session_id}")
    print("\n" + "-" * 60)
    print("Assessment started! Answer the questions naturally.")
    print("Type 'quit' to exit early.")
    print("-" * 60)

    # Run assessment loop
    max_rounds = 5

    for round_num in range(max_rounds):
        # Get next question
        result = engine.get_next_question()

        if result["status"] == "complete":
            print(f"\n✓ Assessment complete: {result.get('termination_reasons', [])}")
            break

        question = result["question"]
        print(f"\n[Round {result['round_index'] + 1}/{max_rounds}]")
        print(f"🤖 {question}")

        # Get user input
        try:
            answer = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nInterrupted by user")
            break

        if answer.lower() == 'quit':
            print("\nExiting...")
            break

        if not answer:
            print("(Empty answer, skipping)")
            continue

        # Submit answer
        print("Processing...")
        response = engine.submit_answer(answer)

        if response["status"] == "complete":
            print("\n✓ Assessment complete!")
            break

    # Finalize
    print("\n" + "=" * 60)
    print("Generating final report...")

    final = engine.finalize()
    report = final.get("report", {})

    if "human_readable" in report:
        hr = report["human_readable"]
        print(f"\n📊 Summary: {hr.get('summary', 'N/A')}")

    # Show results
    print("\n" + "-" * 60)
    print("Assessment Results")
    print("-" * 60)

    final_state = final.get("final_state", {})
    dimensions = final_state.get("dimensions", {})

    for dim_id, dim_state in dimensions.items():
        score = dim_state.get('score', 0)
        confidence = dim_state.get('confidence', 0)
        evidence = dim_state.get('evidence_count', 0)

        # Visual bar for score
        bar_length = 20
        filled = int(score * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)

        print(f"\n  {dim_id}:")
        print(f"    Score:       |{bar}| {score:.2f}")
        print(f"    Confidence:  {confidence:.2f}")
        print(f"    Evidence:    {evidence} items")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
