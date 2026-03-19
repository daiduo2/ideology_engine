"""Protocol API routes."""

from fastapi import APIRouter, Depends

from assessment_engine.api.errors import ConflictError, NotFoundError
from assessment_engine.api.models import CreateProtocolRequest, ProtocolResponse
from assessment_engine.storage.protocol_repo import ProtocolRepository

router = APIRouter()


def get_protocol_repo() -> ProtocolRepository:
    """Get protocol repository instance."""
    from pathlib import Path

    base_path = Path(__file__).parent.parent.parent.parent.parent.resolve()
    return ProtocolRepository(base_path=base_path)


@router.get("", response_model=list[ProtocolResponse])
async def list_protocols(repo: ProtocolRepository = Depends(get_protocol_repo)):
    """List all available protocols."""
    protocols = repo.list_all()
    return [
        ProtocolResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            dimensions=[d.model_dump() for d in p.dimensions],
            coverage_targets=p.coverage_targets,
            stopping_rules=p.stopping_rules.model_dump(),
        )
        for p in protocols
    ]


@router.get("/{protocol_id}", response_model=ProtocolResponse)
async def get_protocol(protocol_id: str, repo: ProtocolRepository = Depends(get_protocol_repo)):
    """Get protocol by ID."""
    protocol = repo.load(protocol_id)
    if not protocol:
        raise NotFoundError("Protocol", protocol_id)

    return ProtocolResponse(
        id=protocol.id,
        name=protocol.name,
        description=protocol.description,
        dimensions=[d.model_dump() for d in protocol.dimensions],
        coverage_targets=protocol.coverage_targets,
        stopping_rules=protocol.stopping_rules.model_dump(),
    )


@router.post("", response_model=ProtocolResponse, status_code=201)
async def create_protocol(
    request: CreateProtocolRequest, repo: ProtocolRepository = Depends(get_protocol_repo)
):
    """Create a new protocol."""
    # Check if protocol already exists
    existing = repo.load(request.id)
    if existing:
        raise ConflictError(f"Protocol '{request.id}' already exists")

    # Create protocol
    from assessment_engine.core.protocol import AssessmentProtocol, Dimension, StoppingRules

    dimensions = [Dimension(**d) for d in request.dimensions]
    stopping_rules = StoppingRules(**request.stopping_rules)

    protocol = AssessmentProtocol(
        id=request.id,
        name=request.name,
        description=request.description,
        dimensions=dimensions,
        coverage_targets=request.coverage_targets or [],
        question_strategies=request.question_strategies or [],
        stopping_rules=stopping_rules,
        report_template=request.report_template,
    )

    repo.save(protocol)

    return ProtocolResponse(
        id=protocol.id,
        name=protocol.name,
        description=protocol.description,
        dimensions=[d.model_dump() for d in protocol.dimensions],
        coverage_targets=protocol.coverage_targets,
        stopping_rules=protocol.stopping_rules.model_dump(),
    )


@router.delete("/{protocol_id}", status_code=204)
async def delete_protocol(protocol_id: str, repo: ProtocolRepository = Depends(get_protocol_repo)):
    """Delete a protocol."""
    import os

    protocol = repo.load(protocol_id)
    if not protocol:
        raise NotFoundError("Protocol", protocol_id)

    # Find and delete file
    file_path = repo._find_protocol_file(protocol_id)
    if file_path and file_path.exists():
        os.remove(file_path)

    return None
