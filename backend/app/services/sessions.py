import re, secrets, uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..core.exceptions import Conflict
from ..db.base import utcnow
from ..db.models import Conversation, RepairSession, User

TRANSITIONS: dict[str, set[str]] = {
    'created': {'active', 'cancelled'},
    'active': {'diagnosing', 'awaiting_confirmation', 'guidance_in_progress', 'escalated', 'completed', 'cancelled'},
    'diagnosing': {'active', 'awaiting_confirmation', 'guidance_in_progress', 'escalated', 'completed', 'cancelled'},
    'awaiting_confirmation': {'active', 'guidance_in_progress', 'escalated', 'completed', 'cancelled'},
    'guidance_in_progress': {'active', 'awaiting_confirmation', 'escalated', 'completed', 'cancelled'},
    'escalated': {'active', 'guidance_in_progress', 'completed', 'cancelled'},
    'completed': set(), 'cancelled': set(),
}
TERMINAL = {'completed', 'cancelled'}
APPLIANCE_LABELS = {'ceiling_fan': 'Ceiling fan', 'split_ac': 'Split AC', 'washing_machine': 'Washing machine', 'refrigerator': 'Refrigerator',
                    'mcb_electrical': 'MCB / electrical', 'rooftop_solar': 'Rooftop solar', 'microwave_oven': 'Microwave oven',
                    'water_purifier': 'Water purifier', 'unknown': 'Not specified'}
def guess_appliance(text: str) -> str:
    from ..datasets.normalize import detect_appliance
    return detect_appliance(text)


def transition(s: RepairSession, new: str) -> None:
    if new == s.status:
        return
    if new not in TRANSITIONS.get(s.status, set()):
        raise Conflict(f'Cannot move a session from {s.status} to {new}.', code='INVALID_TRANSITION')
    s.status = new
    if new in TERMINAL:
        s.completed_at = utcnow()


def ensure_open(s: RepairSession) -> None:
    if s.status in TERMINAL:
        raise Conflict('This session is closed.', code='SESSION_CLOSED')


def _title_from(issue: str, limit: int = 60) -> str:
    """First sentence of the issue, cut at a word boundary, so titles never end mid-word."""
    t = ' '.join(issue.split())
    if not t:
        return ''
    for sep in ('. ', '? ', '! '):
        if sep in t[:limit + 20]:
            t = t.split(sep, 1)[0]; break
    t = t.rstrip('.?!')
    if len(t) > limit:
        t = t[:limit].rsplit(' ', 1)[0].rstrip(',;:') + '...'
    return t


_FILLER = {'hi', 'hello', 'hey', 'namaste', 'please', 'pls', 'kindly', 'help', 'me', 'can', 'could', 'you', 'i', 'have', 'has', 'got', 'need', 'there',
           'my', 'our', 'the', 'a', 'an', 'this', 'that', 'is', 'are', 'was', 'were', 'it', 'its', "it's", 'but', 'and', 'so', 'very', 'really', 'just',
           'customer', "customer's", 'with', 'of', 'to', 'some', 'problem', 'issue', 'facing', 'getting', 'seems', 'still',
           'at', 'all', 'since', 'today', 'yesterday', 'now', 'properly', 'suddenly', 'again', 'also'}
_NEGATIONS = re.compile(r"\b(?:isn'?t|is not|doesn'?t|does not|don'?t|do not|won'?t|will not|wont|can'?t|cannot|not)\b", re.I)


def chat_title(issue: str, appliance_type: str) -> str:
    """A short, readable conversation title from the first message, e.g. 'Ceiling Fan Not Rotating' or 'LG Split AC Showing CH38'."""
    first = _title_from(issue, limit=200)
    words = [w for w in re.split(r'[\s,;:()"]+', _NEGATIONS.sub(' not ', first).rstrip('.')) if w]
    keep: list[str] = []
    for w in words:
        if w.lower() in _FILLER or (w.lower() == 'not' and keep and keep[-1] == 'Not'):
            continue
        keep.append('Not' if w.lower() == 'not' else w if any(c.isupper() for c in w[1:]) or any(c.isdigit() for c in w) or w.isupper() else w.capitalize())
        if len(keep) == 6:
            break
    while keep and keep[-1] in ('Not', 'In', 'On', 'At', 'For', 'From', 'Or'):
        keep.pop()
    if len(keep) < 2:
        return generic_title(appliance_type)
    return ' '.join(keep)[:80]


def generic_title(appliance_type: str) -> str:
    """The name a chat gets before anyone has described a fault ('hi', a photo alone)."""
    return 'New chat' if appliance_type in (None, '', 'unknown') else f'{APPLIANCE_LABELS.get(appliance_type, appliance_type)} repair'


def retitle_from(s: RepairSession, text: str) -> bool:
    """A chat opened with small talk ('hey') keeps a placeholder name. The first message that describes a fault names it,
    becomes its issue description, and sets the appliance if none was known. Titles the technician typed are never changed."""
    if not (s.appliance_details or {}).get('title_auto') or s.title != generic_title(s.appliance_type) or not text.strip():
        return False
    app = s.appliance_type if s.appliance_type not in (None, '', 'unknown') else guess_appliance(text)
    title = chat_title(text, app)
    if title == generic_title(app):
        return False
    s.title, s.issue_description = title, text.strip()[:2000]
    if s.appliance_type in (None, '', 'unknown') and app != 'unknown':
        s.appliance_type = app
    return True


def create_session(db: Session, user: User, appliance_type: str | None, issue: str, title: str | None) -> RepairSession:
    app = appliance_type or guess_appliance(issue)
    ref = None
    for _ in range(5):
        cand = 'FS-' + secrets.token_hex(3).upper()
        if not db.scalar(select(func.count()).select_from(RepairSession).where(RepairSession.reference == cand)):
            ref = cand; break
    s = RepairSession(id=uuid.uuid4(), reference=ref or 'FS-' + uuid.uuid4().hex[:8].upper(), technician_id=user.id, organisation_id=user.organisation_id,
                      appliance_type=app, issue_description=issue.strip(), status='active',
                      appliance_details={} if title else {'title_auto': True}, title=(title or chat_title(issue, app)))
    db.add(s); db.flush()
    return s


def add_message(db: Session, s: RepairSession, role: str, text: str, mtype: str = 'text', meta: dict | None = None) -> Conversation:
    m = Conversation(session_id=s.id, role=role, message=text, message_type=mtype, meta=meta or {})
    db.add(m); db.flush()
    return m
