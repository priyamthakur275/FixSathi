import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, CheckConstraint, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base, CreatedMixin, IdMixin, JSONType, utcnow

ROLES = ('technician', 'manager', 'admin')
SESSION_STATES = ('created', 'active', 'diagnosing', 'awaiting_confirmation', 'guidance_in_progress', 'escalated', 'completed', 'cancelled')


class Organisation(IdMixin, CreatedMixin, Base):
    __tablename__ = 'organisations'
    name: Mapped[str] = mapped_column(String(120), unique=True)


class User(IdMixin, CreatedMixin, Base):
    __tablename__ = 'users'
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='technician')
    preferred_language: Mapped[str] = mapped_column(String(20), default='English')
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('organisations.id', ondelete='SET NULL'), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (CheckConstraint("role in ('technician','manager','admin')", name='role_valid'),)


class RefreshToken(IdMixin, CreatedMixin, Base):
    __tablename__ = 'refresh_tokens'
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RepairSession(IdMixin, CreatedMixin, Base):
    __tablename__ = 'repair_sessions'
    reference: Mapped[str] = mapped_column(String(16), unique=True)
    technician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('organisations.id', ondelete='SET NULL'), index=True)
    appliance_type: Mapped[str] = mapped_column(String(40), default='unknown')
    appliance_details: Mapped[dict] = mapped_column(JSONType, default=dict)
    title: Mapped[str] = mapped_column(String(160), default='New repair session')
    issue_description: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(30), default='active', index=True)
    first_time_fix: Mapped[bool | None] = mapped_column(Boolean)
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set when the technician deletes the conversation from their chat history. The session, its report and safety log are kept.
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    technician = relationship('User', lazy='joined')
    __table_args__ = (CheckConstraint("status in ('created','active','diagnosing','awaiting_confirmation','guidance_in_progress','escalated','completed','cancelled')", name='status_valid'),
                      Index('ix_sessions_tech_created', 'technician_id', 'created_at'))


class Conversation(IdMixin, CreatedMixin, Base):
    __tablename__ = 'conversations'
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system
    message: Mapped[str] = mapped_column(Text, default='')
    message_type: Mapped[str] = mapped_column(String(20), default='text')  # text | voice_transcript | image
    meta: Mapped[dict] = mapped_column('metadata', JSONType, default=dict)


class Media(IdMixin, CreatedMixin, Base):
    __tablename__ = 'media'
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), index=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    kind: Mapped[str] = mapped_column(String(20), default='capture')  # capture | upload | generated | document
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict] = mapped_column('metadata', JSONType, default=dict)


class DiagnosisResult(IdMixin, CreatedMixin, Base):
    __tablename__ = 'diagnosis_results'
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), index=True)
    problem_summary: Mapped[str] = mapped_column(Text, default='')
    faults: Mapped[list] = mapped_column(JSONType, default=list)
    recommended_checks: Mapped[list] = mapped_column(JSONType, default=list)
    follow_up_questions: Mapped[list] = mapped_column(JSONType, default=list)
    safety_requirements: Mapped[list] = mapped_column(JSONType, default=list)
    requires_escalation: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_findings: Mapped[list] = mapped_column(JSONType, default=list)
    missing_information: Mapped[list] = mapped_column(JSONType, default=list)
    required_tools: Mapped[list] = mapped_column(JSONType, default=list)
    escalation_reason: Mapped[str | None] = mapped_column(Text)
    knowledge_coverage: Mapped[str] = mapped_column(String(12), default='none')
    sources: Mapped[list] = mapped_column(JSONType, default=list)
    model_identifier: Mapped[str] = mapped_column(String(80))
    latency_ms: Mapped[int | None] = mapped_column(Integer)


class IdentifiedComponent(IdMixin, CreatedMixin, Base):
    __tablename__ = 'identified_components'
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), index=True)
    media_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('media.id', ondelete='CASCADE'))
    query: Mapped[str | None] = mapped_column(String(120))
    result: Mapped[dict] = mapped_column(JSONType, default=dict)
    model_identifier: Mapped[str] = mapped_column(String(80))


class RepairStep(IdMixin, CreatedMixin, Base):
    __tablename__ = 'repair_steps'
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), index=True)
    step_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(160))
    instruction: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(24), default='safe_action')  # observation | diagnostic_check | safe_action | power_sensitive | escalation
    requires_power_off: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default='pending')  # pending | completed | skipped
    visual_media_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('media.id', ondelete='SET NULL'))
    source: Mapped[str] = mapped_column(String(20), default='ai')
    source_record_ids: Mapped[list] = mapped_column(JSONType, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint('session_id', 'step_number', name='uq_repair_steps_session_step'),)


class SafetyConfirmation(IdMixin, Base):
    """Append-only record of technician-entered statements. The latest row for (session, technician) is the current state."""
    __tablename__ = 'safety_confirmations'
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), index=True)
    technician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    power_off_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    tester_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    confirmation_source: Mapped[str] = mapped_column(String(20), default='ui')


class SafetyEvent(IdMixin, CreatedMixin, Base):
    __tablename__ = 'safety_events'
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), index=True)
    technician_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    event_type: Mapped[str] = mapped_column(String(30))  # confirmation_changed | action_blocked | action_allowed
    attempted_action: Mapped[str | None] = mapped_column(String(120))
    actor: Mapped[str] = mapped_column(String(20), default='api')  # api | ai_tool | live
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSONType, default=dict)


class EscalationRequest(IdMixin, CreatedMixin, Base):
    __tablename__ = 'escalation_requests'
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), index=True)
    technician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    reason: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(10), default='normal')
    status: Mapped[str] = mapped_column(String(16), default='open', index=True)
    diagnosis_summary: Mapped[str | None] = mapped_column(Text)
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default='api')
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ServiceReport(IdMixin, CreatedMixin, Base):
    __tablename__ = 'service_reports'
    reference: Mapped[str] = mapped_column(String(16), unique=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), unique=True)
    technician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('organisations.id', ondelete='SET NULL'), index=True)
    report_data: Mapped[dict] = mapped_column(JSONType, default=dict)
    resolution_status: Mapped[str] = mapped_column(String(20))


class Feedback(IdMixin, CreatedMixin, Base):
    __tablename__ = 'feedback'
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('repair_sessions.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    rating: Mapped[int] = mapped_column(Integer)
    guidance_correct: Mapped[bool | None] = mapped_column(Boolean)
    comment: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint('rating between 1 and 5', name='rating_range'), UniqueConstraint('session_id', 'user_id', name='uq_feedback_session_user'))


class AIUsage(IdMixin, CreatedMixin, Base):
    __tablename__ = 'ai_usage'
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('repair_sessions.id', ondelete='SET NULL'), index=True)
    operation: Mapped[str] = mapped_column(String(40))
    model_identifier: Mapped[str] = mapped_column(String(80))
    latency_ms: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error_code: Mapped[str | None] = mapped_column(String(40))


class RepairEmbedding(IdMixin, CreatedMixin, Base):
    """Portable vector store: vectors kept as JSON arrays, compared in application code.
    On AlloyDB, migrate this column to `vector(n)` with a ScaNN index once the extension is verified there."""
    __tablename__ = 'repair_embeddings'
    source_type: Mapped[str] = mapped_column(String(20))  # knowledge | session
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('organisations.id', ondelete='CASCADE'), index=True)
    technician_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    appliance_type: Mapped[str] = mapped_column(String(40), index=True)
    content: Mapped[str] = mapped_column(Text)
    model_identifier: Mapped[str] = mapped_column(String(80))
    dimensions: Mapped[int] = mapped_column(Integer)
    vector: Mapped[list] = mapped_column(JSONType)
    __table_args__ = (UniqueConstraint('source_type', 'source_id', 'model_identifier', name='uq_repair_embeddings_source_model'),)
