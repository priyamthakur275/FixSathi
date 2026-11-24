import hashlib, secrets, time, uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from ..config import get_settings
from .exceptions import RateLimited, Unauthorized

_ph = PasswordHasher()
ALGO = 'HS256'


def hash_password(p: str) -> str: return _ph.hash(p)


def verify_password(p: str, h: str) -> bool:
    try:
        return _ph.verify(h, p)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: uuid.UUID, role: str, minutes: int | None = None) -> str:
    s = get_settings(); now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=minutes if minutes is not None else s.access_token_expire_minutes)
    return jwt.encode({'sub': str(user_id), 'role': role, 'type': 'access', 'iat': now, 'exp': exp, 'jti': uuid.uuid4().hex}, s.secret_key, algorithm=ALGO)


def decode_access_token(token: str) -> dict:
    try:
        d = jwt.decode(token, get_settings().secret_key, algorithms=[ALGO])
    except jwt.ExpiredSignatureError:
        raise Unauthorized('Access token expired', code='TOKEN_EXPIRED')
    except jwt.PyJWTError:
        raise Unauthorized('Invalid access token', code='TOKEN_INVALID')
    if d.get('type') != 'access':
        raise Unauthorized('Invalid access token', code='TOKEN_INVALID')
    return d


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh(raw)


def hash_refresh(raw: str) -> str: return hashlib.sha256(raw.encode()).hexdigest()


class RateLimiter:
    """Per-process sliding window. On Cloud Run with several instances the limit applies per instance."""
    def __init__(self): self.hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, limit: int, window: float = 60.0) -> None:
        now = time.monotonic(); q = self.hits[key]
        while q and now - q[0] > window: q.popleft()
        if len(q) >= limit:
            raise RateLimited('Too many attempts. Please wait a minute and try again.')
        q.append(now)


auth_limiter = RateLimiter()
