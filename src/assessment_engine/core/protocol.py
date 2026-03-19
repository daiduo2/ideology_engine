from pydantic import BaseModel, Field


class Scale(BaseModel):
    min: float = Field(default=0, ge=-1)
    max: float = Field(default=1, le=1)
    default: float = Field(default=0.5)


class Dimension(BaseModel):
    id: str
    name: str
    description: str
    scale: Scale = Field(default_factory=lambda: Scale(min=0, max=1, default=0.5))


class StoppingRules(BaseModel):
    min_rounds: int = Field(default=6, ge=1)
    max_rounds: int = Field(default=15, ge=1)
    target_confidence: float = Field(default=0.72, ge=0, le=1)
    min_coverage_ratio: float = Field(default=0.8, ge=0, le=1)


class AssessmentProtocol(BaseModel):
    id: str
    name: str
    description: str
    dimensions: list[Dimension]
    coverage_targets: list[str]
    question_strategies: list[str]
    stopping_rules: StoppingRules
    report_template: str
