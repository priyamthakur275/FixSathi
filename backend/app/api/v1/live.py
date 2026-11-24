import asyncio, json, logging, uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...config import get_settings
from ...core.exceptions import AppError
from ...core.logging import log
from ...db.session import SessionLocal
from ...dependencies import user_from_token
from ...services import live
from ...integrations.gemini.errors import classify
from ...services.access import get_owned_session

router = APIRouter(tags=['live'])
logger = logging.getLogger('live')


@router.websocket('/live/{session_id}')
async def live_ws(ws: WebSocket, session_id: uuid.UUID):
    """Protocol: see docs/LIVE_PROTOCOL.md. First message must be {"type":"auth","token":...}; the token is never put in the URL."""
    origin = ws.headers.get('origin')
    host = ws.headers.get('host', '')
    same_origin = bool(origin) and origin.split('://', 1)[-1] == host
    if origin and not same_origin and origin not in get_settings().cors_list:
        await ws.close(code=4403, reason='origin not allowed'); return
    await ws.accept()

    async def emit(m: dict):
        await ws.send_text(json.dumps(m))

    try:
        first = json.loads(await asyncio.wait_for(ws.receive_text(), timeout=10))
        if first.get('type') != 'auth' or not isinstance(first.get('token'), str):
            raise AppError('First message must be auth.', code='AUTH_REQUIRED', status=401)
        db = SessionLocal()
        try:
            u = user_from_token(db, first['token'])
            s = get_owned_session(db, u, session_id)
            if s.status in ('completed', 'cancelled'):
                raise AppError('This session is closed.', code='SESSION_CLOSED', status=409)
            ctx = live.LiveContext(session_id=s.id, user_id=u.id, language=str(first.get('language') or u.preferred_language)[:20])
        finally:
            db.close()
        get_settings_ok = live.get_gemini().model('live')  # raises AIUnavailable with a clear code if not configured
        del get_settings_ok

        async def recv():
            try:
                return await ws.receive_text()
            except WebSocketDisconnect:
                return None
        await live.relay(ctx, recv, emit)
        with_close = True
    except asyncio.TimeoutError:
        await _fail(ws, 'TIMEOUT', 'No message received in time.'); with_close = False
    except (json.JSONDecodeError, KeyError):
        await _fail(ws, 'INVALID_JSON', 'Messages must be JSON.'); with_close = False
    except AppError as e:
        await _fail(ws, e.code, e.message); with_close = False
    except WebSocketDisconnect:
        return
    except Exception as e:  # Gemini connection failure etc.
        c = classify(e, get_settings().gemini_live_model)
        log(logger, 'live_failed', logging.ERROR, session=str(session_id), error=type(e).__name__, code=c.code, provider_status=c.provider_status)
        if c.provider_http is None:  # not a Google API error: keep the generic, safe message
            await _fail(ws, 'LIVE_FAILED', 'The live AI connection failed. Please try again.')
        else:
            await _fail(ws, c.code, f'{c.message} {c.hint}'.strip())
        with_close = False
    if with_close:
        try:
            await ws.send_text(json.dumps({'type': 'session_ended'}))
            await ws.close()
        except Exception:
            pass


async def _fail(ws: WebSocket, code: str, message: str):
    try:
        await ws.send_text(json.dumps({'type': 'error', 'code': code, 'message': message, 'fatal': True}))
        await ws.close(code=4400)
    except Exception:
        pass
