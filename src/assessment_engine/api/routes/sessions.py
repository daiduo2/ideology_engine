"""Session API routes."""

from fastapi import APIRouter, Depends

from assessment_engine.api.errors import NotFoundError, ValidationError
from assessment_engine.api.models import (
    FinalizeResponse,
    QuestionResponse,
    ReportResponse,
    SessionResponse,
    StartSessionRequest,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from assessment_engine.engine.assessment_engine import AssessmentEngine
from assessment_engine.llm import LLMConfig, create_llm_client
from assessment_engine.storage.protocol_repo import ProtocolRepository
from assessment_engine.storage.session_repo import SessionRepository

router = APIRouter()


def get_protocol_repo() -> ProtocolRepository:
    """Get protocol repository instance."""
    from pathlib import Path

    base_path = Path(__file__).parent.parent.parent.parent.parent.resolve()
    return ProtocolRepository(base_path=base_path)


def get_session_repo() -> SessionRepository:
    """Get session repository instance."""
    from pathlib import Path

    base_path = Path(__file__).parent.parent.parent.parent.parent.resolve()
    return SessionRepository(base_path=base_path)


def get_llm_client():
    """Get LLM client from environment or None."""
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    base_url = os.environ.get("LLM_BASE_URL")
    provider = os.environ.get("LLM_PROVIDER", "anthropic")
    model = os.environ.get("LLM_MODEL", "claude-opus-4-6")

    config = LLMConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    return create_llm_client(config)


def create_engine(protocol_id: str) -> AssessmentEngine:
    """Create assessment engine for protocol."""
    repo = get_protocol_repo()
    protocol = repo.load(protocol_id)

    if not protocol:
        raise NotFoundError("Protocol", protocol_id)

    llm_client = get_llm_client()
    return AssessmentEngine(protocol=protocol, llm_client=llm_client)


@router.post("", response_model=SessionResponse, status_code=201)
async def start_session(
    request: StartSessionRequest, session_repo: SessionRepository = Depends(get_session_repo)
):
    """Start a new assessment session."""
    engine = create_engine(request.protocol_id)
    session = engine.start_session(user_context=request.user_context)

    # Save session
    session_repo.save(session)

    return SessionResponse(
        session_id=session.session_id,
        protocol_id=session.protocol_id,
        status=session.status,
        round_index=session.round_index,
        state=session.state.model_dump() if session.state else {},
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, session_repo: SessionRepository = Depends(get_session_repo)):
    """Get session by ID."""
    session = session_repo.load(session_id)
    if not session:
        raise NotFoundError("Session", session_id)

    return SessionResponse(
        session_id=session.session_id,
        protocol_id=session.protocol_id,
        status=session.status,
        round_index=session.round_index,
        state=session.state.model_dump() if session.state else {},
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.post("/{session_id}/answers", response_model=SubmitAnswerResponse)
async def submit_answer(
    session_id: str,
    request: SubmitAnswerRequest,
    session_repo: SessionRepository = Depends(get_session_repo),
):
    """Submit an answer and get next state."""
    session = session_repo.load(session_id)
    if not session:
        raise NotFoundError("Session", session_id)

    if session.status == "completed":
        raise ValidationError("Session is already completed")

    engine = create_engine(session.protocol_id)
    engine.session = session
    engine.current_state = session.state

    result = engine.submit_answer(request.answer)

    # Save updated session
    session_repo.save(session)

    return SubmitAnswerResponse(
        status=result["status"],
        round_index=session.round_index,
        observations=result.get("observations", []),
        evidence=result.get("evidence", []),
        state=result.get("state", {}),
        is_complete=result["status"] == "complete",
    )


@router.get("/{session_id}/next-question", response_model=QuestionResponse)
async def get_next_question(
    session_id: str, session_repo: SessionRepository = Depends(get_session_repo)
):
    """Get the next question for the session."""
    session = session_repo.load(session_id)
    if not session:
        raise NotFoundError("Session", session_id)

    engine = create_engine(session.protocol_id)
    engine.session = session
    engine.current_state = session.state

    result = engine.get_next_question()

    if result["status"] == "complete":
        return QuestionResponse(
            question="",
            round_index=session.round_index,
            strategy=None,
            target_dimension=None,
        )

    return QuestionResponse(
        question=result["question"],
        round_index=result["round_index"],
        strategy=result.get("strategy"),
        target_dimension=result.get("target_dimension"),
    )


@router.post("/{session_id}/finalize", response_model=FinalizeResponse)
async def finalize_session(
    session_id: str, session_repo: SessionRepository = Depends(get_session_repo)
):
    """Finalize the assessment and generate report."""
    session = session_repo.load(session_id)
    if not session:
        raise NotFoundError("Session", session_id)

    engine = create_engine(session.protocol_id)
    engine.session = session
    engine.current_state = session.state

    result = engine.finalize()

    # Save updated session
    session_repo.save(session)

    return FinalizeResponse(
        session_id=session.session_id,
        status=session.status,
        report=result.get("report", {}),
        final_state=result.get("final_state", {}),
    )


@router.get("/{session_id}/report", response_model=ReportResponse)
async def get_report(session_id: str, session_repo: SessionRepository = Depends(get_session_repo)):
    """Get the final report for a completed session."""
    session = session_repo.load(session_id)
    if not session:
        raise NotFoundError("Session", session_id)

    if session.status != "completed":
        raise ValidationError("Session is not completed yet")

    report_data = session.state.report if session.state and session.state.report else {}

    return ReportResponse(
        session_id=session.session_id,
        protocol_id=session.protocol_id,
        status=session.status,
        report=report_data,
        created_at=session.created_at.isoformat(),
        completed_at=session.updated_at.isoformat() if session.status == "completed" else None,
    )
