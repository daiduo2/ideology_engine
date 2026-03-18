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
- **REST API**: Full HTTP API for integration with external systems

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Start

### REST API

Start the API server:

```bash
python run_api.py
```

Or with uvicorn directly:

```bash
uvicorn run_api:app --reload
```

#### API Endpoints

**Health Check**
```bash
curl http://localhost:8000/health
```

**List Protocols**
```bash
curl http://localhost:8000/protocols
```

**Create Session**
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"protocol_id": "generic-assessment-v1"}'
```

**Get Next Question**
```bash
curl http://localhost:8000/sessions/{session_id}/next-question
```

**Submit Answer**
```bash
curl -X POST http://localhost:8000/sessions/{session_id}/answers \
  -H "Content-Type: application/json" \
  -d '{"answer": "I prefer to work in teams"}'
```

**Finalize Assessment**
```bash
curl -X POST http://localhost:8000/sessions/{session_id}/finalize
```

**Get Report**
```bash
curl http://localhost:8000/sessions/{session_id}/report
```

### Python API

#### Define a Protocol

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
│   │   ├── config.py      # Multi-provider LLM config
│   │   ├── factory.py     # LLM client factory
│   │   ├── base.py        # Base LLM client
│   │   ├── client.py      # Main LLM client
│   │   ├── providers/     # Provider implementations
│   │   │   ├── anthropic_client.py
│   │   │   └── openai_client.py
│   │   └── prompts/       # LLM prompts
│   │       ├── extract_evidence.py
│   │       ├── generate_question.py
│   │       ├── parse_response.py
│   │       └── generate_report.py
│   ├── api/               # REST API
│   │   ├── app.py         # FastAPI app factory
│   │   ├── models.py      # Request/response models
│   │   ├── errors.py      # API error classes
│   │   └── routes/        # API routes
│   │       ├── protocols.py
│   │       └── sessions.py
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

## Preset Protocol Templates

The Assessment Engine includes several pre-built protocol templates for common assessments:

### MBTI Assessment (`mbti-assessment`)

Assesses personality preferences across four dichotomies based on the Myers-Briggs Type Indicator framework:

- **Extraversion vs Introversion**: Energy source preference (scale: -1 to +1)
- **Sensing vs Intuition**: Information gathering preference (scale: -1 to +1)
- **Thinking vs Feeling**: Decision making preference (scale: -1 to +1)
- **Judging vs Perceiving**: Lifestyle approach preference (scale: -1 to +1)

**Coverage targets**: self_description, work_scenario, social_interaction, decision_making

### DISC Assessment (`disc-assessment`)

Evaluates behavioral preferences across four dimensions:

- **Dominance**: Control and assertiveness (scale: 0 to 1)
- **Influence**: Social interaction and persuasion (scale: 0 to 1)
- **Steadiness**: Patience and consistency (scale: 0 to 1)
- **Conscientiousness**: Accuracy and quality focus (scale: 0 to 1)

**Coverage targets**: work_pressure, team_collaboration, change_adaptation, rule_following

### Communication Style (`communication-style`)

Assesses communication preferences across three key dimensions:

- **Directness**: Straightforward vs nuanced messaging (scale: 0 to 1)
- **Empathy**: Emotional awareness and consideration (scale: 0 to 1)
- **Assertiveness**: Confidence in expressing needs (scale: 0 to 1)

**Coverage targets**: feedback_giving, conflict_handling, active_listening, clarity_expression

### Leadership Style (`leadership-style`)

Evaluates leadership approach across three complementary styles:

- **Visionary**: Inspiring and strategic direction-setting (scale: 0 to 1)
- **Coaching**: Developing individuals through guidance (scale: 0 to 1)
- **Commanding**: Directing with clear authority (scale: 0 to 1)

**Coverage targets**: team_motivation, delegation, crisis_management, development_focus

### Using Preset Protocols

```bash
# Create session with MBTI protocol
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"protocol_id": "mbti-assessment"}'
```

All preset protocols use the same stopping rules:
- Minimum 6 rounds, maximum 15 rounds
- Target confidence: 0.72
- Minimum coverage ratio: 0.8

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
5. **API Layer**: FastAPI REST endpoints for external integration

### Design Principles

- **Immutability**: State updates return new state objects
- **Pure Functions**: Engine logic has no side effects
- **Type Safety**: Full type hints and Pydantic validation
- **Testability**: Comprehensive test coverage (80%+)
- **Extensibility**: Protocol-agnostic design

## License

MIT License
