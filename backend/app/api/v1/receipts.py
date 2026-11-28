"""Customer Safety Receipt: minimal, expiring, Hindi-first public receipt + QR SVG with zero customer PII."""
from datetime import timedelta
import re
import secrets
import uuid
import segno
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...config import get_settings
from ...core.exceptions import NotFound, error_body
from ...db.base import utcnow
from ...db.models import CustomerReceipt, IdentifiedComponent, RepairSession, RepairStep, SafetyEvent, ServiceReport, User
from ...db.session import get_db
from ...dependencies import current_user
from ...services import safety
from ...services.access import get_owned_session
from ...services.sessions import APPLIANCE_LABELS

router = APIRouter(tags=['receipts'])

APPLIANCE_LABELS_HI = {
    'split_ac': 'स्प्लिट एसी',
    'window_ac': 'विंडो एसी',
    'ceiling_fan': 'सीलिंग फैन',
    'refrigerator': 'फ्रिज (रेफ्रिजरेटर)',
    'washing_machine': 'वॉशिंग मशीन',
    'microwave_oven': 'माइक्रोवेव ओवन',
    'water_purifier': 'वॉटर प्यूरीफायर (RO)',
    'geyser': 'गीज़र',
    'mcb_electrical': 'एमसीबी / वायरिंग',
    'rooftop_solar': 'रूफटॉप सोलर',
    'inverter': 'इन्वर्टर / यूपीएस',
    'unknown': 'घरेलू उपकरण',
}

DISCLAIMER_HI = (
    'यह विवरण टेक्नीशियन द्वारा दर्ज जानकारी पर आधारित है। FixSaathi वोल्टेज माप नहीं सकता और न ही करंट बंद होने की भौतिक पुष्टि कर सकता है। '
    'हमेशा MCB बंद करके अपने टेस्टर से जांच करें।'
)

_PHONE_RE = re.compile(r'(?:\+?\d[\d\s\-]{8,14}\d)')
_EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')


def _scrub_pii(text: str | None) -> str:
    """Strip accidental phone numbers or emails from customer issue summary so zero personal customer data is stored."""
    if not text:
        return ''
    cleaned = _EMAIL_RE.sub('[redacted]', text)
    cleaned = _PHONE_RE.sub('[redacted]', cleaned)
    return ' '.join(cleaned.split())[:280]


def _build_receipt_payload(db: Session, s: RepairSession) -> dict:
    steps = db.scalars(
        select(RepairStep).where(RepairStep.session_id == s.id, RepairStep.status == 'completed').order_by(RepairStep.step_number)
    ).all()
    comps = db.scalars(select(IdentifiedComponent).where(IdentifiedComponent.session_id == s.id)).all()
    events = db.scalars(select(SafetyEvent).where(SafetyEvent.session_id == s.id)).all()
    st = safety.current_state(db, s)
    parts = [c.result.get('component_name') for c in comps if c.result.get('found') and c.result.get('component_name')]
    np = (s.appliance_details or {}).get('nameplate') or {}
    brand_model = ' '.join(x for x in (np.get('brand'), np.get('model')) if x)
    return {
        'session_reference': s.reference,
        'appliance_type': s.appliance_type,
        'appliance_en': APPLIANCE_LABELS.get(s.appliance_type, s.appliance_type),
        'appliance_hi': APPLIANCE_LABELS_HI.get(s.appliance_type, 'घरेलू उपकरण'),
        'unit_label': brand_model or None,
        'issue': _scrub_pii(s.issue_description or s.title) or 'General inspection',
        'checks_done': [x.title for x in steps],
        'parts': list(dict.fromkeys(parts)),
        'safety_status': {
            'power_off_confirmed': st.power_off_confirmed,
            'tester_checked': st.tester_checked,
            'unlocked': st.unlocked,
            'blocked_attempts': sum(1 for e in events if e.blocked),
            'disclaimer_en': safety.DISCLAIMER,
            'disclaimer_hi': DISCLAIMER_HI,
        },
        'technician_name': s.technician.full_name if s.technician else 'Verified Technician',
        'issued_at': utcnow().isoformat(),
    }


def _load_active_receipt(db: Session, token: str) -> CustomerReceipt:
    if not re.fullmatch(r'[A-Za-z0-9_\-]{16,64}', token):
        raise NotFound('Safety receipt not found.')
    r = db.get(CustomerReceipt, token)
    if not r:
        raise NotFound('Safety receipt not found.')
    if utcnow() > r.expires_at:
        raise NotFound('This safety receipt has expired.')  # handled via 410 helper below
    return r


@router.post('/sessions/{session_id}/receipt', status_code=201)
def create_safety_receipt(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    """Issue a minimal, unguessable, expiring Customer Safety Receipt for the technician's session."""
    s = get_owned_session(db, u, session_id)
    now = utcnow()
    existing = db.scalars(
        select(CustomerReceipt).where(CustomerReceipt.session_id == s.id, CustomerReceipt.expires_at > now).order_by(CustomerReceipt.created_at.desc()).limit(1)
    ).first()
    payload = _build_receipt_payload(db, s)
    ttl_days = max(1, int(get_settings().receipt_ttl_days))
    if existing:
        existing.payload = payload
        r = existing
    else:
        rep = db.scalars(select(ServiceReport).where(ServiceReport.session_id == s.id).limit(1)).first()
        r = CustomerReceipt(
            token=secrets.token_urlsafe(24),
            session_id=s.id,
            report_id=rep.id if rep else None,
            created_by=u.id,
            payload=payload,
            created_at=now,
            expires_at=now + timedelta(days=ttl_days),
        )
        db.add(r)
    db.flush()
    return {
        'token': r.token,
        'url': f'/receipt/{r.token}',
        'qr_url': f'/api/v1/receipts/{r.token}/qr',
        'created_at': r.created_at.isoformat(),
        'expires_at': r.expires_at.isoformat(),
        'receipt': r.payload,
    }


@router.get('/receipts/{token}')
def get_public_receipt(token: str, db: Session = Depends(get_db, scope="function")):
    """Public unauthenticated endpoint returning minimal safety receipt details (zero customer PII)."""
    if not re.fullmatch(r'[A-Za-z0-9_\-]{16,64}', token):
        raise NotFound('Safety receipt not found.')
    r = db.get(CustomerReceipt, token)
    if not r:
        raise NotFound('Safety receipt not found.')
    if utcnow() > r.expires_at:
        return JSONResponse(error_body('RECEIPT_EXPIRED', 'This safety receipt has expired.'), status_code=410)
    return JSONResponse(
        {
            'token': r.token,
            'created_at': r.created_at.isoformat(),
            'expires_at': r.expires_at.isoformat(),
            'qr_url': f'/api/v1/receipts/{r.token}/qr',
            'receipt': r.payload,
        },
        headers={'Cache-Control': 'private, no-store', 'X-Robots-Tag': 'noindex'},
    )


@router.get('/receipts/{token}/qr')
def get_receipt_qr(token: str, request: Request, db: Session = Depends(get_db, scope="function")):
    """Public SVG QR code pointing to the public /receipt/<token> page."""
    if not re.fullmatch(r'[A-Za-z0-9_\-]{16,64}', token):
        raise NotFound('Safety receipt not found.')
    r = db.get(CustomerReceipt, token)
    if not r:
        raise NotFound('Safety receipt not found.')
    if utcnow() > r.expires_at:
        return JSONResponse(error_body('RECEIPT_EXPIRED', 'This safety receipt has expired.'), status_code=410)
    base = str(request.base_url).rstrip('/')
    target = f'{base}/receipt/{r.token}'
    svg = segno.make(target, error='m').svg_inline(scale=5, border=2, dark='#0f172a', light='#ffffff')
    return Response(content=svg, media_type='image/svg+xml', headers={'Cache-Control': 'public, max-age=300', 'X-Robots-Tag': 'noindex'})
