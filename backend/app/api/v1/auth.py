from datetime import timedelta
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ...config import get_settings
from ...core.exceptions import Conflict, Unauthorized
from ...core.security import auth_limiter, create_access_token, hash_password, hash_refresh, new_refresh_token, verify_password
from ...db.base import utcnow
from ...db.models import Organisation, RefreshToken, User
from ...db.session import get_db
from ...dependencies import client_ip, current_user
from ...schemas.auth import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut, UserPatch

_DUMMY_HASH = hash_password('not-a-real-password-used-for-timing-only')
router = APIRouter(tags=['auth'])
users = APIRouter(prefix='/users', tags=['users'])


def user_out(db: Session, u: User) -> UserOut:
    org = db.get(Organisation, u.organisation_id) if u.organisation_id else None
    return UserOut.model_validate(u).model_copy(update={'organisation_name': org.name if org else None})


def issue_tokens(db: Session, u: User) -> TokenOut:
    s = get_settings(); raw, h = new_refresh_token()
    db.add(RefreshToken(user_id=u.id, token_hash=h, expires_at=utcnow() + timedelta(days=s.refresh_token_expire_days)))
    db.flush()
    return TokenOut(access_token=create_access_token(u.id, u.role), refresh_token=raw, expires_in=s.access_token_expire_minutes * 60, user=user_out(db, u))


@router.post('/auth/register', response_model=TokenOut, status_code=201)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db, scope="function")):
    auth_limiter.check(f'register:{client_ip(request)}', get_settings().auth_rate_limit_per_minute)
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise Conflict('An account with this email already exists.', code='EMAIL_TAKEN')
    org = None
    if body.organisation_name:
        org = db.scalar(select(Organisation).where(Organisation.name == body.organisation_name.strip()))
        if not org:
            org = Organisation(name=body.organisation_name.strip()); db.add(org); db.flush()
    # Self-registration always creates a technician. Managers/admins are promoted with scripts/create_user.py.
    u = User(full_name=body.full_name.strip(), email=email, password_hash=hash_password(body.password), role='technician',
             preferred_language=body.preferred_language, organisation_id=org.id if org else None)
    db.add(u)
    try:
        db.flush()
    except IntegrityError:  # the same email registered at the same moment by another request
        db.rollback(); raise Conflict('An account with this email already exists.', code='EMAIL_TAKEN')
    return issue_tokens(db, u)


@router.post('/auth/login', response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db, scope="function")):
    auth_limiter.check(f'login:{client_ip(request)}', get_settings().auth_rate_limit_per_minute)
    u = db.scalar(select(User).where(User.email == body.email.lower()))
    # Hash even when the email is unknown, so response time does not reveal which emails have accounts.
    ok = verify_password(body.password, u.password_hash if u else _DUMMY_HASH)
    if not u or not u.is_active or not ok:
        raise Unauthorized('Incorrect email or password.', code='INVALID_CREDENTIALS')
    return issue_tokens(db, u)


@router.post('/auth/refresh', response_model=TokenOut)
def refresh(body: RefreshIn, request: Request, db: Session = Depends(get_db, scope="function")):
    auth_limiter.check(f'refresh:{client_ip(request)}', get_settings().auth_rate_limit_per_minute * 6)
    t = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh(body.refresh_token)).with_for_update())
    if t and t.revoked_at and t.revoked_at < utcnow() - timedelta(seconds=30):
        # A rotated token used again long after rotation means it may have been copied: sign that account out everywhere.
        # (Within 30 s it is usually two browser tabs refreshing together, so it only fails, without the sign-out.)
        for other in db.scalars(select(RefreshToken).where(RefreshToken.user_id == t.user_id, RefreshToken.revoked_at.is_(None))):
            other.revoked_at = utcnow()
        db.commit()
        raise Unauthorized('This sign-in was already used. Please sign in again.', code='REFRESH_REUSED')
    if not t or t.revoked_at or t.expires_at < utcnow():
        raise Unauthorized('Refresh token is invalid or expired.', code='REFRESH_INVALID')
    t.revoked_at = utcnow()  # rotation: each refresh token works once
    u = db.get(User, t.user_id)
    if not u or not u.is_active:
        raise Unauthorized('Account inactive.', code='REFRESH_INVALID')
    return issue_tokens(db, u)


@router.post('/auth/logout', status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db, scope="function")):
    t = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh(body.refresh_token)))
    if t and not t.revoked_at:
        t.revoked_at = utcnow()


@router.get('/auth/me', response_model=UserOut)
def me(u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return user_out(db, u)


@users.get('/me', response_model=UserOut)
def users_me(u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return user_out(db, u)


@users.patch('/me', response_model=UserOut)
def patch_me(body: UserPatch, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(u, k, v)
    db.flush()
    return user_out(db, u)
