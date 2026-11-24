import json, logging, sys, time, uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware

request_id: ContextVar[str] = ContextVar('request_id', default='-')
SENSITIVE = ('password', 'token', 'secret', 'api_key', 'authorization')


class JsonFormatter(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        d = {'ts': round(r.created, 3), 'level': r.levelname, 'logger': r.name, 'msg': r.getMessage(), 'request_id': request_id.get()}
        for k, v in getattr(r, 'extra_fields', {}).items():
            d[k] = '[redacted]' if any(s in k.lower() for s in SENSITIVE) else v
        if r.exc_info:
            d['exc'] = self.formatException(r.exc_info)
        return json.dumps(d, default=str)


def setup_logging(debug: bool = False) -> None:
    h = logging.StreamHandler(sys.stdout); h.setFormatter(JsonFormatter())
    root = logging.getLogger(); root.handlers = [h]; root.setLevel(logging.DEBUG if debug else logging.INFO)


def log(logger: logging.Logger, msg: str, level: int = logging.INFO, **fields) -> None:
    logger.log(level, msg, extra={'extra_fields': fields})


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get('x-request-id') or uuid.uuid4().hex[:16]
        token = request_id.set(rid); t0 = time.perf_counter()
        try:
            resp = await call_next(request)
        finally:
            request_id.reset(token)
        resp.headers['x-request-id'] = rid
        log(logging.getLogger('http'), 'request', method=request.method, path=request.url.path, status=resp.status_code, ms=round((time.perf_counter() - t0) * 1000, 1))
        return resp
