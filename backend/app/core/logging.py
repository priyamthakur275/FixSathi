import json, logging, re, sys, time, uuid
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar('request_id', default='-')
SENSITIVE = ('password', 'token', 'secret', 'api_key', 'authorization', 'image_bytes', 'raw_bytes', 'inline_data', 'base64')
API_KEY_RE = re.compile(r'AIza[0-9A-Za-z_-]{20,}|AQ\.[0-9A-Za-z_.-]{20,}')


def _scrub(v):
    if isinstance(v, str):
        return API_KEY_RE.sub('[redacted-key]', v)
    return v


class JsonFormatter(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        d = {'ts': round(r.created, 3), 'level': r.levelname, 'logger': r.name, 'msg': _scrub(r.getMessage()), 'request_id': request_id.get()}
        for k, v in getattr(r, 'extra_fields', {}).items():
            d[k] = '[redacted]' if any(s in k.lower() for s in SENSITIVE) else _scrub(v)
        if r.exc_info:
            d['exc'] = _scrub(self.formatException(r.exc_info))
        return json.dumps(d, default=str)


def setup_logging(debug: bool = False) -> None:
    h = logging.StreamHandler(sys.stdout); h.setFormatter(JsonFormatter())
    root = logging.getLogger(); root.handlers = [h]; root.setLevel(logging.DEBUG if debug else logging.INFO)


def log(logger: logging.Logger, msg: str, level: int = logging.INFO, **fields) -> None:
    logger.log(level, msg, extra={'extra_fields': fields})


class RequestIdMiddleware:
    """Pure ASGI middleware so SSE StreamingResponse chunks are never buffered."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        headers = {k.lower(): v for k, v in scope.get('headers', [])}
        raw_rid = headers.get(b'x-request-id')
        rid = raw_rid.decode('latin-1') if raw_rid else uuid.uuid4().hex[:16]
        token = request_id.set(rid)
        t0 = time.perf_counter()
        status = 500

        async def send_wrapper(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
                hdrs = list(message.get('headers', []))
                hdrs.append((b'x-request-id', rid.encode('latin-1')))
                message = {**message, 'headers': hdrs}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            request_id.reset(token)
            log(logging.getLogger('http'), 'request', method=scope.get('method', ''), path=scope.get('path', ''), status=status, ms=round((time.perf_counter() - t0) * 1000, 1))
