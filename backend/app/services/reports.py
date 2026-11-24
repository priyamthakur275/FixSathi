import secrets
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..core.exceptions import Conflict, Forbidden
from ..db.models import (DiagnosisResult, EscalationRequest, Feedback, IdentifiedComponent, RepairSession, RepairStep, SafetyEvent, ServiceReport, User)
from .safety import DISCLAIMER, current_state
from .sessions import APPLIANCE_LABELS, transition


def build_report_data(db: Session, s: RepairSession, outcome: str, notes: str | None) -> dict:
    """Built only from recorded data. Steps not marked completed are listed as not performed."""
    d = db.scalars(select(DiagnosisResult).where(DiagnosisResult.session_id == s.id).order_by(DiagnosisResult.created_at.desc()).limit(1)).first()
    steps = db.scalars(select(RepairStep).where(RepairStep.session_id == s.id).order_by(RepairStep.step_number)).all()
    comps = db.scalars(select(IdentifiedComponent).where(IdentifiedComponent.session_id == s.id)).all()
    events = db.scalars(select(SafetyEvent).where(SafetyEvent.session_id == s.id).order_by(SafetyEvent.created_at)).all()
    esc = db.scalars(select(EscalationRequest).where(EscalationRequest.session_id == s.id)).all()
    fb = db.scalars(select(Feedback).where(Feedback.session_id == s.id)).first()
    st = current_state(db, s)
    return {
        'demo': bool((s.appliance_details or {}).get('demo_scenario')),
        'session': {'reference': s.reference, 'appliance_type': s.appliance_type, 'appliance': APPLIANCE_LABELS.get(s.appliance_type, s.appliance_type),
                    'title': s.title, 'started_at': s.started_at.isoformat(), 'technician': s.technician.full_name if s.technician else None},
        'customer_issue': s.issue_description,
        'diagnosis': {'problem_summary': d.problem_summary, 'faults': d.faults, 'model_identifier': d.model_identifier,
                      'note': 'AI-generated estimate reviewed by the technician; confidence values are model estimates.'} if d else None,
        'steps_performed': [{'step_number': x.step_number, 'title': x.title, 'completed_at': x.completed_at.isoformat() if x.completed_at else None} for x in steps if x.status == 'completed'],
        'steps_not_performed': [{'step_number': x.step_number, 'title': x.title} for x in steps if x.status != 'completed'],
        'parts_identified': [{'name': c.result.get('component_name'), 'explanation': c.result.get('explanation')} for c in comps if c.result.get('found')],
        'safety': {'final_state': {'power_off_confirmed': st.power_off_confirmed, 'tester_checked': st.tester_checked, 'expired': st.expired},
                   'confirmation_events': [{'at': e.created_at.isoformat(), **e.details} for e in events if e.event_type == 'confirmation_changed'],
                   'blocked_attempts': sum(1 for e in events if e.blocked), 'disclaimer': DISCLAIMER},
        'escalations': [{'reason': e.reason, 'status': e.status} for e in esc],
        'resolution': {'outcome': outcome, 'first_time_fix': s.first_time_fix, 'notes': notes},
        'feedback': {'rating': fb.rating, 'guidance_correct': fb.guidance_correct, 'comment': fb.comment} if fb else None,
    }


def create_report(db: Session, s: RepairSession, user: User, outcome: str, first_time_fix: bool | None, notes: str | None) -> ServiceReport:
    if s.technician_id != user.id:
        raise Forbidden('Only the session technician can generate its report.')
    if db.scalar(select(func.count()).select_from(ServiceReport).where(ServiceReport.session_id == s.id)):
        raise Conflict('A report already exists for this session.', code='REPORT_EXISTS')
    s.first_time_fix = first_time_fix if outcome == 'resolved' else False if first_time_fix is not None else None
    s.resolution_notes = notes
    if outcome == 'escalated':
        transition(s, 'escalated')
    elif s.status != 'completed':
        transition(s, 'completed')
    r = ServiceReport(reference='R-' + secrets.token_hex(3).upper(), session_id=s.id, technician_id=s.technician_id, organisation_id=s.organisation_id,
                      resolution_status=outcome, report_data=build_report_data(db, s, outcome, notes))
    db.add(r); db.flush()
    return r


def refresh_feedback(db: Session, s: RepairSession) -> None:
    r = db.scalars(select(ServiceReport).where(ServiceReport.session_id == s.id)).first()
    if r:
        fb = db.scalars(select(Feedback).where(Feedback.session_id == s.id)).first()
        data = dict(r.report_data); data['feedback'] = {'rating': fb.rating, 'guidance_correct': fb.guidance_correct, 'comment': fb.comment} if fb else None
        r.report_data = data
