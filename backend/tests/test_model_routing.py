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
