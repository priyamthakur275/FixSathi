"""Tests for task-specific Gemini model ordering, fallback order, and AQ key redaction."""
import logging
from app.config import get_settings
from app.core.logging import JsonFormatter
from app.integrations.gemini.client import GeminiClient


def test_chat_prefers_fast_model_then_agent_fallbacks(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'AQ.FakeUnitTestKey12345678901234567890')
    monkeypatch.setattr(s, 'gemini_agent_model', 'gemini-4-neon')
    monkeypatch.setattr(s, 'gemini_fast_model', 'gemini-3.5-flash-lite')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'gemini-4-hydrogen,gemini-3.5-flash-lite')

    g = GeminiClient()
    assert g._agent_models('chat') == ['gemini-3.5-flash-lite', 'gemini-4-neon', 'gemini-4-hydrogen']
    assert g._agent_models('diagnosis') == ['gemini-4-neon', 'gemini-4-hydrogen', 'gemini-3.5-flash-lite']
    assert g._agent_models('nameplate') == ['gemini-4-neon', 'gemini-4-hydrogen', 'gemini-3.5-flash-lite']


def test_json_formatter_redacts_aq_api_keys():
    fmt = JsonFormatter()
    rec = logging.LogRecord('gemini', logging.ERROR, __file__, 1, 'bad key AQ.Ab8RN6FakeSecretKey0123456789abcdef', (), None)
    out = fmt.format(rec)
    assert 'AQ.Ab8RN6FakeSecretKey' not in out
    assert '[redacted-key]' in out


def test_cloudsql_unix_socket_database_url_preserves_host_and_password():
    import urllib.parse
    from sqlalchemy.dialects.postgresql.psycopg import dialect
    from sqlalchemy.engine import make_url
    from app.config import Settings

    raw_pw = 'p@ss/w:o+r=d'
    encoded = urllib.parse.quote(raw_pw, safe='')
    raw_url = f'postgresql://fixsaathi:{encoded}@/fixsaathi?host=/cloudsql/geminisprints26blr-3820:us-east4:fixsaathi-db'
    rewritten = Settings._db(raw_url)
    assert rewritten.startswith('postgresql+psycopg://')
    _, kwargs = dialect().create_connect_args(make_url(rewritten))
    assert kwargs['host'] == '/cloudsql/geminisprints26blr-3820:us-east4:fixsaathi-db'
    assert kwargs['dbname'] == 'fixsaathi'
    assert kwargs['user'] == 'fixsaathi'
    assert kwargs['password'] == raw_pw


def test_circuit_breaker_trips_for_5_minutes_after_two_consecutive_failures(monkeypatch):
    import asyncio, time as _t
    from google.genai import errors as ge
    from app.integrations.gemini import client as gc

    gc.COOLDOWN.clear()
    gc.CONSECUTIVE_FAILURES.clear()
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test')
    monkeypatch.setattr(s, 'gemini_agent_model', 'flaky')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'steady')
    monkeypatch.setattr(s, 'gemini_fast_model', '')
    monkeypatch.setattr(s, 'gemini_max_retries', 0)
    monkeypatch.setattr(s, 'gemini_thinking_level', '')
    monkeypatch.setattr(s, 'gemini_hedge_seconds', 0)
    monkeypatch.setattr(s, 'gemini_chat_timeout_seconds', 0.05)

    used = []

    class Resp:
        text = 'ok'; candidates = [object()]; prompt_feedback = None; usage_metadata = None

    class Models:
        async def generate_content(self, model, contents, config):
            used.append(model)
            if model == 'flaky':
                raise ge.ClientError(429, {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', 'message': 'rate limit'}})
            return Resp()

    g = gc.GeminiClient()
    g._client = type('C', (), {'aio': type('A', (), {'models': Models()})()})()
    try:
        # 1st failure sets short cooldown (<300s); expire it manually to trigger 2nd consecutive failure
        _, m1 = asyncio.run(g.generate_text('chat', 'hi', 'sys'))
        assert m1.model == 'steady' and gc.CONSECUTIVE_FAILURES.get('flaky') == 1
        gc.COOLDOWN.pop('flaky', None)

        _, m2 = asyncio.run(g.generate_text('chat', 'hi 2', 'sys'))
        assert m2.model == 'steady' and gc.CONSECUTIVE_FAILURES.get('flaky') == 2
        assert gc.COOLDOWN['flaky'] - _t.time() >= 290.0  # 5-minute circuit breaker tripped
    finally:
        gc.COOLDOWN.clear()
        gc.CONSECUTIVE_FAILURES.clear()


def test_timeout_falls_back_to_next_model(monkeypatch):
    import asyncio
    from app.integrations.gemini import client as gc

    gc.COOLDOWN.clear()
    gc.CONSECUTIVE_FAILURES.clear()
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test')
    monkeypatch.setattr(s, 'gemini_agent_model', 'slow-model')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'fast-model')
    monkeypatch.setattr(s, 'gemini_fast_model', '')
    monkeypatch.setattr(s, 'gemini_max_retries', 0)
    monkeypatch.setattr(s, 'gemini_thinking_level', '')
    monkeypatch.setattr(s, 'gemini_hedge_seconds', 0)
    monkeypatch.setattr(s, 'gemini_chat_timeout_seconds', 0.05)

    used = []

    class Resp:
        text = 'from fast'; candidates = [object()]; prompt_feedback = None; usage_metadata = None

    class Models:
        async def generate_content(self, model, contents, config):
            used.append(model)
            if model == 'slow-model':
                await asyncio.sleep(0.5)
            return Resp()

    g = gc.GeminiClient()
    g._client = type('C', (), {'aio': type('A', (), {'models': Models()})()})()
    try:
        text, meta = asyncio.run(g.generate_text('chat', 'hi', 'sys'))
        assert text == 'from fast' and meta.model == 'fast-model' and used == ['slow-model', 'fast-model']
    finally:
        gc.COOLDOWN.clear()
        gc.CONSECUTIVE_FAILURES.clear()


def test_health_exposes_cached_models_available(client, monkeypatch):
    from app.integrations.gemini import client as gc
    monkeypatch.setattr(gc, 'MODELS_CHECK_CACHE', {'at': 9999999999.0, 'models': ['gemini-4-hydrogen', 'gemini-3.5-flash-lite']})
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['ai']['models_available'] == ['gemini-4-hydrogen', 'gemini-3.5-flash-lite']


def test_sample_nameplate_endpoint_returns_png(client):
    r = client.get('/api/v1/samples/nameplate')
    assert r.status_code == 200
    assert r.headers['content-type'] == 'image/png'
    assert r.content.startswith(b'\x89PNG')
