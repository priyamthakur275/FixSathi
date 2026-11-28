"""Streaming chat reliability: one jittered retry on 503/timeout for the first two models, skip gemini-4-neon after a recent 429,
and a clear 'Gemini is busy' message when every model answered 503."""
import asyncio
import time

import pytest
from google.genai import errors as ge

from app.config import get_settings
from app.core.exceptions import AIUnavailable
from app.integrations.gemini import client as gc


def _err503():
    return ge.ServerError(503, {'error': {'code': 503, 'status': 'UNAVAILABLE', 'message': 'overloaded'}})


def _err429():
    return ge.ClientError(429, {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', 'message': 'rate limit'}})


class _Chunk:
    def __init__(self, text):
        self.text = text
        self.usage_metadata = None


async def _gen(text):
    yield _Chunk(text)


@pytest.fixture
def setup(monkeypatch):
    for d in (gc.COOLDOWN, gc.CONSECUTIVE_FAILURES, gc.LAST_429):
        d.clear()
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test')
    monkeypatch.setattr(s, 'gemini_fast_model', 'gemini-3.5-flash-lite')
    monkeypatch.setattr(s, 'gemini_agent_model', 'gemini-4-hydrogen')
    monkeypatch.setattr(s, 'gemini_agent_fallback_models', 'gemini-4-neon,gemini-3.5-flash-lite')
    monkeypatch.setattr(s, 'gemini_thinking_level', '')
    monkeypatch.setattr(s, 'gemini_chat_timeout_seconds', 0.05)
    jitter = []

    def fake_uniform(a, b):
        jitter.append((a, b))
        return 0.0

    monkeypatch.setattr(gc.random, 'uniform', fake_uniform)
    yield jitter
    for d in (gc.COOLDOWN, gc.CONSECUTIVE_FAILURES, gc.LAST_429):
        d.clear()


def _client(behaviour, used):
    """behaviour: model -> list of outcomes consumed per call ('503', '429', 'timeout', or reply text)."""
    class Models:
        async def generate_content_stream(self, model, contents, config):
            used.append(model)
            outcome = behaviour[model].pop(0) if len(behaviour[model]) > 1 else behaviour[model][0]
            if outcome == '503':
                raise _err503()
            if outcome == '429':
                raise _err429()
            if outcome == 'timeout':
                await asyncio.sleep(0.5)
            return _gen(outcome)

    g = gc.GeminiClient()
    g._client = type('C', (), {'aio': type('A', (), {'models': Models()})()})()
    return g


async def _collect(g):
    text, meta = '', None
    async for chunk, m in g.stream_text('chat', 'hi', 'sys'):
        text += chunk
        meta = m or meta
    return text, meta


def test_first_model_503_is_retried_once_with_jitter_then_succeeds(setup):
    used = []
    g = _client({'gemini-3.5-flash-lite': ['503', 'ok after retry'], 'gemini-4-hydrogen': ['x'], 'gemini-4-neon': ['x']}, used)
    text, meta = asyncio.run(_collect(g))
    assert text == 'ok after retry' and meta.model == 'gemini-3.5-flash-lite'
    assert used == ['gemini-3.5-flash-lite', 'gemini-3.5-flash-lite']
    assert setup == [(0.4, 0.8)]


def test_timeout_retried_on_first_two_models_then_next(setup):
    used = []
    g = _client({'gemini-3.5-flash-lite': ['timeout'], 'gemini-4-hydrogen': ['timeout', 'timeout'], 'gemini-4-neon': ['from neon']}, used)
    text, meta = asyncio.run(_collect(g))
    assert meta.model == 'gemini-4-neon'
    assert used == ['gemini-3.5-flash-lite', 'gemini-3.5-flash-lite', 'gemini-4-hydrogen', 'gemini-4-hydrogen', 'gemini-4-neon']
    assert setup == [(0.4, 0.8), (0.4, 0.8)]


def test_quota_429_is_not_retried_on_same_model(setup):
    used = []
    g = _client({'gemini-3.5-flash-lite': ['429'], 'gemini-4-hydrogen': ['from hydrogen'], 'gemini-4-neon': ['x']}, used)
    _, meta = asyncio.run(_collect(g))
    assert meta.model == 'gemini-4-hydrogen' and used == ['gemini-3.5-flash-lite', 'gemini-4-hydrogen'] and setup == []


def test_neon_skipped_after_recent_429(setup):
    gc.LAST_429['gemini-4-neon'] = time.time() - 10
    used = []
    g = _client({'gemini-3.5-flash-lite': ['503'], 'gemini-4-hydrogen': ['503'], 'gemini-4-neon': ['429']}, used)
    with pytest.raises(AIUnavailable):
        asyncio.run(_collect(g))
    assert 'gemini-4-neon' not in used


def test_neon_tried_again_after_5_minutes(setup):
    gc.LAST_429['gemini-4-neon'] = time.time() - 301
    used = []
    g = _client({'gemini-3.5-flash-lite': ['503'], 'gemini-4-hydrogen': ['503'], 'gemini-4-neon': ['from neon']}, used)
    _, meta = asyncio.run(_collect(g))
    assert meta.model == 'gemini-4-neon'


def test_neon_429_is_recorded(setup):
    used = []
    g = _client({'gemini-3.5-flash-lite': ['503'], 'gemini-4-hydrogen': ['503'], 'gemini-4-neon': ['429']}, used)
    with pytest.raises(AIUnavailable):
        asyncio.run(_collect(g))
    assert time.time() - gc.LAST_429['gemini-4-neon'] < 5


def test_all_503_shows_busy_message_even_when_neon_429s(setup):
    used = []
    g = _client({'gemini-3.5-flash-lite': ['503'], 'gemini-4-hydrogen': ['503'], 'gemini-4-neon': ['429']}, used)
    with pytest.raises(AIUnavailable) as ei:
        asyncio.run(_collect(g))
    assert ei.value.message == gc.GEMINI_BUSY_MESSAGE
    assert ei.value.code == 'PROVIDER_UNAVAILABLE'
    assert gc.GEMINI_BUSY_MESSAGE == "Google's Gemini service is busy right now. Please press Retry in a few seconds."


def test_all_503_with_neon_skipped_shows_busy_message(setup):
    gc.LAST_429['gemini-4-neon'] = time.time()
    used = []
    g = _client({'gemini-3.5-flash-lite': ['503'], 'gemini-4-hydrogen': ['503'], 'gemini-4-neon': ['429']}, used)
    with pytest.raises(AIUnavailable) as ei:
        asyncio.run(_collect(g))
    assert ei.value.message == gc.GEMINI_BUSY_MESSAGE
    assert used == ['gemini-3.5-flash-lite', 'gemini-3.5-flash-lite', 'gemini-4-hydrogen', 'gemini-4-hydrogen']


def test_mixed_failures_keep_real_error_not_busy_message(setup):
    used = []
    g = _client({'gemini-3.5-flash-lite': ['503'], 'gemini-4-hydrogen': ['timeout'], 'gemini-4-neon': ['429']}, used)
    with pytest.raises(Exception) as ei:
        asyncio.run(_collect(g))
    assert getattr(ei.value, 'message', '') != gc.GEMINI_BUSY_MESSAGE
