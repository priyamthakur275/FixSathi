"""Per-user limits on calls that spend the Gemini (or ElevenLabs) key.

Anyone can register on the public app, so without a limit one account (or a script) could use up the whole key's quota
for every other technician. Two sliding windows per user: a short one against bursts and loops, a daily one against
slow, steady abuse. Scripted demo sessions call no model and are not counted.

Like the sign-in limiter, the windows live in the API process. With several instances each enforces its own limit.
"""
from ..config import get_settings
from .exceptions import AppError
from .security import RateLimiter

ai_minute = RateLimiter()
ai_day = RateLimiter()
DAY = 86_400.0


class AIQuotaExceeded(AppError):
    status, code = 429, 'AI_RATE_LIMITED'


def check_ai_quota(user_id, cost: int = 1) -> None:
    """Count `cost` AI calls for this user, or raise AIQuotaExceeded without counting anything."""
    st = get_settings()
    key = str(user_id)
    for limiter, limit, window, msg, hint in (
        (ai_minute, st.ai_requests_per_minute, 60.0, 'Too many AI requests in a minute.', 'Wait a minute, then send your message again.'),
        (ai_day, st.ai_requests_per_day, DAY, 'Daily AI limit reached for this account.',
         'The limit resets within 24 hours. Your messages and the safety panel still work; ask your manager if you need more.'),
    ):
        if limit <= 0:
            continue
        if limiter.count(key, window) + cost > limit:
            raise AIQuotaExceeded(msg, details={'hint': hint, 'limit': limit, 'window_seconds': int(window)})
    ai_minute.add(key, cost); ai_day.add(key, cost)


def reset() -> None:
    ai_minute.hits.clear(); ai_day.hits.clear()
