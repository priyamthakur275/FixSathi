"""Every provider failure maps to a specific, safe category. Uses the SDK's real error classes."""
import asyncio
import httpx, httpx2, pytest
from google.genai import errors
from app.config import get_settings
from app.integrations.gemini.client import GeminiClient
from app.integrations.gemini.errors import classify


def api(code, status, msg, details=None):
    cls = errors.ClientError if code < 500 else errors.ServerError
    return cls(code, {'error': {'code': code, 'status': status, 'message': msg, 'details': details or []}})


@pytest.mark.parametrize('exc,expected,retry', [
    (api(400, 'INVALID_ARGUMENT', 'API key not valid. Please pass a valid API key.', [{'reason': 'API_KEY_INVALID'}]), 'INVALID_API_KEY', False),
    (api(400, 'INVALID_ARGUMENT', 'Invalid JSON payload received.'), 'INVALID_REQUEST', False),
    (api(400, 'FAILED_PRECONDITION', 'User location is not supported for the API use.'), 'REGION_NOT_SUPPORTED', False),
    (api(403, 'PERMISSION_DENIED', 'Generative Language API has not been used in project 123 before or it is disabled.'), 'PERMISSION_DENIED', False),
    (api(404, 'NOT_FOUND', 'models/gemini-9 is not found for API version v1beta'), 'MODEL_NOT_FOUND', False),
    (api(429, 'RESOURCE_EXHAUSTED', 'Quota exceeded for metric generate_content_free_tier_requests, limit: 0'), 'BILLING_REQUIRED', False),
    (api(429, 'RESOURCE_EXHAUSTED', 'Resource has been exhausted (e.g. check quota).'), 'QUOTA_EXCEEDED', True),
    (api(503, 'UNAVAILABLE', 'The model is overloaded.'), 'PROVIDER_UNAVAILABLE', True),
    (asyncio.TimeoutError(), 'AI_TIMEOUT', True),
    (httpx.ConnectError('dns failure'), 'NETWORK_ERROR', True),
    (httpx2.ConnectError('connection reset'), 'NETWORK_ERROR', True),  # google-genai 3.x transport
    (httpx2.RemoteProtocolError('peer closed connection'), 'NETWORK_ERROR', True),
    (httpx2.ReadTimeout('read timed out'), 'AI_TIMEOUT', True),
    (ValueError('boom'), 'AI_INTERNAL_ERROR', False),
])
def test_classify(exc, expected, retry):
    c = classify(exc, 'gemini-x')
    assert c.code == expected and c.retryable is retry and c.message and c.hint


def test_key_never_leaks_into_messages():
    c = classify(api(400, 'INVALID_ARGUMENT', 'API key not valid: ' + 'AIza' + 'Sy' + 'X' * 33 + ' key=abc'))
    assert 'AIza' not in (c.provider_message or '') and 'key=abc' not in (c.provider_message or '')


def test_no_retry_on_bad_key_and_bounded_retry_on_outage(monkeypatch):
    calls = {'n': 0}

    async def bad_key():
        calls['n'] += 1; raise api(400, 'INVALID_ARGUMENT', 'API key not valid.')

    async def outage():
        calls['n'] += 1; raise api(503, 'UNAVAILABLE', 'overloaded')
    monkeypatch.setenv('GEMINI_MAX_RETRIES', '2'); get_settings.cache_clear()
    monkeypatch.setattr('app.integrations.gemini.client.asyncio.sleep', lambda *_: _noop())
    g = GeminiClient(client=object())
    with pytest.raises(Exception) as e:
        asyncio.run(g._call('t', 'm', bad_key))
    assert e.value.code == 'INVALID_API_KEY' and calls['n'] == 1
    calls['n'] = 0
    with pytest.raises(Exception) as e:
        asyncio.run(g._call('t', 'm', outage))
    assert e.value.code == 'PROVIDER_UNAVAILABLE' and calls['n'] == 3


async def _noop():
    return None


def test_key_whitespace_and_quotes_stripped(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', '  "abc123"\n'); monkeypatch.setenv('GEMINI_AGENT_MODEL', ' gemini-3.6-flash '); get_settings.cache_clear()
    s = get_settings()
    assert s.gemini_api_key == 'abc123' and s.gemini_agent_model == 'gemini-3.6-flash'


def test_chat_surfaces_specific_reason(client, tech, session_id, fake):
    from app.core.exceptions import AIUnavailable
    fake.fail['chat'] = AIUnavailable('The server\'s Gemini API key is invalid, expired or revoked.', code='INVALID_API_KEY', details={'hint': 'Create a new key', 'provider_status': 'INVALID_ARGUMENT'})
    r = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'fan hums'}, headers=tech['h']).json()
    assert r['ai_status'] == 'unavailable' and r['ai_error']['code'] == 'INVALID_API_KEY' and r['ai_error']['hint'] == 'Create a new key'


def test_blocked_and_empty_responses():
    class C:  # minimal response shapes
        def __init__(self, text=None, block=None, finish=None):
            self.text = text; self.prompt_feedback = type('F', (), {'block_reason': block})() if block else None
            self.candidates = [type('Cand', (), {'finish_reason': finish})()] if finish or text else []
    with pytest.raises(Exception) as e:
        GeminiClient._text_or_raise(C(block='SAFETY'), 'chat')
    assert e.value.code == 'AI_BLOCKED'
    with pytest.raises(Exception) as e:
        GeminiClient._text_or_raise(C(finish='MAX_TOKENS'), 'chat')
    assert e.value.code == 'AI_EMPTY'
    assert GeminiClient._text_or_raise(C(text=' OK '), 'chat') == 'OK'


def test_ai_status_endpoint_has_no_secret(client, tech, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'super-secret-value-1234567890'); get_settings.cache_clear()
    r = client.get('/api/v1/ai/status', headers=tech['h'])
    assert r.status_code == 200 and r.json()['configured'] is True and 'super-secret' not in r.text


def test_free_tier_rate_limit_is_quota_not_billing():
    from google.genai import errors as ge
    from app.integrations.gemini.errors import classify
    rl = ge.ClientError(429, {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', 'message':
         'You exceeded your current quota. Quota exceeded for metric: generate_content_free_tier_requests, limit: 10. Please retry in 7.5s.'}})
    c = classify(rl, 'm'); assert c.code == 'QUOTA_EXCEEDED' and c.retryable and c.retry_after == 7.5
    zero = ge.ClientError(429, {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', 'message':
           'Quota exceeded for metric: generate_content_free_tier_requests, limit: 0'}})
    assert classify(zero, 'm').code == 'BILLING_REQUIRED'


def test_agent_falls_back_to_next_model_on_rate_limit(monkeypatch):
    import asyncio
    from google.genai import errors as ge
    from app.config import get_settings
    from app.integrations.gemini.client import GeminiClient
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_agent_model', 'primary')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'backup'); monkeypatch.setattr(s, 'gemini_max_retries', 0)
    monkeypatch.setattr(s, 'gemini_thinking_level', 'low')
    used = []

    class Resp:
        text = 'ok'; candidates = [object()]; prompt_feedback = None; usage_metadata = None

    class Models:
        async def generate_content(self, model, contents, config):
            used.append((model, config.thinking_config.thinking_level if config.thinking_config else None))
            if model == 'primary':
                raise ge.ClientError(429, {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', 'message': 'free_tier_requests, limit: 10'}})
            return Resp()

    g = GeminiClient()
    g._client = type('C', (), {'aio': type('A', (), {'models': Models()})()})()
    text, meta = asyncio.run(g.generate_text('chat', 'hi', 'sys'))
    assert text == 'ok' and meta.model == 'backup' and [u[0] for u in used] == ['primary', 'backup'] and used[0][1] is not None


def test_exhausted_model_is_skipped_on_the_next_message(monkeypatch):
    """Live log 20 Nov: two exhausted models were retried on every message (24 s). Now: no retry wait on them, then skipped."""
    import asyncio, time as _t
    from google.genai import errors as ge
    from app.config import get_settings
    from app.integrations.gemini import client as gc
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_agent_model', 'a')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'b,c'); monkeypatch.setattr(s, 'gemini_max_retries', 1)
    monkeypatch.setattr(s, 'gemini_thinking_level', '')
    used = []

    class Resp:
        text = 'ok'; candidates = [object()]; prompt_feedback = None; usage_metadata = None

    class Models:
        async def generate_content(self, model, contents, config):
            used.append(model)
            if model in ('a', 'b'):
                raise ge.ClientError(429, {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', 'message': 'free_tier_requests, limit: 10'}})
            return Resp()

    g = gc.GeminiClient()
    g._client = type('C', (), {'aio': type('A', (), {'models': Models()})()})()
    t0 = _t.perf_counter()
    text, meta = asyncio.run(g.generate_text('chat', 'hi', 'sys'))
    assert meta.model == 'c' and used == ['a', 'b', 'c'] and _t.perf_counter() - t0 < 1.0  # no retry sleeps on exhausted models
    used.clear()
    text, meta = asyncio.run(g.generate_text('chat', 'hi again', 'sys'))
    assert meta.model == 'c' and used == ['c']  # a and b are cooling down
    gc.COOLDOWN.clear()


def test_schema_too_complex_falls_back_and_keeps_thinking(monkeypatch):
    """Live run 21 Nov: gemini-3.1-flash-lite rejected the diagnosis schema ('too many states'); diagnosis failed with 502
    instead of trying the next fallback model, and thinking was switched off for every model."""
    import asyncio
    from google.genai import errors as ge
    from app.config import get_settings
    from app.integrations.gemini.client import GeminiClient
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_agent_model', 'lite')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'big'); monkeypatch.setattr(s, 'gemini_max_retries', 0)
    monkeypatch.setattr(s, 'gemini_thinking_level', 'low')
    used = []

    class Resp:
        text = '{"x": 1}'; candidates = [object()]; prompt_feedback = None; usage_metadata = None

    class Models:
        async def generate_content(self, model, contents, config):
            used.append((model, config.thinking_config is not None))
            if model == 'lite':
                raise ge.ClientError(400, {'error': {'code': 400, 'status': 'INVALID_ARGUMENT', 'message':
                                     'The specified schema produces a constraint that has too many states for serving.'}})
            return Resp()

    g = GeminiClient()
    g._client = type('C', (), {'aio': type('A', (), {'models': Models()})()})()
    text, meta = asyncio.run(g.generate_text('diagnosis', 'hi', 'sys'))
    assert meta.model == 'big' and used == [('lite', True), ('big', True)] and not getattr(g, '_no_thinking_cfg', False)


def test_schema_too_complex_retries_same_model_with_relaxed_schema(monkeypatch):
    """Only model available rejects the full schema: it is retried once without length limits; the reply is still validated."""
    import asyncio
    from google.genai import errors as ge
    from pydantic import BaseModel, Field
    from app.config import get_settings
    from app.integrations.gemini.client import GeminiClient
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_agent_model', 'lite')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', ''); monkeypatch.setattr(s, 'gemini_max_retries', 0)

    class Out(BaseModel):
        items: list[str] = Field(max_length=2)

    seen = []

    class Resp:
        candidates = [object()]; prompt_feedback = None; usage_metadata = None
        def __init__(self, text): self.text = text

    class Models:
        async def generate_content(self, model, contents, config):
            sch = config.response_json_schema; seen.append('maxItems' in str(sch))
            if 'maxItems' in str(sch):
                raise ge.ClientError(400, {'error': {'code': 400, 'status': 'INVALID_ARGUMENT', 'message': 'schema produces a constraint that has too many states'}})
            return Resp(RESP)

    g = GeminiClient()
    g._client = type('C', (), {'aio': type('A', (), {'models': Models()})()})()
    RESP = '{"items": ["a"]}'
    out, meta = asyncio.run(g.generate_json('diagnosis', Out, 'hi', 'sys'))
    assert out.items == ['a'] and seen == [True, False]
    from app.core.exceptions import AIError
    import pytest
    RESP = '{"items": ["a", "b", "c"]}'  # breaks the real limit: still rejected by server-side validation
    with pytest.raises(AIError) as e:
        asyncio.run(g.generate_json('diagnosis', Out, 'hi', 'sys'))
    assert e.value.code == 'AI_INVALID_OUTPUT'


def _fake_models(behaviour, used):
    class Models:
        async def generate_content(self, model, contents, config):
            used.append(model)
            return await behaviour(model)
    return type('C', (), {'aio': type('A', (), {'models': Models()})()})()


def test_overloaded_model_fails_over_without_retrying_it(monkeypatch):
    """Live log 21 Nov: a 504/503 from the agent model was retried on the same model (45 s + 45 s) instead of trying the fallback."""
    from google.genai import errors as ge
    from app.integrations.gemini import client as gc
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_agent_model', 'a')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'b'); monkeypatch.setattr(s, 'gemini_max_retries', 1)
    monkeypatch.setattr(s, 'gemini_thinking_level', ''); monkeypatch.setattr(s, 'gemini_hedge_seconds', 0)
    used = []

    async def behaviour(model):
        if model == 'a':
            raise ge.ServerError(503, {'error': {'code': 503, 'status': 'UNAVAILABLE', 'message': 'This model is currently experiencing high demand.'}})
        r = type('R', (), {'text': 'from b', 'candidates': [object()], 'prompt_feedback': None, 'usage_metadata': None})
        return r()
    g = gc.GeminiClient(); g._client = _fake_models(behaviour, used)
    text, meta = asyncio.run(g.generate_text('diagnosis_text', 'hi', 'sys'))
    assert text == 'from b' and used == ['a', 'b']
    used.clear()
    asyncio.run(g.generate_text('diagnosis_text', 'again', 'sys'))
    assert used == ['b']  # the overloaded model cools down briefly
    gc.COOLDOWN.clear()


def test_slow_chat_reply_is_hedged_with_the_fallback(monkeypatch):
    import time as _t
    from app.integrations.gemini import client as gc
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_agent_model', 'slow')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'quick'); monkeypatch.setattr(s, 'gemini_max_retries', 0)
    monkeypatch.setattr(s, 'gemini_thinking_level', ''); monkeypatch.setattr(s, 'gemini_hedge_seconds', 0.05)
    used, cancelled = [], []

    async def behaviour(model):
        try:
            await asyncio.sleep(5 if model == 'slow' else 0.01)
        except asyncio.CancelledError:
            cancelled.append(model); raise
        return type('R', (), {'text': f'from {model}', 'candidates': [object()], 'prompt_feedback': None, 'usage_metadata': None})()
    g = gc.GeminiClient(); g._client = _fake_models(behaviour, used)
    t0 = _t.perf_counter()
    text, meta = asyncio.run(g.generate_text('chat', 'hi', 'sys'))
    assert text == 'from quick' and meta.model == 'quick' and used == ['slow', 'quick'] and cancelled == ['slow'] and _t.perf_counter() - t0 < 1


def test_fast_chat_reply_is_not_hedged(monkeypatch):
    from app.integrations.gemini import client as gc
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_agent_model', 'a')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'b'); monkeypatch.setattr(s, 'gemini_thinking_level', '')
    monkeypatch.setattr(s, 'gemini_hedge_seconds', 5)
    used = []

    async def behaviour(model):
        return type('R', (), {'text': 'ok', 'candidates': [object()], 'prompt_feedback': None, 'usage_metadata': None})()
    g = gc.GeminiClient(); g._client = _fake_models(behaviour, used)
    text, meta = asyncio.run(g.generate_text('chat', 'hi', 'sys'))
    assert meta.model == 'a' and used == ['a']


def test_relaxed_schema_is_remembered_per_model(monkeypatch):
    """Live log 21 Nov: every diagnosis on gemini-3.1-flash-lite cost a rejected call before the relaxed one."""
    from google.genai import errors as ge
    from pydantic import BaseModel, Field
    from app.integrations.gemini import client as gc
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_agent_model', 'lite')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', ''); monkeypatch.setattr(s, 'gemini_max_retries', 0)

    class Out(BaseModel):
        items: list[str] = Field(max_length=2)
    seen = []

    class Models:
        async def generate_content(self, model, contents, config):
            full = 'maxItems' in str(config.response_json_schema); seen.append(full)
            if full:
                raise ge.ClientError(400, {'error': {'code': 400, 'status': 'INVALID_ARGUMENT', 'message': 'schema produces a constraint that has too many states'}})
            return type('R', (), {'text': '{"items": ["a"]}', 'candidates': [object()], 'prompt_feedback': None, 'usage_metadata': None})()
    g = gc.GeminiClient(); g._client = type('C', (), {'aio': type('A', (), {'models': Models()})()})()
    asyncio.run(g.generate_json('diagnosis', Out, 'hi', 'sys'))
    asyncio.run(g.generate_json('diagnosis', Out, 'again', 'sys'))
    assert seen == [True, False, False]  # one rejected call in total, not one per diagnosis


def test_daily_quota_is_not_retried(monkeypatch):
    from google.genai import errors as ge
    calls = {'n': 0}

    async def daily():
        calls['n'] += 1
        raise ge.ClientError(429, {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', 'message': 'Quota exceeded for metric: generate_content_free_tier_requests, limit: 20. Please retry in 58084.5s.'}})
    monkeypatch.setenv('GEMINI_MAX_RETRIES', '2'); get_settings.cache_clear()
    slept = []

    async def fake_sleep(t):
        slept.append(t)
    monkeypatch.setattr('app.integrations.gemini.client.asyncio.sleep', fake_sleep)
    g = GeminiClient(client=object())
    with pytest.raises(Exception) as e:
        asyncio.run(g._call('chat', 'm', daily))
    assert e.value.code == 'QUOTA_EXCEEDED' and calls['n'] == 1 and slept == []
