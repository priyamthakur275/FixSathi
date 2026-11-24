import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

Appliance = Literal['ceiling_fan', 'split_ac', 'washing_machine', 'refrigerator', 'mcb_electrical', 'rooftop_solar', 'microwave_oven', 'water_purifier', 'unknown']


class SessionCreate(BaseModel):
    appliance_type: Appliance | None = None
    issue_description: str = Field(default='', max_length=2000)
    title: str | None = Field(default=None, max_length=160)


class SessionPatch(BaseModel):
    appliance_type: Appliance | None = None
    issue_description: str | None = Field(default=None, max_length=2000)
    title: str | None = Field(default=None, max_length=160)
    status: Literal['active', 'diagnosing', 'awaiting_confirmation', 'guidance_in_progress'] | None = None


class SessionOut(BaseModel):
    id: uuid.UUID
    reference: str
    title: str
    appliance_type: str
    appliance_label: str
    issue_description: str
    status: str
    technician_id: uuid.UUID
    technician_name: str | None
    first_time_fix: bool | None
    started_at: datetime
    completed_at: datetime | None
    demo: bool = False
    report_id: uuid.UUID | None = None


class MessageIn(BaseModel):
    text: str = Field(default='', max_length=4000)
    media_ids: list[uuid.UUID] = Field(default_factory=list, max_length=6)
    channel: Literal['text', 'voice'] = 'text'


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role: str
    message: str
    message_type: str
    meta: dict
    created_at: datetime


class ChatResult(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut | None
    ai_status: Literal['ok', 'unavailable', 'error']
    ai_error: dict | None = None


class MediaOut(BaseModel):
    id: uuid.UUID
    kind: str
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    url: str
    meta: dict
    created_at: datetime


class DiagnoseIn(BaseModel):
    media_ids: list[uuid.UUID] = Field(default_factory=list, max_length=3)


class DiagnosisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    problem_summary: str
    faults: list[dict]
    recommended_checks: list[str]
    follow_up_questions: list[str]
    safety_requirements: list[str]
    requires_escalation: bool
    confirmed_findings: list[str] = []
    missing_information: list[str] = []
    required_tools: list[str] = []
    escalation_reason: str | None = None
    knowledge_coverage: str = 'none'
    sources: list[dict] = []
    model_identifier: str
    created_at: datetime
    confidence_note: str = 'Confidence values are model estimates, not calibrated probabilities.'


class IdentifyIn(BaseModel):
    media_id: uuid.UUID
    query: str | None = Field(default=None, max_length=120)


class StepOut(BaseModel):
    id: uuid.UUID
    step_number: int
    title: str
    instruction: str | None
    kind: str
    requires_power_off: bool
    status: str
    locked: bool
    visual_media_id: uuid.UUID | None
    completed_at: datetime | None


class SafetyIn(BaseModel):
    power_off_confirmed: bool
    tester_checked: bool


class SafetyOut(BaseModel):
    power_off_confirmed: bool
    tester_checked: bool
    unlocked: bool
    missing: list[str]
    expired: bool
    confirmed_at: str | None
    expires_at: str | None
    disclaimer: str


class EscalateIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
    priority: Literal['low', 'normal', 'high'] = 'normal'


class EscalationPatch(BaseModel):
    status: Literal['open', 'in_review', 'resolved'] | None = None
    resolution_notes: str | None = Field(default=None, max_length=2000)


class ReportIn(BaseModel):
    outcome: Literal['resolved', 'not_resolved', 'escalated']
    first_time_fix: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    guidance_correct: bool | None = None
    comment: str | None = Field(default=None, max_length=1000)


class AnswerFeedbackIn(BaseModel):
    """Thumbs up / down on one AI answer. helpful=None clears the rating."""
    helpful: bool | None
    comment: str | None = Field(default=None, max_length=500)


class Page(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int
