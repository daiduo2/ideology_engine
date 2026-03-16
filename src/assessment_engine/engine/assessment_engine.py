"""Main Assessment Engine orchestrator."""
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from assessment_engine.core.protocol import AssessmentProtocol
from assessment_engine.core.session import AssessmentSession
from assessment_engine.core.state import AssessmentState, DimensionState, Coverage, TerminationStatus
from assessment_engine.core.evidence import Evidence, DimensionMapping
from assessment_engine.core.contradiction import Contradiction
from assessment_engine.engine.state_updater import StateUpdater
from assessment_engine.engine.termination_checker import TerminationChecker
from assessment_engine.engine.probe_planner import ProbePlanner


class AssessmentEngine:
    """Main orchestrator for natural language assessment."""

    def __init__(
        self,
        protocol: AssessmentProtocol,
        llm_client: Optional[Any] = None,
        learning_rate: float = 0.1,
    ):
        self.protocol = protocol
        self.llm_client = llm_client
        self.session: Optional[AssessmentSession] = None
        self.state_updater = StateUpdater(learning_rate=learning_rate)
        self.termination_checker = TerminationChecker(protocol.stopping_rules)
        self.probe_planner = ProbePlanner(protocol)

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

        return self.session

    def get_next_question(self) -> Dict[str, Any]:
        """Get the next question for the user."""
        if not self.session:
            raise RuntimeError("No active session. Call start_session() first.")

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
            question_data = self.llm_client.generate_question(
                target=target.model_dump(),
                strategy=target.recommended_strategy or "ask_recent_example",
                conversation_history=self.session.conversation_log,
            )
        else:
            # Default question without LLM
            question_data = {
                "question": self._get_default_question(target),
                "strategy_used": target.recommended_strategy,
            }

        return {
            "status": "active",
            "question": question_data.get("question", "Tell me more."),
            "target_type": target.type,
            "target": target.target,
            "round_index": self.session.round_index,
        }

    def submit_answer(self, answer: str) -> Dict[str, Any]:
        """Submit user answer and process it."""
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
            result = self._process_with_llm(answer)
        else:
            result = self._process_without_llm(answer)

        # Update session
        self.session.round_index += 1
        self.session.state = result["state"]
        self.session.updated_at = datetime.utcnow()

        return result

    def _process_with_llm(self, answer: str) -> Dict[str, Any]:
        """Process answer using LLM."""
        state = AssessmentState.model_validate(self.session.state)

        # 1. Parse response
        parsed = self.llm_client.parse_response(
            protocol_summary=self.protocol.model_dump_json(),
            state_summary=state.model_dump_json(),
            user_answer=answer,
        )

        # 2. Extract evidence
        evidence_data = self.llm_client.extract_evidence(
            protocol=self.protocol.model_dump(),
            observations=parsed.get("observations", []),
            current_state=state.model_dump(),
        )

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
        new_state = self.state_updater.update_state(
            state,
            evidence_list,
            self.session.round_index,
            coverage_targets=self.protocol.coverage_targets,
            new_contradictions=contradiction_list,
        )

        # 4. Check termination
        termination = self.termination_checker.check(
            new_state,
            self.session.round_index,
            coverage_targets=self.protocol.coverage_targets,
            unresolved_contradictions=contradiction_list,
        )

        new_state.termination = termination

        return {
            "status": "active" if not termination.eligible else "complete",
            "parsed_observations": parsed.get("observations", []),
            "new_evidence": [e.model_dump() for e in evidence_list],
            "state": new_state.model_dump(),
            "termination": termination.model_dump(),
        }

    def _process_without_llm(self, answer: str) -> Dict[str, Any]:
        """Process answer without LLM (placeholder for testing)."""
        state = AssessmentState.model_validate(self.session.state)

        # Simple update - just increment round
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

    def finalize(self) -> Dict[str, Any]:
        """Finalize assessment and generate report."""
        if not self.session:
            raise RuntimeError("No active session.")

        self.session.status = "completed"
        state = AssessmentState.model_validate(self.session.state)

        if self.llm_client:
            report = self.llm_client.generate_report(
                protocol=self.protocol.model_dump(),
                state=state.model_dump(),
                evidence=[],  # Would load from storage
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

    def get_debug_trace(self) -> Dict[str, Any]:
        """Get debug trace for current session."""
        if not self.session:
            raise RuntimeError("No active session.")

        return {
            "session_id": self.session.session_id,
            "round_index": self.session.round_index,
            "conversation_log": self.session.conversation_log,
            "current_state": self.session.state,
        }
