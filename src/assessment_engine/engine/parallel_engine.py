"""Parallel Assessment Engine with multi-agent architecture.

This module provides a parallelized version of the assessment engine
where evidence extraction and question generation happen concurrently.
"""

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Optional

from assessment_engine.core.contradiction import Contradiction
from assessment_engine.core.evidence import DimensionMapping, Evidence
from assessment_engine.core.protocol import AssessmentProtocol
from assessment_engine.core.session import AssessmentSession
from assessment_engine.core.state import (
    AssessmentState,
    Coverage,
    DimensionState,
    TerminationStatus,
)
from assessment_engine.engine.probe_planner import ProbePlanner
from assessment_engine.engine.state_updater import StateUpdater
from assessment_engine.engine.termination_checker import TerminationChecker


class ParallelAssessmentEngine:
    """Parallel orchestrator for natural language assessment.

    Uses multi-agent architecture:
    - Evidence Agent: Extracts evidence from user answers (async)
    - Question Agent: Generates next questions (async)
    - State Manager: Updates state synchronously (fast)

    Parallel flows:
    1. User submits answer → Evidence Agent starts (background)
    2. Question Agent generates next question immediately (parallel)
    3. Return question to user immediately (~1.5s instead of 4-6s)
    4. Evidence Agent completes and updates state (background)
    """

    def __init__(
        self,
        protocol: AssessmentProtocol,
        llm_client: Optional[Any] = None,
        learning_rate: float = 0.1,
        max_workers: int = 3,
    ):
        self.protocol = protocol
        self.llm_client = llm_client
        self.session: Optional[AssessmentSession] = None
        self.state_updater = StateUpdater(learning_rate=learning_rate)
        self.termination_checker = TerminationChecker(protocol.stopping_rules)
        self.probe_planner = ProbePlanner(protocol)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Pending evidence processing
        self._pending_evidence_futures: list[Any] = []
        self._last_evidence_result: Optional[dict[str, Any]] = None

        # Initialize dimension states from protocol
        self.initial_dimensions = {
            dim.id: DimensionState(
                score=dim.scale.default,
                confidence=0.0,
                evidence_count=0,
                last_updated_at_round=0,
            )
            for dim in protocol.dimensions
        }

    def start_session(self, user_context: Optional[dict[str, Any]] = None) -> AssessmentSession:
        """Start a new assessment session."""
        session_id = str(uuid.uuid4())

        initial_state = AssessmentState(
            dimensions=self.initial_dimensions.copy(),
            coverage=Coverage(),
        )

        self.session = AssessmentSession(
            session_id=session_id,
            protocol_id=self.protocol.id,
            status="active",
            round_index=0,
            user_context=user_context or {},
            state=initial_state.model_dump(),
        )

        return self.session

    async def get_next_question_async(self) -> dict[str, Any]:
        """Get the next question asynchronously."""
        if not self.session:
            raise RuntimeError("No active session. Call start_session() first.")

        overall_start = time.time()

        # Wait for any pending evidence processing
        wait_start = time.time()
        await self._wait_for_pending_evidence()
        wait_elapsed = time.time() - wait_start
        if wait_elapsed > 0.01:
            print(f"    [DEBUG] 等待后台证据处理: {wait_elapsed:.2f}s")

        state = AssessmentState.model_validate(self.session.state)

        # Check termination
        termination = self.termination_checker.check(
            state,
            self.session.round_index,
            coverage_targets=self.protocol.coverage_targets,
        )

        if termination.eligible:
            return {
                "status": "complete",
                "message": "Assessment complete",
                "termination_reasons": termination.reasons,
            }

        # Plan next target
        target = self.probe_planner.plan_next(
            state,
            coverage_targets=self.protocol.coverage_targets,
        )

        # Generate question (or use default if no LLM)
        if self.llm_client:
            # Run question generation in thread pool
            q_start = time.time()
            loop = asyncio.get_event_loop()
            question_data = await loop.run_in_executor(
                self.executor,
                self._generate_question_sync,
                target,
            )
            q_elapsed = time.time() - q_start
            print(f"    [DEBUG] 问题生成耗时: {q_elapsed:.2f}s")
        else:
            # Default question without LLM
            question_data = {
                "question": self._get_default_question(target),
                "strategy_used": target.recommended_strategy,
            }

        overall_elapsed = time.time() - overall_start
        print(f"    [DEBUG] 获取问题总耗时: {overall_elapsed:.2f}s")

        return {
            "status": "active",
            "question": question_data.get("question", "Tell me more."),
            "target_type": target.type,
            "target": target.target,
            "round_index": self.session.round_index,
        }

    def _generate_question_sync(self, target) -> dict[str, Any]:
        """Synchronous wrapper for question generation."""
        return self.llm_client.generate_question(
            target=target.model_dump(),
            strategy=target.recommended_strategy or "ask_recent_example",
            conversation_history=self.session.conversation_log,
        )

    async def submit_answer_async(self, answer: str) -> dict[str, Any]:
        """Submit user answer and process it asynchronously.

        This method:
        1. Logs the answer
        2. Starts evidence extraction in background (non-blocking)
        3. Returns immediately with current status

        The evidence will be processed in background and available
        for the next round.
        """
        if not self.session:
            raise RuntimeError("No active session. Call start_session() first.")

        # Log the answer
        self.session.conversation_log.append(
            {
                "role": "user",
                "content": answer,
                "round_index": self.session.round_index,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Process with LLM if available
        if self.llm_client:
            # Start evidence extraction in background
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self.executor,
                self._process_evidence_sync,
                answer,
            )
            self._pending_evidence_futures.append(future)

            # Store reference to get result later
            self._last_evidence_result = None

            # Don't wait for evidence - return immediately
            result = {
                "status": "active",
                "message": "Answer received, processing in background",
                "round_index": self.session.round_index,
            }
        else:
            result = self._process_without_llm(answer)

        # Increment round
        self.session.round_index += 1
        self.session.updated_at = datetime.utcnow()

        return result

    def _process_evidence_sync(self, answer: str) -> dict[str, Any]:
        """Process evidence synchronously (runs in thread pool)."""
        start_time = time.time()
        print("    [DEBUG] 开始后台证据处理...")

        state = AssessmentState.model_validate(self.session.state)

        # 1. Parse response
        p_start = time.time()
        parsed = self.llm_client.parse_response(
            protocol_summary=self.protocol.model_dump_json(),
            state_summary=state.model_dump_json(),
            user_answer=answer,
        )
        print(f"    [DEBUG]   - 解析回答: {time.time() - p_start:.2f}s")

        # 2. Extract evidence
        e_start = time.time()
        evidence_data = self.llm_client.extract_evidence(
            protocol=self.protocol.model_dump(),
            observations=parsed.get("observations", []),
            current_state=state.model_dump(),
        )
        print(f"    [DEBUG]   - 提取证据: {time.time() - e_start:.2f}s")

        # Convert to Evidence objects
        evidence_list = []
        for i, e_data in enumerate(evidence_data.get("evidence", [])):
            evidence = Evidence(
                id=f"e_{self.session.session_id}_{i}",
                round_index=self.session.round_index,
                source_text=e_data.get("source_text", answer),
                evidence_type=e_data.get("evidence_type", "unknown"),
                normalized_claim=e_data.get("normalized_claim", ""),
                mapped_dimensions=[
                    DimensionMapping(**m) for m in e_data.get("mapped_dimensions", [])
                ],
                tags=e_data.get("tags", []),
            )
            evidence_list.append(evidence)

        # Convert contradictions
        contradiction_list = []
        for i, c_data in enumerate(evidence_data.get("contradiction_candidates", [])):
            contradiction = Contradiction(
                id=f"c_{self.session.session_id}_{i}",
                round_index=self.session.round_index,
                description=c_data.get("description", ""),
                related_dimension_ids=c_data.get("related_dimension_ids", []),
                evidence_ids=c_data.get("evidence_ids", []),
                severity=c_data.get("severity", "low"),
                needs_followup=c_data.get("needs_followup", True),
            )
            contradiction_list.append(contradiction)

        # 3. Update state
        u_start = time.time()
        new_state = self.state_updater.update_state(
            state,
            evidence_list,
            self.session.round_index,
            coverage_targets=self.protocol.coverage_targets,
            new_contradictions=contradiction_list,
        )
        print(f"    [DEBUG]   - 更新状态: {time.time() - u_start:.2f}s")

        # 4. Check termination
        t_start = time.time()
        termination = self.termination_checker.check(
            new_state,
            self.session.round_index,
            coverage_targets=self.protocol.coverage_targets,
            unresolved_contradictions=contradiction_list,
        )
        print(f"    [DEBUG]   - 检查终止: {time.time() - t_start:.2f}s")

        new_state.termination = termination

        # Update session state
        self.session.state = new_state.model_dump()

        elapsed = time.time() - start_time
        print(f"    [DEBUG] 证据处理完成，总耗时: {elapsed:.2f}s")

        return {
            "status": "active" if not termination.eligible else "complete",
            "parsed_observations": parsed.get("observations", []),
            "new_evidence": [e.model_dump() for e in evidence_list],
            "state": new_state.model_dump(),
            "termination": termination.model_dump(),
        }

    async def _wait_for_pending_evidence(self):
        """Wait for any pending evidence processing to complete."""
        if self._pending_evidence_futures:
            # Wait for all pending futures
            done, pending = await asyncio.wait(
                self._pending_evidence_futures,
                return_when=asyncio.ALL_COMPLETED,
            )
            self._pending_evidence_futures = list(pending)

            # Store the last completed result
            if done:
                self._last_evidence_result = done.pop().result()

    def _process_without_llm(self, answer: str) -> dict[str, Any]:
        """Process answer without LLM (placeholder for testing)."""
        state = AssessmentState.model_validate(self.session.state)

        return {
            "status": "active",
            "parsed_observations": [],
            "new_evidence": [],
            "state": state.model_dump(),
            "termination": TerminationStatus(eligible=False, reasons=[]).model_dump(),
        }

    def _get_default_question(self, target) -> str:
        """Get a default question when LLM is not available."""
        defaults = {
            "coverage_gap": "Can you tell me more about that?",
            "dimension_uncertainty": "I'd like to understand that better.",
            "contradiction": "Can you clarify something for me?",
            "ambiguity": "Could you give me a specific example?",
        }
        return defaults.get(target.type, "Tell me more.")

    async def finalize_async(self) -> dict[str, Any]:
        """Finalize assessment and generate report asynchronously."""
        if not self.session:
            raise RuntimeError("No active session.")

        # Wait for any pending evidence
        await self._wait_for_pending_evidence()

        self.session.status = "completed"
        state = AssessmentState.model_validate(self.session.state)

        if self.llm_client:
            loop = asyncio.get_event_loop()
            report = await loop.run_in_executor(
                self.executor,
                self._generate_report_sync,
                state,
            )
        else:
            report = {
                "human_readable": {
                    "summary": "Assessment completed without LLM.",
                    "key_characteristics": [],
                }
            }

        return {
            "session_id": self.session.session_id,
            "status": "completed",
            "final_state": state.model_dump(),
            "report": report,
        }

    def _generate_report_sync(self, state: AssessmentState) -> dict[str, Any]:
        """Synchronous wrapper for report generation."""
        return self.llm_client.generate_report(
            protocol=self.protocol.model_dump(),
            state=state.model_dump(),
            evidence=[],
        )

    def shutdown(self):
        """Shutdown the executor."""
        self.executor.shutdown(wait=True)
