"""Optimized Parallel Assessment Engine with caching and batch processing.

Implements:
- Scheme 2: Merge parse_response + extract_evidence into single LLM call
- Scheme 3: Pregenerate candidate questions asynchronously
- Scheme 5: Cache responses for similar inputs
"""
import asyncio
import hashlib
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from assessment_engine.core.protocol import AssessmentProtocol
from assessment_engine.core.session import AssessmentSession
from assessment_engine.core.state import AssessmentState, DimensionState, Coverage, TerminationStatus
from assessment_engine.core.evidence import Evidence, DimensionMapping
from assessment_engine.core.contradiction import Contradiction
from assessment_engine.engine.state_updater import StateUpdater
from assessment_engine.engine.termination_checker import TerminationChecker
from assessment_engine.engine.probe_planner import ProbePlanner


@dataclass
class CacheEntry:
    """Cache entry with timestamp and TTL."""
    result: Dict[str, Any]
    timestamp: float
    ttl: float = 300  # 5 minutes default

    def is_valid(self) -> bool:
        return time.time() - self.timestamp < self.ttl


@dataclass
class PregeneratedQuestions:
    """Pregenerated candidate questions for upcoming rounds."""
    questions: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    based_on_round: int = 0

    def is_fresh(self, max_age: float = 60) -> bool:
        return time.time() - self.generated_at < max_age

    def get_next(self) -> Optional[Dict[str, Any]]:
        if self.questions:
            return self.questions.pop(0)
        return None


class OptimizedLLMClient:
    """Optimized LLM client with caching and batch processing."""

    def __init__(self, base_client):
        self.client = base_client
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def _get_cache_key(self, method: str, *args) -> str:
        """Generate cache key from method and arguments."""
        # Simple hash of method name and args
        content = json.dumps({"method": method, "args": args}, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content.encode()).hexdigest()

    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache if valid."""
        if key in self.cache:
            entry = self.cache[key]
            if entry.is_valid():
                self.cache_hits += 1
                print(f"    [CACHE] Cache hit! ({self.cache_hits} hits, {self.cache_misses} misses)")
                return entry.result
            else:
                del self.cache[key]
        return None

    def _set_cache(self, key: str, result: Dict[str, Any]):
        """Store result in cache."""
        self.cache[key] = CacheEntry(result=result, timestamp=time.time())
        self.cache_misses += 1

    def clear_cache(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0

    def parse_and_extract(self, protocol: Dict[str, Any], state: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """
        Scheme 2: Merge parse_response + extract_evidence into single LLM call.

        Instead of:
        - parse_response: LLM call 1
        - extract_evidence: LLM call 2

        We do:
        - parse_and_extract: Single LLM call that returns both observations AND evidence
        """
        # Check cache first (Scheme 5)
        cache_key = self._get_cache_key("parse_and_extract", protocol.get("id"), user_answer)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Build combined prompt
        from assessment_engine.llm.prompts.parse_response import SYSTEM_PROMPT as PARSE_PROMPT
        from assessment_engine.llm.prompts.extract_evidence import SYSTEM_PROMPT as EXTRACT_PROMPT

        combined_system_prompt = f"""{PARSE_PROMPT}

---

Now, after parsing, you must also extract evidence. COMBINE both steps:

1. First, parse the user's answer into structured observations (as per above)
2. Then, immediately extract evidence from those observations and map to dimensions

{EXTRACT_PROMPT}

OUTPUT FORMAT - Return a SINGLE JSON object with BOTH results:
{{
    "observations": [
        {{"type": "preference|fact|behavior", "content": "...", "confidence": 0.8}}
    ],
    "evidence": [
        {{
            "source_text": "...",
            "evidence_type": "...",
            "normalized_claim": "...",
            "mapped_dimensions": [
                {{"dimension_id": "...", "direction": 1, "weight": 0.8, "confidence": 0.8}}
            ],
            "tags": []
        }}
    ],
    "contradiction_candidates": []
}}"""

        user_message = f"""
Protocol: {json.dumps(protocol, ensure_ascii=False)}

Current State: {json.dumps(state, ensure_ascii=False)}

User Answer: {user_answer}

IMPORTANT: Return a SINGLE JSON combining both parse results AND extracted evidence.
"""

        start = time.time()
        result = self.client._call_llm(combined_system_prompt, user_message)
        elapsed = time.time() - start
        print(f"    [OPTIMIZED] 合并解析+提取耗时: {elapsed:.2f}s (vs 原本 ~{elapsed*2:.2f}s)")

        # Cache the result (Scheme 5)
        self._set_cache(cache_key, result)

        return result

    def generate_question(self, target: Dict[str, Any], strategy: str,
                          conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate question with caching."""
        # Simple cache based on target
        cache_key = self._get_cache_key("generate_question", target.get("target"), strategy)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        result = self.client.generate_question(target, strategy, conversation_history)
        self._set_cache(cache_key, result)
        return result

    def generate_questions_batch(self, targets: List[Dict[str, Any]],
                                 conversation_history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Scheme 3: Generate multiple questions in batch for pregeneration.
        """
        results = []
        for target in targets:
            try:
                result = self.generate_question(target, target.get("recommended_strategy", "ask_recent_example"),
                                               conversation_history)
                results.append(result)
            except Exception as e:
                print(f"    [PREGEN] Failed to pregenerate question for {target.get('target')}: {e}")
        return results

    def generate_report(self, protocol: Dict[str, Any], state: Dict[str, Any],
                        evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate final report."""
        return self.client.generate_report(protocol, state, evidence)


class OptimizedParallelAssessmentEngine:
    """Optimized parallel engine with caching and pregeneration."""

    def __init__(
        self,
        protocol: AssessmentProtocol,
        llm_client: Optional[Any] = None,
        learning_rate: float = 0.1,
        max_workers: int = 3,
    ):
        self.protocol = protocol
        self.original_llm_client = llm_client

        # Wrap with optimized client
        if llm_client:
            self.llm_client = OptimizedLLMClient(llm_client)
        else:
            self.llm_client = None

        self.session: Optional[AssessmentSession] = None
        self.state_updater = StateUpdater(learning_rate=learning_rate)
        self.termination_checker = TerminationChecker(protocol.stopping_rules)
        self.probe_planner = ProbePlanner(protocol)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Pending evidence processing
        self._pending_evidence_futures: List[Any] = []
        self._last_evidence_result: Optional[Dict[str, Any]] = None

        # Scheme 3: Pregenerated questions
        self._pregenerated: Optional[PregeneratedQuestions] = None
        self._pregen_future: Optional[Any] = None

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

    def start_session(self, user_context: Optional[Dict[str, Any]] = None) -> AssessmentSession:
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

        # Pre-generate first question immediately
        if self.llm_client:
            self._start_pregeneration()

        return self.session

    def _start_pregeneration(self):
        """Start pregenerating next questions in background."""
        if not self.llm_client or not self.session:
            return

        state = AssessmentState.model_validate(self.session.state)

        # Plan next 2-3 targets
        targets = []
        for _ in range(3):
            target = self.probe_planner.plan_next(
                state,
                coverage_targets=self.protocol.coverage_targets,
            )
            targets.append(target.model_dump())

        # Start async pregeneration
        loop = asyncio.get_event_loop()
        self._pregen_future = loop.run_in_executor(
            self.executor,
            self._pregenerate_questions_sync,
            targets,
        )

    def _pregenerate_questions_sync(self, targets: List[Dict[str, Any]]) -> PregeneratedQuestions:
        """Synchronous pregeneration of questions."""
        print(f"    [PREGEN] 开始预生成 {len(targets)} 个问题...")
        start = time.time()

        questions = self.llm_client.generate_questions_batch(
            targets,
            self.session.conversation_log if self.session else []
        )

        elapsed = time.time() - start
        print(f"    [PREGEN] 预生成完成: {len(questions)} 个问题，耗时 {elapsed:.2f}s")

        return PregeneratedQuestions(
            questions=questions,
            generated_at=time.time(),
            based_on_round=self.session.round_index if self.session else 0,
        )

    async def get_next_question_async(self) -> Dict[str, Any]:
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

        # Scheme 3: Try to use pregenerated question first
        question_data = None
        if self._pregenerated and self._pregenerated.is_fresh():
            pregen_q = self._pregenerated.get_next()
            if pregen_q:
                print(f"    [PREGEN] 使用预生成的问题 (节省 ~1.5s)")
                question_data = pregen_q

        # If no pregenerated question available, generate one
        if not question_data:
            if self.llm_client:
                target = self.probe_planner.plan_next(
                    state,
                    coverage_targets=self.protocol.coverage_targets,
                )
                q_start = time.time()
                loop = asyncio.get_event_loop()
                question_data = await loop.run_in_executor(
                    self.executor,
                    self.llm_client.generate_question,
                    target.model_dump(),
                    target.recommended_strategy or "ask_recent_example",
                    self.session.conversation_log,
                )
                print(f"    [DEBUG] 实时问题生成耗时: {time.time() - q_start:.2f}s")
            else:
                target = self.probe_planner.plan_next(
                    state,
                    coverage_targets=self.protocol.coverage_targets,
                )
                question_data = {
                    "question": self._get_default_question(target),
                    "strategy_used": target.recommended_strategy,
                }

        # Start pregenerating next batch for future rounds
        if self.llm_client and (not self._pregenerated or not self._pregenerated.questions):
            self._start_pregeneration()

        overall_elapsed = time.time() - overall_start
        print(f"    [DEBUG] 获取问题总耗时: {overall_elapsed:.2f}s")

        return {
            "status": "active",
            "question": question_data.get("question", "Tell me more."),
            "target_type": "unknown",
            "round_index": self.session.round_index,
        }

    async def submit_answer_async(self, answer: str) -> Dict[str, Any]:
        """Submit user answer and process it asynchronously."""
        if not self.session:
            raise RuntimeError("No active session. Call start_session() first.")

        # Log the answer
        self.session.conversation_log.append({
            "role": "user",
            "content": answer,
            "round_index": self.session.round_index,
            "timestamp": datetime.utcnow().isoformat(),
        })

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

            self._last_evidence_result = None

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

    def _process_evidence_sync(self, answer: str) -> Dict[str, Any]:
        """Process evidence synchronously using optimized single-call method."""
        start_time = time.time()
        print(f"    [DEBUG] 开始后台证据处理 (合并解析+提取)...")

        state = AssessmentState.model_validate(self.session.state)

        # Scheme 2: Use merged parse+extract in single LLM call
        combined_result = self.llm_client.parse_and_extract(
            self.protocol.model_dump(),
            state.model_dump(),
            answer,
        )

        observations = combined_result.get("observations", [])
        evidence_data_list = combined_result.get("evidence", [])
        contradiction_data_list = combined_result.get("contradiction_candidates", [])

        print(f"    [DEBUG]   - 解析+提取完成，发现 {len(evidence_data_list)} 条证据")

        # Convert to Evidence objects
        evidence_list = []
        for i, e_data in enumerate(evidence_data_list):
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
        for i, c_data in enumerate(contradiction_data_list):
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

        # Update state
        u_start = time.time()
        new_state = self.state_updater.update_state(
            state,
            evidence_list,
            self.session.round_index,
            coverage_targets=self.protocol.coverage_targets,
            new_contradictions=contradiction_list,
        )
        print(f"    [DEBUG]   - 更新状态: {time.time() - u_start:.2f}s")

        # Check termination
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
        print(f"    [DEBUG] 证据处理完成，总耗时: {elapsed:.2f}s (单次LLM调用)")

        return {
            "status": "active" if not termination.eligible else "complete",
            "parsed_observations": observations,
            "new_evidence": [e.model_dump() for e in evidence_list],
            "state": new_state.model_dump(),
            "termination": termination.model_dump(),
        }

    async def _wait_for_pending_evidence(self):
        """Wait for any pending evidence processing to complete."""
        if self._pending_evidence_futures:
            done, pending = await asyncio.wait(
                self._pending_evidence_futures,
                return_when=asyncio.ALL_COMPLETED,
            )
            self._pending_evidence_futures = list(pending)

            if done:
                self._last_evidence_result = done.pop().result()

    def _process_without_llm(self, answer: str) -> Dict[str, Any]:
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

    async def finalize_async(self) -> Dict[str, Any]:
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

        # Print cache stats
        if self.llm_client:
            hits = self.llm_client.cache_hits
            misses = self.llm_client.cache_misses
            total = hits + misses
            if total > 0:
                print(f"\n📊 缓存统计: {hits}/{total} 命中 ({hits/total*100:.1f}%)")

        return {
            "session_id": self.session.session_id,
            "status": "completed",
            "final_state": state.model_dump(),
            "report": report,
        }

    def _generate_report_sync(self, state: AssessmentState) -> Dict[str, Any]:
        """Synchronous wrapper for report generation."""
        return self.llm_client.generate_report(
            protocol=self.protocol.model_dump(),
            state=state.model_dump(),
            evidence=[],
        )

    def shutdown(self):
        """Shutdown the executor."""
        self.executor.shutdown(wait=True)
