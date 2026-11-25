"""Per-user AI quota: one account cannot spend the whole Gemini key. Scripted demo sessions are not counted."""
from app.config import get_settings
from tests.conftest import register


def _session(client, h, text='Fan humming, not starting'):
    r = client.post('/api/v1/sessions', json={'appliance_type': 'ceiling_fan', 'issue_description': text}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()['id']


def test_chat_over_the_minute_limit_keeps_the_message_and_explains(client, fake, monkeypatch):
    monkeypatch.setenv('AI_REQUESTS_PER_MINUTE', '2'); get_settings.cache_clear()
    h = register(client)['h']
    sid = _session(client, h)
    for _ in range(2):
        r = client.post(f'/api/v1/sessions/{sid}/messages', json={'text': 'still humming'}, headers=h)
        assert r.json()['ai_status'] == 'ok', r.text
    r = client.post(f'/api/v1/sessions/{sid}/messages', json={'text': 'third question'}, headers=h)
    body = r.json()
    assert r.status_code == 201 and body['ai_status'] == 'error'
    assert body['ai_error']['code'] == 'AI_RATE_LIMITED' and body['ai_error']['hint']
    assert body['user_message']['message'] == 'third question'  # the technician's words are saved anyway
    msgs = client.get(f'/api/v1/sessions/{sid}/messages', headers=h).json()['items']
    assert [m['message'] for m in msgs if m['role'] == 'user'][-1] == 'third question'


def test_quota_is_per_account(client, fake, monkeypatch):
    monkeypatch.setenv('AI_REQUESTS_PER_MINUTE', '1'); get_settings.cache_clear()
    a, b = register(client)['h'], register(client)['h']
    sa, sb = _session(client, a), _session(client, b)
    assert client.post(f'/api/v1/sessions/{sa}/messages', json={'text': 'q'}, headers=a).json()['ai_status'] == 'ok'
    assert client.post(f'/api/v1/sessions/{sa}/messages', json={'text': 'q'}, headers=a).json()['ai_error']['code'] == 'AI_RATE_LIMITED'
    assert client.post(f'/api/v1/sessions/{sb}/messages', json={'text': 'q'}, headers=b).json()['ai_status'] == 'ok'


def test_diagnosis_over_the_daily_limit_is_429(client, fake, monkeypatch):
    monkeypatch.setenv('AI_REQUESTS_PER_DAY', '1'); get_settings.cache_clear()
    h = register(client)['h']
    sid = _session(client, h)
    assert client.post(f'/api/v1/sessions/{sid}/diagnose', headers=h).status_code == 201
    r = client.post(f'/api/v1/sessions/{sid}/diagnose', headers=h)
    assert r.status_code == 429 and r.json()['error']['code'] == 'AI_RATE_LIMITED'
    assert 'resets' in r.json()['error']['details']['hint']


def test_demo_sessions_are_not_counted(client, monkeypatch):
    monkeypatch.setenv('AI_REQUESTS_PER_MINUTE', '1'); get_settings.cache_clear()
    h = register(client)['h']
    sid = client.post('/api/v1/demo/sessions', json={'scenario': 'split_ac_not_cooling'}, headers=h).json()['id']
    for _ in range(3):
        r = client.post(f'/api/v1/sessions/{sid}/messages', json={'text': 'what next?'}, headers=h)
        assert r.json()['ai_status'] == 'ok', r.text


def test_zero_disables_the_limit(client, fake, monkeypatch):
    monkeypatch.setenv('AI_REQUESTS_PER_MINUTE', '0'); monkeypatch.setenv('AI_REQUESTS_PER_DAY', '0'); get_settings.cache_clear()
    h = register(client)['h']
    sid = _session(client, h)
    for _ in range(4):
        assert client.post(f'/api/v1/sessions/{sid}/messages', json={'text': 'q'}, headers=h).json()['ai_status'] == 'ok'
