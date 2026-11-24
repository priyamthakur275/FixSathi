from datetime import timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..db.base import utcnow
from ..db.models import AIUsage, Conversation, EscalationRequest, Feedback, RepairSession, User
from .access import session_scope

TERMINAL = ('completed', 'cancelled')


def _ids(db: Session, user: User):
    return session_scope(user).with_only_columns(RepairSession.id).scalar_subquery()


def overview(db: Session, user: User) -> dict:
    sub = _ids(db, user)
    base = select(RepairSession).where(RepairSession.id.in_(sub)).subquery()
    total, completed, active, escalated = db.execute(select(
        func.count(), func.count().filter(base.c.status == 'completed'), func.count().filter(base.c.status.not_in(TERMINAL + ('escalated',))),
        func.count().filter(base.c.status == 'escalated'))).one()
    ftf_known, ftf_yes = db.execute(select(func.count().filter(base.c.first_time_fix.is_not(None)), func.count().filter(base.c.first_time_fix.is_(True)))
                                    .where(base.c.status == 'completed')).one()
    dur = db.scalar(select(func.avg(func.extract('epoch', base.c.completed_at - base.c.started_at))).where(base.c.status == 'completed'))
    rating, rated, correct_known, correct_yes = db.execute(select(func.avg(Feedback.rating), func.count(), func.count(Feedback.guidance_correct),
                                                                  func.count().filter(Feedback.guidance_correct.is_(True))).where(Feedback.session_id.in_(sub))).one()
    helpful_flag = Conversation.meta['feedback']['helpful'].as_boolean()
    up, down = db.execute(select(func.count().filter(helpful_flag.is_(True)), func.count().filter(helpful_flag.is_(False)))
                          .where(Conversation.session_id.in_(sub), Conversation.role == 'assistant')).one()
    lat = db.scalar(select(func.avg(AIUsage.latency_ms)).where(AIUsage.session_id.in_(sub), AIUsage.ok.is_(True)))
    open_esc = db.scalar(select(func.count()).select_from(EscalationRequest).where(EscalationRequest.session_id.in_(sub), EscalationRequest.status == 'open'))
    return {
        'total_sessions': total, 'completed': completed, 'active': active, 'escalated': escalated, 'open_escalations': open_esc,
        'first_time_fix_rate': round(ftf_yes / ftf_known, 3) if ftf_known else None,
        'first_time_fix_sample': ftf_known,
        'avg_repair_minutes': round(float(dur) / 60, 1) if dur else None,
        'avg_rating': round(float(rating), 2) if rating else None, 'ratings_count': rated,
        'guidance_correct_rate': round(correct_yes / correct_known, 3) if correct_known else None,
        'answers_rated': up + down, 'answers_helpful': up,
        'answer_helpful_rate': round(up / (up + down), 3) if up + down else None,
        'avg_ai_latency_ms': int(lat) if lat else None,
        'ai_cost_per_repair': None, 'ai_cost_note': 'Not calculated: no verified pricing table is configured.',
    }


def trend(db: Session, user: User, days: int = 7) -> list[dict]:
    sub = _ids(db, user); start = (utcnow() - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day = func.date_trunc('day', RepairSession.created_at)
    rows = db.execute(select(day, func.count(), func.count().filter(RepairSession.status == 'completed'))
                      .where(RepairSession.id.in_(sub), RepairSession.created_at >= start).group_by(day)).all()
    by = {r[0].date(): (r[1], r[2]) for r in rows}
    out = []
    for i in range(days):
        d = (start + timedelta(days=i)).date(); n, c = by.get(d, (0, 0))
        out.append({'day': d.strftime('%a'), 'date': d.isoformat(), 'sessions': n, 'completed': c})
    return out


def technicians(db: Session, user: User) -> list[dict]:
    sub = _ids(db, user)
    rows = db.execute(select(User.full_name, func.count(RepairSession.id), func.count().filter(RepairSession.status == 'escalated'),
                             func.count().filter(RepairSession.status == 'completed'))
                      .join(RepairSession, RepairSession.technician_id == User.id).where(RepairSession.id.in_(sub)).group_by(User.id, User.full_name)
                      .order_by(func.count(RepairSession.id).desc()).limit(20)).all()
    return [{'name': r[0], 'sessions': r[1], 'escalated': r[2], 'completed': r[3]} for r in rows]


def ratings(db: Session, user: User) -> list[dict]:
    sub = _ids(db, user)
    rows = dict(db.execute(select(Feedback.rating, func.count()).where(Feedback.session_id.in_(sub)).group_by(Feedback.rating)).all())
    return [{'stars': str(i), 'count': rows.get(i, 0)} for i in (5, 4, 3, 2, 1)]
