"""Fault finder: look up an error code or a symptom in the repair records, without the AI.

Answers come straight from the sourced records, so they are instant, cost no Gemini quota and work when AI is not configured.
The safety rule still holds: a check or repair step from a record that needs the power isolated is sent as locked, without its
text, exactly as in a repair session. Opening a session and recording the two safety statements is the only way to read it.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ...core.power_rules import MICROWAVE_INTERNAL, step_needs_power_off
from ...db.models import User
from ...db.session import get_db
from ...dependencies import current_user
from ...services import knowledge_base as kb
from ...services.retrieval import record_title
from ...services.sessions import APPLIANCE_LABELS

router = APIRouter(tags=['lookup'])


def _steps(r: dict) -> tuple[list[dict], int]:
    out, locked = [], 0
    for text in (r.get('diagnostic_procedure') or [])[:6] + (r.get('repair_steps') or [])[:6]:
        lock = r['appliance_category'] == 'microwave_oven' and bool(MICROWAVE_INTERNAL.search(text)) or step_needs_power_off(text)
        locked += lock
        out.append({'text': None if lock else text, 'locked': lock})
    return out, locked


@router.get('/lookup')
async def lookup(q: str = Query(..., min_length=1, max_length=200), appliance_type: str | None = Query(None, max_length=40),
                 u: User = Depends(current_user), db: Session = Depends(get_db, scope='function')):
    """Records for an error code or symptom, best first. Keyword and error-code channels only: no AI call."""
    res = await kb.retrieve(db, q, category=appliance_type or None, k=8, use_embeddings=False)
    results = []
    hits = res['hits']
    if res['error_codes_found']:  # a code on the display was asked about: other records are noise
        hits = [h for h in hits if h.match == 'error_code']
    for h in hits:
        r = h.record
        steps, locked = _steps(r)
        results.append({
            'record_id': h.record_id, 'title': record_title(r), 'appliance_type': r['appliance_category'],
            'appliance_label': APPLIANCE_LABELS.get(r['appliance_category'], r['appliance_category'].replace('_', ' ')),
            'brand': r.get('appliance_brand'), 'model': r.get('appliance_model'), 'error_code': r.get('error_code'),
            'symptoms': (r.get('reported_symptoms') or [])[:4], 'possible_faults': (r.get('possible_faults') or [])[:5],
            'components': (r.get('suspected_components') or [])[:6], 'steps': steps, 'locked_steps': locked,
            'safety': (r.get('fixsaathi_safety_policy') or [])[:2], 'severity': r.get('severity'),
            'match': h.match, 'related_category': h.related, 'source_name': r['source_name'], 'source_url': r.get('source_url'),
            'license': r['source_license'], 'verification_status': r['verification_status']})
    return {'query': q, 'appliance_type': res['category'], 'appliance_detected': res['category_detected'], 'brand': res['brand'],
            'error_codes_found': res['error_codes_found'], 'error_codes_unknown': res['error_codes_unknown'], 'coverage': res['coverage'],
            'results': results}
