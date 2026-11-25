"""Similar-repair retrieval. Embeddings mode uses Gemini embeddings stored in repair_embeddings and cosine similarity in Python.
Keyword mode always works. The response states which mode was used. ScaNN / pgvector are NOT used here (see docs/RAG_PIPELINE.md)."""
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..core.exceptions import AppError
from ..core.logging import log
from ..db.models import RepairEmbedding, RepairSession, ServiceReport, User
from . import knowledge_base as kb
from ..integrations.gemini.client import get_gemini
from .knowledge import cosine, tokens

logger = logging.getLogger('retrieval')


def record_title(r: dict) -> str:
    """'LG split ac: code CH38' or 'Kent water purifier: purifier beeping continuously'. The category alone ('ceiling fan',
    five times over) told the technician nothing about which record was which."""
    head = f"{r.get('appliance_brand') or ''} {r['appliance_category'].replace('_', ' ')}".strip()
    what = f"code {r['error_code']}" if r.get('error_code') else next(iter(r.get('reported_symptoms') or []), '') or next(iter(r.get('possible_faults') or []), '')
    return f'{head}: {what}' if what else head


def _session_text(s: RepairSession, r: ServiceReport | None) -> str:
    d = (r.report_data if r else {}) or {}
    dg = d.get('diagnosis') or {}; res = d.get('resolution') or {}
    return ' | '.join(str(x) for x in [s.appliance_type, s.title, s.issue_description, dg.get('problem_summary', ''),
                                       ', '.join(f.get('fault', '') for f in dg.get('faults', [])), res.get('notes') or ''] if x)


def _scoped_sessions(db: Session, user: User):
    q = select(RepairSession, ServiceReport).join(ServiceReport, ServiceReport.session_id == RepairSession.id)
    if user.role == 'technician':
        q = q.where(RepairSession.technician_id == user.id)
    elif user.role == 'manager':
        q = q.where(RepairSession.organisation_id == user.organisation_id) if user.organisation_id else q.where(RepairSession.id.is_(None))
    return db.execute(q).all()


async def index_session(db: Session, s: RepairSession, r: ServiceReport) -> bool:
    if get_settings().vector_search_mode == 'keyword' or not get_gemini().configured or not get_settings().gemini_embed_model:
        return False
    try:
        (vec,), model = await get_gemini().embed([_session_text(s, r)])
    except AppError as e:
        log(logger, 'embed_failed', logging.WARNING, code=e.code); return False
    db.add(RepairEmbedding(source_type='session', source_id=s.id, organisation_id=s.organisation_id, technician_id=s.technician_id, appliance_type=s.appliance_type,
                           content=_session_text(s, r), model_identifier=model, dimensions=len(vec), vector=vec))
    return True


async def search(db: Session, user: User, query: str, appliance: str | None, exclude=None, k: int = 5) -> dict:
    sessions = {s.id: (s, r) for s, r in _scoped_sessions(db, user) if s.id != exclude}
    mode, reason, results = 'keyword', None, []
    st = get_settings()
    embedded: set = set()
    if st.vector_search_mode != 'keyword' and get_gemini().configured and st.gemini_embed_model:
        mdl = get_gemini().model('embed')
        emb = db.scalars(select(RepairEmbedding).where(RepairEmbedding.model_identifier == mdl, RepairEmbedding.source_type == 'session',
                                                      RepairEmbedding.source_id.in_(list(sessions) or [None]))).all()
        if emb:  # embed the query only when there is something to compare it with (saves free-tier quota)
            try:
                (qv,), _ = await get_gemini().embed([query], task='RETRIEVAL_QUERY')
                mode = 'embeddings'
                for e in emb:
                    if e.dimensions != len(qv):
                        continue
                    embedded.add(e.source_id)
                    if appliance and appliance != 'unknown' and e.appliance_type != appliance:
                        continue
                    results.append((cosine(qv, e.vector), e.source_type, e.source_id, e.content))
            except AppError as e:
                reason = f'Embedding call failed ({e.code}).'
        else:
            reason = 'No embeddings indexed yet for the configured model.'
    else:
        reason = 'Embedding model not configured or VECTOR_SEARCH_MODE=keyword.'
    q = tokens(query)
    for sid, (s, r) in sessions.items():  # keyword score for every session without a vector (all of them in keyword mode)
        if sid in embedded or (appliance and appliance != 'unknown' and s.appliance_type != appliance):
            continue
        t = _session_text(s, r); sc = len(q & tokens(t)) / (len(q) or 1)
        if sc > 0: results.append((sc, 'session', sid, t))
    results.sort(key=lambda x: -x[0])
    # Knowledge records use their own index (scripts/index_knowledge.py), independent of whether past sessions have vectors.
    kres = await kb.retrieve(db, query, category=appliance, k=k)
    out = []
    for score, typ, sid, text in results[:k]:
        if typ == 'session' and sid in sessions:
            s, r = sessions[sid]
            out.append({'source_type': 'session', 'source_id': str(sid), 'reference': s.reference, 'report_id': str(r.id), 'title': s.title, 'appliance_type': s.appliance_type,
                        'score': round(score, 3), 'snippet': text[:220], 'why': 'Similar past repair in your permitted history'})
    for h in kres['hits']:
        r = h.record
        title = record_title(r)
        out.append({'source_type': 'knowledge', 'source_id': h.record_id, 'reference': h.record_id, 'title': title, 'appliance_type': r['appliance_category'],
                    'score': round(h.score, 3), 'snippet': '; '.join((r.get('possible_faults') or r.get('reported_symptoms') or [])[:2])[:220],
                    'why': f"{r['source_name']} ({r['verification_status']}{', related category' if h.related else ''})",
                    'source_url': r.get('source_url'), 'license': r['source_license'], 'verification_status': r['verification_status']})
    return {'mode': mode, 'fallback_reason': reason, 'knowledge_mode': kres['mode'], 'results': out}
