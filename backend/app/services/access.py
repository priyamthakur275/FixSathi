"""Authorization policy. Ownership is always derived from the verified token, never from request bodies."""
import uuid
from sqlalchemy import Select, select
from sqlalchemy.orm import Session
from ..core.exceptions import Forbidden, NotFound
from ..db.models import RepairSession, User


def session_scope(user: User) -> Select:
    q = select(RepairSession)
    if user.role == 'admin':
        return q
    if user.role == 'manager':
        if user.organisation_id is None:
            return q.where(RepairSession.id.is_(None))  # a manager without an organisation sees nothing
        return q.where(RepairSession.organisation_id == user.organisation_id)
    return q.where(RepairSession.technician_id == user.id)


def get_readable_session(db: Session, user: User, session_id: uuid.UUID, *, lock: bool = False) -> RepairSession:
    q = session_scope(user).where(RepairSession.id == session_id)
    if lock:
        q = q.with_for_update(of=RepairSession)
    s = db.scalars(q).unique().first()
    if not s:
        raise NotFound('Repair session not found.')  # 404 for both missing and not-permitted: do not reveal existence
    return s


def get_owned_session(db: Session, user: User, session_id: uuid.UUID, *, lock: bool = False) -> RepairSession:
    s = get_readable_session(db, user, session_id, lock=lock)
    if s.technician_id != user.id:
        raise Forbidden('Only the technician who owns this session can do this.')
    return s


def require_role(user: User, *roles: str) -> None:
    if user.role not in roles:
        raise Forbidden('Your role does not allow this action.')
