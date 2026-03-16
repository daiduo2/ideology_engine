#!/usr/bin/env python3
"""
Simple CLI demo of the assessment engine.

Usage:
    python demo.py
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from assessment_engine.storage.protocol_repo import ProtocolRepository
from assessment_engine.engine.assessment_engine import AssessmentEngine


def main():
    print("=" * 60)
    print("Natural Language Assessment Engine Demo")
    print("=" * 60)

    # Load protocol
    repo = ProtocolRepository(base_path=".")
    protocol = repo.load("generic_assessment_v1")

    if not protocol:
        print("Error: Could not load generic_assessment_v1 protocol")
        print("Make sure you're running from the assessment-engine directory")
        sys.exit(1)

    print(f"\nLoaded protocol: {protocol.name}")
    print(f"Dimensions: {[d.name for d in protocol.dimensions]}")
    print(f"Coverage targets: {protocol.coverage_targets}")

    # Initialize engine (no LLM for demo)
    print("\nRunning in demo mode (no LLM)")
    engine = AssessmentEngine(protocol=protocol, llm_client=None)

    # Start session
    session = engine.start_session()
    print(f"\nStarted session: {session.session_id}")

    # Run assessment loop
    max_rounds = 3  # Limit for demo

    for round_num in range(max_rounds):
        # Get next question
        result = engine.get_next_question()

        if result["status"] == "complete":
            print(f"\nAssessment complete: {result.get('termination_reasons', [])}")
            break

        question = result["question"]
        print(f"\n[Round {result['round_index'] + 1}]")
        print(f"AI: {question}")

        # Get user input
        try:
            answer = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nInterrupted by user")
            break

        if not answer:
            print("(Empty answer, skipping)")
            continue

        # Submit answer
        response = engine.submit_answer(answer)

        if response["status"] == "complete":
            print("\nAssessment complete!")
            break

    # Finalize
    print("\n" + "=" * 60)
    print("Finalizing assessment...")

    final = engine.finalize()
    report = final.get("report", {})

    if "human_readable" in report:
        hr = report["human_readable"]
        print(f"\nSummary: {hr.get('summary', 'N/A')}")

    # Show debug state
    print("\n" + "-" * 60)
    print("Debug: Final State")
    print("-" * 60)

    final_state = final.get("final_state", {})
    dimensions = final_state.get("dimensions", {})

    for dim_id, dim_state in dimensions.items():
        print(f"\n  {dim_id}:")
        print(f"    Score: {dim_state.get('score', 0):.2f}")
        print(f"    Confidence: {dim_state.get('confidence', 0):.2f}")
        print(f"    Evidence count: {dim_state.get('evidence_count', 0)}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
