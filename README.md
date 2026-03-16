# Assessment Engine

A protocol-agnostic natural language assessment engine for conducting structured assessments through conversational interfaces.

## Overview

The Assessment Engine provides a framework for conducting systematic assessments using natural language conversations. It supports:

- **Protocol-driven assessments**: Define assessment protocols with dimensions, scales, and stopping rules
- **State management**: Track assessment state including dimension scores, confidence levels, and coverage
- **Evidence extraction**: Map conversational evidence to assessment dimensions
- **Contradiction detection**: Identify and track contradictory evidence
- **Smart probing**: Automatically determine the next question based on assessment state
- **Termination checking**: Determine when assessment criteria are met

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Define a Protocol

```python
from assessment_engine.core.protocol import AssessmentProtocol, Dimension, Scale, StoppingRules

protocol = AssessmentProtocol(
    id="communication-assessment",
    name="Communication Style Assessment",
    description="Assess communication patterns and preferences",
    dimensions=[
        Dimension(
            id="directness",
            name="Directness",
            description="Tendency to communicate directly vs indirectly",
            scale=Scale(min=0, max=1, default=0.5)
        ),
        Dimension(
            id="empathy",
            name="Empathy",
            description="Level of empathetic communication",
            scale=Scale(min=0, max=1, default=0.5)
        ),
    ],
    coverage_targets=["self_description", "recent_example", "decision_process"],
    question_strategies=["ask_recent_example", "ask_clarification"],
    stopping_rules=StoppingRules(
        min_rounds=6,
        max_rounds=15,
        target_confidence=0.72,
        min_coverage_ratio=0.8
    ),
    report_template="default"
)
```

### Create an Assessment Session

```python
from assessment_engine.core.session import AssessmentSession

session = AssessmentSession(
    session_id="session-001",
    protocol_id="communication-assessment",
    status="active"
)
```

### Update State with Evidence

```python
from assessment_engine.core.state import AssessmentState, DimensionState
from assessment_engine.core.evidence import Evidence, DimensionMapping
from assessment_engine.engine.state_updater import StateUpdater

# Initialize state
state = AssessmentState(
    dimensions={
        "directness": DimensionState(),
        "empathy": DimensionState()
    }
)

# Create evidence
evidence = Evidence(
    id="ev-001",
    round_index=1,
    raw_text="I prefer to get straight to the point in meetings",
    mapped_dimensions=[
        DimensionMapping(
            dimension_id="directness",
            direction=1.0,  # positive direction
            weight=0.8,
            confidence=0.9
        )
    ],
    tags=["self_description"]
)

# Update state
updater = StateUpdater(learning_rate=0.1)
new_state = updater.update_state(
    state=state,
    new_evidence=[evidence],
    round_index=1,
    coverage_targets=protocol.coverage_targets
)
```

### Plan Next Question

```python
from assessment_engine.engine.probe_planner import ProbePlanner

planner = ProbePlanner(protocol)
next_target = planner.plan_next(
    state=new_state,
    coverage_targets=protocol.coverage_targets
)

print(f"Next target: {next_target.target}")
print(f"Strategy: {next_target.recommended_strategy}")
```

### Check Termination

```python
from assessment_engine.engine.termination_checker import TerminationChecker

checker = TerminationChecker(protocol.stopping_rules)
status = checker.check(
    state=new_state,
    round_index=5,
    coverage_targets=protocol.coverage_targets
)

if status.eligible:
    print("Assessment can be terminated")
else:
    print(f"Continue: {status.reasons}")
```

### Persist Sessions

```python
from assessment_engine.storage.session_repo import SessionRepository
from assessment_engine.storage.protocol_repo import ProtocolRepository

# Save/load sessions
session_repo = SessionRepository(base_path="./sessions")
session_repo.save(session)
loaded_session = session_repo.load(session.session_id)

# Save/load protocols
protocol_repo = ProtocolRepository(base_path=".")
protocol_repo.save(protocol)
loaded_protocol = protocol_repo.load(protocol.id)
```

## Project Structure

```
assessment-engine/
├── src/assessment_engine/
│   ├── core/              # Core data models
│   │   ├── protocol.py    # Protocol, Dimension, Scale, StoppingRules
│   │   ├── session.py     # AssessmentSession
│   │   ├── state.py       # AssessmentState, DimensionState, Coverage
│   │   ├── evidence.py    # Evidence, DimensionMapping
│   │   └── contradiction.py # Contradiction
│   ├── engine/            # Assessment logic
│   │   ├── state_updater.py    # Update state from evidence
│   │   ├── probe_planner.py    # Determine next question
│   │   └── termination_checker.py # Check stopping conditions
│   ├── storage/           # Persistence layer
│   │   ├── session_repo.py     # File-based session storage
│   │   └── protocol_repo.py    # File-based protocol storage
│   ├── llm/               # LLM integration
│   │   ├── client.py      # Anthropic client wrapper
│   │   └── prompts/       # LLM prompts
│   │       ├── extract_evidence.py
│       ├── generate_question.py
│       ├── parse_response.py
│       └── generate_report.py
│   └── utils/             # Utilities
├── tests/                 # Test suite
├── protocols/             # Protocol definitions
└── sessions/              # Session storage
```

## Core Concepts

### Protocol

A protocol defines the structure of an assessment:

- **Dimensions**: The traits or characteristics being assessed (e.g., directness, empathy)
- **Scale**: The measurement scale for each dimension (default: 0-1)
- **Coverage Targets**: Areas that must be covered during assessment
- **Question Strategies**: Approaches for generating questions
- **Stopping Rules**: Criteria for when to end the assessment

### State

Assessment state tracks progress:

- **Dimensions**: Current scores and confidence levels for each dimension
- **Coverage**: Which coverage targets have been addressed
- **Evidence IDs**: References to collected evidence
- **Contradiction IDs**: References to detected contradictions
- **Open Questions**: Areas needing clarification

### Evidence

Evidence represents extracted information from conversations:

- **Raw Text**: The original conversational text
- **Mapped Dimensions**: How the evidence relates to assessment dimensions
- **Direction**: Whether evidence supports (+1) or contradicts (-1) a dimension
- **Weight**: The strength of the evidence (0-1)
- **Confidence**: Reliability of the evidence (0-1)

### Contradiction

Contradictions track conflicting evidence:

- **Severity**: low, medium, or high
- **Related Dimensions**: Which dimensions are affected
- **Needs Followup**: Whether the contradiction requires clarification

## Testing

Run the test suite:

```bash
python -m pytest tests/ -v
```

Run specific test modules:

```bash
python -m pytest tests/core/ -v
python -m pytest tests/engine/ -v
python -m pytest tests/storage/ -v
```

## Architecture

The Assessment Engine follows a layered architecture:

1. **Core Layer**: Pydantic models for data validation and serialization
2. **Engine Layer**: Pure functions for state updates, planning, and termination
3. **Storage Layer**: File-based repositories for persistence
4. **LLM Layer**: Integration with language models for natural language processing

### Design Principles

- **Immutability**: State updates return new state objects
- **Pure Functions**: Engine logic has no side effects
- **Type Safety**: Full type hints and Pydantic validation
- **Testability**: Comprehensive test coverage (80%+)
- **Extensibility**: Protocol-agnostic design

## License

MIT License
