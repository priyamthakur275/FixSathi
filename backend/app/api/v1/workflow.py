import uuid
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...core.exceptions import NotFound, error_body
from ...core.quota import check_ai_quota
from ...demo.client import is_demo
from ...db.base import utcnow
from ...db.models import DiagnosisResult, IdentifiedComponent, RepairStep, SafetyEvent, User
from ...db.session import get_db
from ...dependencies import current_user
from ...schemas.repair import DiagnoseIn, DiagnosisOut, IdentifyIn, MediaOut, SafetyIn, SafetyOut, StepOut
from ...services import ai, retrieval, safety
from ...services.access import get_owned_session, get_readable_session
from ...services.sessions import ensure_open, transition
from .serializers import media_out, step_out

router = APIRouter(tags=['workflow'])


def safety_out(st: safety.SafetyState) -> SafetyOut:
    return SafetyOut(power_off_confirmed=st.power_off_confirmed, tester_checked=st.tester_checked, unlocked=st.unlocked, missing=st.missing,
                     expired=st.expired, confirmed_at=st.confirmed_at, expires_at=st.expires_at, disclaimer=safety.DISCLAIMER)


def _quota(u: User, s) -> None:
    if not is_demo(s):  # scripted demo sessions call no model
        check_ai_quota(u.id)


@router.post('/sessions/{session_id}/diagnose', response_model=DiagnosisOut, status_code=201)
async def diagnose(session_id: uuid.UUID, body: DiagnoseIn | None = None, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id)
    _quota(u, s)
    return DiagnosisOut.model_validate(await ai.diagnose(db, s, (body.media_ids if body else None) or None))


@router.get('/sessions/{session_id}/diagnosis', response_model=DiagnosisOut | None)
def latest_diagnosis(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_readable_session(db, u, session_id)
    d = db.scalars(select(DiagnosisResult).where(DiagnosisResult.session_id == s.id).order_by(DiagnosisResult.created_at.desc()).limit(1)).first()
    return DiagnosisOut.model_validate(d) if d else None


@router.get('/diagnoses', response_model=list[dict])
def my_diagnoses(limit: int = Query(20, ge=1, le=100), u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    from ...services.access import session_scope
    from ...db.models import RepairSession
    ids = session_scope(u).with_only_columns(RepairSession.id).scalar_subquery()
    rows = db.execute(select(DiagnosisResult, RepairSession).join(RepairSession, RepairSession.id == DiagnosisResult.session_id)
                      .where(DiagnosisResult.session_id.in_(ids)).order_by(DiagnosisResult.created_at.desc()).limit(limit)).unique().all()
    return [{'id': str(d.id), 'session_id': str(s.id), 'reference': s.reference, 'title': s.title, 'problem_summary': d.problem_summary,
             'top_fault': d.faults[0] if d.faults else None, 'created_at': d.created_at.isoformat()} for d, s in rows]


@router.post('/sessions/{session_id}/identify-component', status_code=201)
async def identify(session_id: uuid.UUID, body: IdentifyIn, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id)
    _quota(u, s)
    c: IdentifiedComponent = await ai.identify_component(db, s, body.media_id, body.query)
    return {'id': str(c.id), 'media_id': str(c.media_id), 'coordinate_system': 'normalised 0-1000, origin top-left of the original image',
            **c.result, 'note': 'Visual identification only. The component has not been measured or tested.'}


@router.get('/sessions/{session_id}/steps', response_model=list[StepOut])
def steps(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_readable_session(db, u, session_id)
    unlocked = safety.current_state(db, s).unlocked and u.id == s.technician_id
    return [step_out(x, unlocked) for x in db.scalars(select(RepairStep).where(RepairStep.session_id == s.id).order_by(RepairStep.step_number))]


@router.post('/sessions/{session_id}/steps/generate', response_model=list[StepOut], status_code=201)
async def generate(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id)
    _quota(u, s)
    out = await ai.generate_steps(db, s)
    unlocked = safety.current_state(db, s).unlocked
    return [step_out(x, unlocked) for x in out]


@router.post('/sessions/{session_id}/steps/{step_id}/complete', response_model=StepOut)
def complete_step(session_id: uuid.UUID, step_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id, lock=True); ensure_open(s)
    x = db.get(RepairStep, step_id)
    if not x or x.session_id != s.id:
        raise NotFound('Step not found in this session.')
    d = safety.guard(db, s, u, f'complete_step:{x.step_number}:{x.title}', x.requires_power_off, actor='api')
    if not d.allowed:
        db.commit()  # keep the blocked-attempt record even though the request fails
        return JSONResponse(error_body('SAFETY_CONFIRMATION_REQUIRED', 'Record both safety statements before this step.', d.as_dict()), status_code=409)
    if x.status != 'completed':
        x.status = 'completed'; x.completed_at = utcnow()
    return step_out(x, True)


@router.post('/sessions/{session_id}/steps/{step_id}/reopen', response_model=StepOut)
def reopen_step(session_id: uuid.UUID, step_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id); ensure_open(s)
    x = db.get(RepairStep, step_id)
    if not x or x.session_id != s.id:
        raise NotFound('Step not found in this session.')
    x.status = 'pending'; x.completed_at = None
    return step_out(x, safety.current_state(db, s).unlocked)


@router.post('/sessions/{session_id}/steps/{step_id}/visual', response_model=MediaOut, status_code=201)
async def step_visual(session_id: uuid.UUID, step_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id)
    x = db.get(RepairStep, step_id)
    if not x or x.session_id != s.id:
        raise NotFound('Step not found in this session.')
    if x.requires_power_off and not safety.current_state(db, s).unlocked:
        d = safety.guard(db, s, u, f'visual_for_step:{x.step_number}', True, actor='api'); db.commit()
        return JSONResponse(error_body('SAFETY_CONFIRMATION_REQUIRED', 'Record both safety statements first.', d.as_dict()), status_code=409)
    if not x.visual_media_id:  # an illustration already made is returned without a new call
        _quota(u, s)
    return media_out(await ai.step_visual(db, s, x))


@router.get('/sessions/{session_id}/safety', response_model=SafetyOut)
def get_safety(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return safety_out(safety.current_state(db, get_readable_session(db, u, session_id)))


@router.post('/sessions/{session_id}/safety/confirm', response_model=SafetyOut)
def confirm_safety(session_id: uuid.UUID, body: SafetyIn, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id, lock=True)
    st = safety.confirm(db, s, u, body.power_off_confirmed, body.tester_checked, source='ui')
    if s.status == 'awaiting_confirmation' and st.unlocked:
        transition(s, 'guidance_in_progress')
    return safety_out(st)


@router.get('/sessions/{session_id}/safety/events')
def safety_events(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_readable_session(db, u, session_id)
    return [{'id': str(e.id), 'event_type': e.event_type, 'attempted_action': e.attempted_action, 'actor': e.actor, 'blocked': e.blocked,
             'reason': e.reason, 'details': e.details, 'created_at': e.created_at.isoformat()}
            for e in db.scalars(select(SafetyEvent).where(SafetyEvent.session_id == s.id).order_by(SafetyEvent.created_at))]


@router.get('/sessions/{session_id}/similar-repairs')
async def similar(session_id: uuid.UUID, q: str | None = Query(None, max_length=300), u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_readable_session(db, u, session_id)
    return await retrieval.search(db, u, q or f'{s.title} {s.issue_description}', s.appliance_type, exclude=s.id)


@router.get('/ai/status')
def ai_status(u: User = Depends(current_user)):
    """What the server is configured with and how the last Gemini call went. No secrets: the key is reported only as present/absent."""
    from ...config import get_settings
    from ...integrations.gemini.client import LAST_STATUS
    s = get_settings()
    return {'configured': s.ai_configured, 'vertex_ai': s.google_genai_use_vertexai,
            'models': {'agent': s.gemini_agent_model, 'live': s.gemini_live_model, 'embed': s.gemini_embed_model, 'image': s.nano_banana_model},
            'last_call': {k: v for k, v in LAST_STATUS.items()}}


@router.get('/knowledge/search')
async def knowledge_search(q: str = Query(..., min_length=2, max_length=300), appliance_type: str | None = None, brand: str | None = Query(None, max_length=60),
                           model: str | None = Query(None, max_length=80), error_code: str | None = Query(None, max_length=20), k: int = Query(8, ge=1, le=25),
                           u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    from ...datasets.normalize import error_code as norm_code
    from ...services import knowledge_base as kb
    res = await kb.retrieve(db, q, category=appliance_type, brand=brand, model=model, error_codes=[norm_code(error_code)] if error_code else None, k=k)
    return {**{k_: v for k_, v in res.items() if k_ != 'hits'}, 'results': [{**h.citation(), 'score': round(h.score, 3), 'flags': h.flags, 'record': h.record} for h in res['hits']]}


@router.get('/knowledge/stats')
def knowledge_stats(u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    from ...services import knowledge_base as kb
    return kb.stats(db)


@router.get('/similar-repairs')
async def similar_free(q: str = Query(..., min_length=2, max_length=300), appliance_type: str | None = None, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return await retrieval.search(db, u, q, appliance_type)
