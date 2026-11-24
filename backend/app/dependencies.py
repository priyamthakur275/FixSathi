import uuid
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .core.exceptions import Unauthorized
from .core.security import decode_access_token
from .db.models import User
from .db.session import get_db

bearer = HTTPBearer(auto_error=False)


def user_from_token(db: Session, token: str) -> User:
    claims = decode_access_token(token)
    try:
        uid = uuid.UUID(claims['sub'])
    except (KeyError, ValueError):
        raise Unauthorized('Invalid access token', code='TOKEN_INVALID')
    u = db.get(User, uid)
    if not u or not u.is_active:
        raise Unauthorized('Account not found or inactive', code='TOKEN_INVALID')
    return u


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db, scope="function")) -> User:
    if not creds or creds.scheme.lower() != 'bearer':
        raise Unauthorized('Sign in required')
    return user_from_token(db, creds.credentials)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else 'unknown'
