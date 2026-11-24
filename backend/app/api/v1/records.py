import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ...core.exceptions import Conflict, NotFound
from ...db.base import utcnow
from ...db.models import DiagnosisResult, EscalationRequest, Feedback, RepairSession, ServiceReport, User
from ...db.session import get_db
from ...dependencies import current_user
from ...schemas.repair import EscalateIn, EscalationPatch, FeedbackIn, Page, ReportIn
from ...services import dashboard as dash, retrieval
from ...services.access import get_owned_session, get_readable_session, require_role, session_scope
from ...services.reports import create_report, refresh_feedback
from ...services.sessions import APPLIANCE_LABELS, ensure_open, transition

router = APIRouter(tags=['records'])


def report_out(r: ServiceReport, s: RepairSession) -> dict:
    return {'id': str(r.id), 'reference': r.reference, 'session_id': str(s.id), 'session_reference': s.reference, 'appliance_type': s.appliance_type,
            'appliance': APPLIANCE_LABELS.get(s.appliance_type, s.appliance_type), 'technician': s.technician.full_name if s.technician else None,
            'resolution_status': r.resolution_status, 'created_at': r.created_at.isoformat(), 'title': s.title, 'data': r.report_data}


def esc_out(e: EscalationRequest, s: RepairSession) -> dict:
    return {'id': str(e.id), 'session_id': str(s.id), 'session_reference': s.reference, 'appliance_type': s.appliance_type, 'technician': s.technician.full_name if s.technician else None,
            'reason': e.reason, 'priority': e.priority, 'status': e.status, 'diagnosis_summary': e.diagnosis_summary, 'resolution_notes': e.resolution_notes,
            'created_at': e.created_at.isoformat(), 'resolved_at': e.resolved_at.isoformat() if e.resolved_at else None}


@router.post('/sessions/{session_id}/reports', status_code=201)
async def make_report(session_id: uuid.UUID, body: ReportIn, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id, lock=True)
    r = create_report(db, s, u, body.outcome, body.first_time_fix, body.notes)
    await retrieval.index_session(db, s, r)
    return report_out(r, s)


@router.get('/reports', response_model=Page)
def reports(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    ids = session_scope(u).with_only_columns(RepairSession.id).scalar_subquery()
    q = select(ServiceReport, RepairSession).join(RepairSession, RepairSession.id == ServiceReport.session_id).where(ServiceReport.session_id.in_(ids))
    total = db.scalar(select(func.count()).select_from(ServiceReport).where(ServiceReport.session_id.in_(ids)))
    rows = db.execute(q.order_by(ServiceReport.created_at.desc()).limit(limit).offset(offset)).unique().all()
    return Page(items=[report_out(r, s) for r, s in rows], total=total or 0, limit=limit, offset=offset)


@router.get('/reports/{report_id}')
def report(report_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    r = db.get(ServiceReport, report_id)
    if not r:
        raise NotFound('Report not found.')
    return report_out(r, get_readable_session(db, u, r.session_id))


@router.get('/history', response_model=Page)
def history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), open_only: bool = False, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    from .serializers import session_out
    q = session_scope(u)
    if open_only:
        q = q.where(RepairSession.status.not_in(('completed', 'cancelled')))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(RepairSession.created_at.desc()).limit(limit).offset(offset)).unique().all()
    return Page(items=[session_out(db, s) for s in rows], total=total or 0, limit=limit, offset=offset)


@router.post('/sessions/{session_id}/feedback', status_code=201)
def feedback(session_id: uuid.UUID, body: FeedbackIn, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id)
    f = db.scalars(select(Feedback).where(Feedback.session_id == s.id, Feedback.user_id == u.id)).first()
    if f:
        f.rating, f.guidance_correct, f.comment = body.rating, body.guidance_correct, body.comment
    else:
        db.add(Feedback(session_id=s.id, user_id=u.id, **body.model_dump()))
    db.flush(); refresh_feedback(db, s)
    return {'ok': True}


@router.post('/sessions/{session_id}/escalate', status_code=201)
def escalate(session_id: uuid.UUID, body: EscalateIn, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id, lock=True); ensure_open(s)
    if db.scalar(select(func.count()).select_from(EscalationRequest).where(EscalationRequest.session_id == s.id, EscalationRequest.status != 'resolved')):
        raise Conflict('This session already has an open escalation.', code='ESCALATION_OPEN')
    d = db.scalars(select(DiagnosisResult).where(DiagnosisResult.session_id == s.id).order_by(DiagnosisResult.created_at.desc()).limit(1)).first()
    e = EscalationRequest(session_id=s.id, technician_id=u.id, reason=body.reason, priority=body.priority, diagnosis_summary=d.problem_summary if d else None)
    db.add(e); transition(s, 'escalated'); db.flush()
    return esc_out(e, s)


@router.get('/sessions/{session_id}/escalations')
def session_escalations(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_readable_session(db, u, session_id)
    return [esc_out(e, s) for e in db.scalars(select(EscalationRequest).where(EscalationRequest.session_id == s.id).order_by(EscalationRequest.created_at.desc()))]


@router.get('/escalations')
def escalations(status: str | None = None, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    ids = session_scope(u).with_only_columns(RepairSession.id).scalar_subquery()
    q = select(EscalationRequest, RepairSession).join(RepairSession, RepairSession.id == EscalationRequest.session_id).where(EscalationRequest.session_id.in_(ids))
    if status:
        q = q.where(EscalationRequest.status == status)
    return [esc_out(e, s) for e, s in db.execute(q.order_by(EscalationRequest.created_at.desc()).limit(100)).unique().all()]


@router.patch('/escalations/{escalation_id}')
def update_escalation(escalation_id: uuid.UUID, body: EscalationPatch, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    require_role(u, 'manager', 'admin')
    e = db.get(EscalationRequest, escalation_id)
    if not e:
        raise NotFound('Escalation not found.')
    s = get_readable_session(db, u, e.session_id)
    if body.status:
        e.status = body.status; e.assigned_to = e.assigned_to or u.id
        if body.status == 'resolved':
            e.resolved_at = utcnow()
            if s.status == 'escalated':
                transition(s, 'active')
    if body.resolution_notes is not None:
        e.resolution_notes = body.resolution_notes
    return esc_out(e, s)


@router.get('/dashboard/overview')
def overview(u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    require_role(u, 'manager', 'admin')
    return dash.overview(db, u)


@router.get('/dashboard/repairs')
def trend(days: int = Query(7, ge=1, le=60), u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    require_role(u, 'manager', 'admin')
    return dash.trend(db, u, days)


@router.get('/dashboard/technicians')
def techs(u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    require_role(u, 'manager', 'admin')
    return dash.technicians(db, u)


@router.get('/dashboard/metrics')
def metrics(u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    require_role(u, 'manager', 'admin')
    return {'ratings': dash.ratings(db, u)}
