from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

APPLIANCES = ('ceiling_fan', 'split_ac', 'washing_machine', 'refrigerator', 'mcb_electrical', 'rooftop_solar', 'microwave_oven', 'water_purifier', 'unknown')
EvidenceSource = Literal['observed_in_image', 'technician_statement', 'ai_inference', 'unknown']


class Evidence(BaseModel):
    source: EvidenceSource
    detail: str = Field(max_length=400)


class Fault(BaseModel):
    fault: str = Field(max_length=120)
    explanation: str = Field(max_length=600)
    confidence: float = Field(ge=0, le=1, description='Model estimate, not a calibrated probability')
    evidence: list[Evidence] = Field(default_factory=list, max_length=8)
    status: Literal['supported_by_records', 'possible_cause', 'unverified_hypothesis'] = 'possible_cause'
    record_ids: list[str] = Field(default_factory=list, max_length=6, description='Only ids from the supplied <knowledge> block')


class DiagnosisOutput(BaseModel):
    appliance_type: str
    problem_summary: str = Field(max_length=400)
    possible_faults: list[Fault] = Field(default_factory=list, max_length=6)
    recommended_checks: list[str] = Field(default_factory=list, max_length=8)
    follow_up_questions: list[str] = Field(default_factory=list, max_length=5)
    safety_requirements: list[str] = Field(default_factory=list, max_length=8)
    requires_escalation: bool = False
    confirmed_findings: list[str] = Field(default_factory=list, max_length=8, description='Only what the technician stated or what is clearly visible')
    missing_information: list[str] = Field(default_factory=list, max_length=6)
    required_tools: list[str] = Field(default_factory=list, max_length=8, description='Tools the checks need, e.g. tester, multimeter, screwdriver set')
    escalation_reason: str | None = Field(default=None, max_length=300, description='Why a senior technician is needed, when requires_escalation is true')

    @field_validator('appliance_type')
    @classmethod
    def _app(cls, v: str) -> str:
        return v if v in APPLIANCES else 'unknown'


class StepOut(BaseModel):
    title: str = Field(max_length=160)
    instruction: str = Field(max_length=800)
    kind: Literal['observation', 'diagnostic_check', 'safe_action', 'power_sensitive', 'escalation']
    requires_power_off: bool


class GuidanceOutput(BaseModel):
    steps: list[StepOut] = Field(min_length=1, max_length=12)
    escalation_recommendation: str | None = None
    record_ids: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode='after')
    def _force_power(self):
        # Never trust the model to label power-sensitive work correctly: a power_sensitive kind always requires power off.
        for s in self.steps:
            if s.kind == 'power_sensitive':
                s.requires_power_off = True
        return self


class BoundingBox(BaseModel):
    """Normalised 0-1000 coordinates relative to the original image (x right, y down)."""
    x_min: int = Field(ge=0, le=1000)
    y_min: int = Field(ge=0, le=1000)
    x_max: int = Field(ge=0, le=1000)
    y_max: int = Field(ge=0, le=1000)

    @model_validator(mode='after')
    def _order(self):
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError('box must have positive width and height')
        return self


class ComponentOut(BaseModel):
    found: bool
    component_name: str | None = Field(default=None, max_length=120)
    explanation: str = Field(max_length=600)
    box: BoundingBox | None = None
    confidence: float = Field(ge=0, le=1)
    uncertainty: str | None = Field(default=None, max_length=300)
    safety_warnings: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode='after')
    def _consistent(self):
        if not self.found:
            self.box = None
        return self
