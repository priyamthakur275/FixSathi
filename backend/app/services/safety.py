"""Server-enforced safety gate. The ONLY place that decides whether a power-sensitive action may proceed.

Statements are technician-entered. FixSaathi cannot physically verify isolation; the API and UI say so.
Rules:
- Both power_off_confirmed and tester_checked must be recorded, by the session's own technician, for THIS session.
- Statements expire after SAFETY_CONFIRMATION_TTL_MINUTES so a stale confirmation cannot unlock later work.
- Every blocked attempt and every change is recorded in safety_events.
- AI tools, REST step completion and the live relay all call `guard`.
- Free-text AI output (chat replies, spoken live replies) goes through `screen_text`: power-sensitive instructions are
  withheld while the gate is locked, and microwave internal work is always replaced by a hand-over to authorised service.
"""
import logging, re
from dataclasses import dataclass, field
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..core.exceptions import Forbidden
from ..core.logging import log
from ..core.power_rules import FAULT_LEAD, IMPERATIVE, MICROWAVE_ESCALATION, instructs_power_work, mentions_microwave_internals, step_text_needs_power_off
from ..db.base import utcnow
from ..db.models import RepairSession, SafetyConfirmation, SafetyEvent, User
from .sessions import ensure_open

logger = logging.getLogger('safety')
DISCLAIMER = ('These are statements entered by the technician. FixSaathi cannot measure voltage or verify that a circuit is isolated. '
              'Always switch off at the MCB or isolator and verify with your own tester.')


@dataclass
class SafetyState:
    power_off_confirmed: bool = False
    tester_checked: bool = False
    confirmed_at: str | None = None
    expires_at: str | None = None
    expired: bool = False

    @property
    def missing(self) -> list[str]:
        return [k for k, v in (('power_off_confirmed', self.power_off_confirmed), ('tester_checked', self.tester_checked)) if not v]

    @property
    def unlocked(self) -> bool:
        return not self.missing


@dataclass
class Decision:
    allowed: bool
    reason: str | None = None
    missing: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {'allowed': self.allowed, 'reason': self.reason, 'missing': self.missing, 'disclaimer': DISCLAIMER}


def current_state(db: Session, s: RepairSession) -> SafetyState:
    row = db.scalars(select(SafetyConfirmation).where(SafetyConfirmation.session_id == s.id, SafetyConfirmation.technician_id == s.technician_id)
                     .order_by(SafetyConfirmation.confirmed_at.desc()).limit(1)).first()
    if not row:
        return SafetyState()
    ttl = timedelta(minutes=get_settings().safety_confirmation_ttl_minutes)
    exp = row.confirmed_at + ttl
    if utcnow() > exp:
        return SafetyState(confirmed_at=row.confirmed_at.isoformat(), expires_at=exp.isoformat(), expired=True)
    return SafetyState(row.power_off_confirmed, row.tester_checked, row.confirmed_at.isoformat(), exp.isoformat())


def confirm(db: Session, s: RepairSession, user: User, power_off: bool, tester: bool, source: str = 'ui') -> SafetyState:
    if s.technician_id != user.id:
        raise Forbidden('Only the technician working on this session can record safety statements.')
    ensure_open(s)
    db.add(SafetyConfirmation(session_id=s.id, technician_id=user.id, power_off_confirmed=power_off, tester_checked=tester, confirmation_source=source))
    db.add(SafetyEvent(session_id=s.id, technician_id=user.id, event_type='confirmation_changed', actor=source, blocked=False,
                       details={'power_off_confirmed': power_off, 'tester_checked': tester}))
    db.flush()
    log(logger, 'safety_confirmation', session=str(s.id), power_off=power_off, tester=tester)
    return current_state(db, s)


def guard(db: Session, s: RepairSession, user: User | None, action: str, requires_power_off: bool, actor: str = 'api') -> Decision:
    if not requires_power_off:
        return Decision(True)
    if user is not None and user.id != s.technician_id:
        d = Decision(False, 'NOT_SESSION_TECHNICIAN', ['power_off_confirmed', 'tester_checked'])
    else:
        st = current_state(db, s)
        d = Decision(True) if st.unlocked else Decision(False, 'SAFETY_CONFIRMATION_EXPIRED' if st.expired else 'SAFETY_CONFIRMATION_REQUIRED', st.missing)
    db.add(SafetyEvent(session_id=s.id, technician_id=user.id if user else None, event_type='action_allowed' if d.allowed else 'action_blocked',
                       attempted_action=action[:120], actor=actor, blocked=not d.allowed, reason=d.reason, details={'missing': d.missing}))
    db.flush()
    if not d.allowed:
        log(logger, 'safety_block', logging.WARNING, session=str(s.id), action=action, actor=actor, reason=d.reason)
    return d


def record_block(db: Session, s: RepairSession, user: User | None, action: str, reason: str, actor: str) -> None:
    """Log a refusal that is not about the power-off statements (e.g. microwave internals are never allowed)."""
    db.add(SafetyEvent(session_id=s.id, technician_id=user.id if user else None, event_type='action_blocked', attempted_action=action[:120],
                       actor=actor, blocked=True, reason=reason, details={}))
    db.flush()
    log(logger, 'safety_block', logging.WARNING, session=str(s.id), action=action, actor=actor, reason=reason)


LOCK_NOTE = ('**Power-sensitive step withheld.** Switch off at the MCB (or unplug) and verify with your own tester, then tick both '
             'statements in the safety panel of the repair workspace. Ask again after that and the full step will be shown.')
LOCK_NOTE_VOICE = ('I have held back a power-sensitive step. Switch off at the MCB, check with your own tester, and tick both '
                   'statements in the safety panel, then ask me again.')
WITHHELD_MARK = '*(power-sensitive step withheld: see the note below)*'
_SENTENCE = re.compile(r'(?<=[.!?।])\s+')
_BULLET = re.compile(r'^(\s*(?:[-*•]|\d+[.)])\s+)?(.*)$')
_CLAUSE = re.compile(r'(?<=[—–;])\s+|(?<=\s-)\s+')  # inside a cause item: "Weak capacitor — measure it" is two clauses
# A heading that introduces suspected causes. List items under it name faults; they are screened as text, not as steps.
_CAUSE_HEAD = re.compile(r'\b(causes?|reasons?|culprits?|suspects?|suspected|diagnos\w*|faults?|symptoms?|kaaran|karan|wajah|vajah)\b', re.I)


def _heading(line: str) -> str | None:
    """The text of a heading-like line ('## Likely causes', '**Likely causes:**', 'Here are the likely causes:'), else None."""
    t = line.strip()
    if not t or _BULLET.match(t).group(1):
        return None
    if t.startswith('#'):
        return t.lstrip('#').strip()
    m = re.match(r'^\*\*([^*]+?)\*\*:?', t)
    if m and (m.group(1).rstrip().endswith(':') or t[m.end() - 1:m.end()] == ':' or m.end() == len(t)):
        return m.group(1)
    return t if t.rstrip('*').endswith(':') else None


@dataclass
class Screened:
    text: str
    withheld: int = 0
    microwave_escalated: int = 0
    reason: str | None = None


def screen_text(db: Session, s: RepairSession, user: User | None, text: str, actor: str, appliance: str | None = None, voice: bool = False) -> Screened:
    """Server-side check of free-text AI output before anyone sees or hears it. Works sentence by sentence, so the diagnosis
    around a withheld step stays readable. Uses `guard`, so every withheld or allowed instruction is in safety_events."""
    from ..datasets.normalize import detect_appliance
    microwave = (appliance or s.appliance_type) == 'microwave_oven' or detect_appliance(text) == 'microwave_oven'
    lines = (text or '').split('\n')
    plan = []  # (line_index, prefix, [(sentence, kind)])
    in_causes = False
    for i, line in enumerate(lines):
        head = _heading(line)
        if head is not None:
            in_causes = bool(_CAUSE_HEAD.search(head))
        prefix, body = _BULLET.match(line).groups()
        # A list item is a step (step rule) unless it names a suspected fault: under a causes heading, or opening with a fault
        # word ("Faulty relay", "Weak capacitor"). Causes and prose get the instruction rule, so naming a part stays readable and
        # only an instruction to work on it is withheld.
        cause = bool(prefix) and (in_causes or bool(FAULT_LEAD.match(re.sub(r'^\W*\*\*', '', body))))
        # Indented sub-items are what to do about the cause above them: never lenient.
        cause = cause and not prefix.startswith((' ', '\t'))
        parts = [c for p in _SENTENCE.split(body) if p for c in (_CLAUSE.split(p) if cause else [p]) if c]
        is_step = bool(prefix) and not cause

        def power(p: str) -> bool:
            # Inside a cause, a clause that is an instruction ("Unplug the PTC and shake it") still gets the step rule.
            if is_step or (cause and IMPERATIVE.match(re.sub(r'^\W*\*\*[^*]*\*\*:?', '', p))):
                return step_text_needs_power_off(p)
            return instructs_power_work(p)
        kinds = [(p, 'microwave' if microwave and mentions_microwave_internals(p) else 'power' if power(p) else 'ok') for p in parts]
        if is_step and any(k == 'power' for _, k in kinds):  # a step is withheld whole, never half-shown
            kinds = [(p, 'power' if k == 'ok' else k) for p, k in kinds]
        plan.append((i, prefix or '', kinds))
    needs = any(k == 'power' for _, _, ps in plan for _, k in ps)
    has_mw = any(k == 'microwave' for _, _, ps in plan for _, k in ps)
    if has_mw:
        record_block(db, s, user, f'{actor}_reply:microwave_internal', 'MICROWAVE_INTERNAL', actor)
    allowed = guard(db, s, user, f'{actor}_reply', True, actor=actor) if needs else Decision(True)
    if not has_mw and allowed.allowed:
        return Screened(text)
    out, withheld, mw_done = [], 0, False
    for i, prefix, parts in plan:
        kept = []
        for p, k in parts:
            if k == 'microwave':
                if not mw_done:
                    kept.append(MICROWAVE_ESCALATION); mw_done = True
            elif k == 'power' and not allowed.allowed:
                withheld += 1
                if not voice and (not kept or kept[-1] != WITHHELD_MARK):
                    kept.append(WITHHELD_MARK)
            else:
                kept.append(p)
        if kept or not parts:
            out.append(prefix + ' '.join(kept) if kept else lines[i])
    # Consecutive fully withheld steps read as one marker, not a column of them.
    collapsed: list[str] = []
    for line in out:
        if line.strip().endswith(WITHHELD_MARK) and _BULLET.match(line).group(2).strip() == WITHHELD_MARK:
            line = WITHHELD_MARK
            if collapsed and collapsed[-1] == WITHHELD_MARK:
                continue
        collapsed.append(line)
    body = '\n'.join(collapsed).strip()
    if withheld:
        body = f'{body} {LOCK_NOTE_VOICE}'.strip() if voice else f'{body}\n\n{LOCK_NOTE}'.strip()
    return Screened(body, withheld, int(mw_done), None if allowed.allowed else allowed.reason)
