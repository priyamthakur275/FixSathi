"""Demo mode is labelled and still goes through the real safety gate; database storage survives a storage reset."""
from app.integrations.storage import local as st
from app.config import get_settings
import pytest
from tests.conftest import register


@pytest.fixture
def other(client): return register(client, org='Other Co')


def _start(client, tech, scenario='ceiling_fan_burn'):
    r = client.post('/api/v1/demo/sessions', json={'scenario': scenario}, headers=tech['h']); assert r.status_code == 201, r.text
    return r.json()


def test_demo_lists_scenarios_and_requires_login(client, tech):
    assert client.get('/api/v1/demo/scenarios').status_code == 401
    r = client.get('/api/v1/demo/scenarios', headers=tech['h']).json()
    assert 'not live AI' in r['label'] and {x['id'] for x in r['items']} >= {'ceiling_fan_burn', 'split_ac_not_cooling'}


def test_demo_session_is_labelled_never_ai(client, tech):
    s = _start(client, tech); assert s['demo'] is True and s['title'].startswith('Demo:')
    msgs = client.get(f"/api/v1/sessions/{s['id']}/messages", headers=tech['h']).json()['items']
    a = [m for m in msgs if m['role'] == 'assistant'][0]
    assert a['meta']['demo'] is True and a['meta']['ai_generated'] is False and a['message'].startswith('DEMO SCENARIO')
    assert len(client.get(f"/api/v1/sessions/{s['id']}/images", headers=tech['h']).json()) == 1
    d = client.post(f"/api/v1/sessions/{s['id']}/diagnose", json={'media_ids': []}, headers=tech['h']).json()
    assert d['model_identifier'] == 'demo-scenario'


def test_demo_session_keeps_the_real_safety_gate(client, tech):
    s = _start(client, tech); sid = s['id']
    assert client.post(f'/api/v1/sessions/{sid}/diagnose', json={'media_ids': []}, headers=tech['h']).status_code == 201
    r0 = client.post(f'/api/v1/sessions/{sid}/steps/generate', headers=tech['h']); assert r0.status_code == 201, r0.text; steps = r0.json()
    power = [x for x in steps if x['requires_power_off']]
    assert power and all(x['locked'] and x['instruction'] is None for x in power)
    r = client.post(f"/api/v1/sessions/{sid}/steps/{power[0]['id']}/complete", headers=tech['h'])
    assert r.status_code == 409
    client.post(f'/api/v1/sessions/{sid}/safety/confirm', json={'power_off_confirmed': True, 'tester_checked': False}, headers=tech['h'])
    assert client.post(f"/api/v1/sessions/{sid}/steps/{power[0]['id']}/complete", headers=tech['h']).status_code == 409
    client.post(f'/api/v1/sessions/{sid}/safety/confirm', json={'power_off_confirmed': True, 'tester_checked': True}, headers=tech['h'])
    assert client.post(f"/api/v1/sessions/{sid}/steps/{power[0]['id']}/complete", headers=tech['h']).status_code == 200


def test_unknown_scenario_and_other_users_cannot_read_demo(client, tech, other):
    assert client.post('/api/v1/demo/sessions', json={'scenario': 'nope'}, headers=tech['h']).status_code == 404
    s = _start(client, tech, 'split_ac_not_cooling')
    assert client.get(f"/api/v1/sessions/{s['id']}", headers=other['h']).status_code == 404


def test_database_storage_survives_restart_and_is_access_checked(client, tech, other, monkeypatch, session_id):
    from tests.fakes import png
    monkeypatch.setattr(get_settings(), 'storage_provider', 'database'); st.reset_storage()
    try:
        up = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('a.png', png(), 'image/png')}, headers=tech['h']); assert up.status_code == 201
        url = up.json()['url']
        st.reset_storage()  # simulate a restart: nothing is cached in memory or on disk
        r = client.get(url, headers=tech['h']); assert r.status_code == 200
        import io as _io
        from PIL import Image as _Im
        assert _Im.open(_io.BytesIO(r.content)).convert('RGB').tobytes() == _Im.open(_io.BytesIO(png())).convert('RGB').tobytes()  # same pixels, metadata stripped
        assert client.get(url, headers=other['h']).status_code == 404
        assert client.get(url).status_code == 401
        bad = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('x.png', b'not an image', 'image/png')}, headers=tech['h'])
        assert bad.status_code == 415
    finally:
        monkeypatch.setattr(get_settings(), 'storage_provider', 'local'); st.reset_storage()


def test_missing_local_file_is_a_clear_404(client, tech, session_id, monkeypatch):
    from tests.fakes import png
    up = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('a.png', png(), 'image/png')}, headers=tech['h']).json()
    import shutil; shutil.rmtree(st.get_storage().root, ignore_errors=True)
    r = client.get(up['url'], headers=tech['h']); assert r.status_code == 404 and r.json()['error']['code'] == 'MEDIA_MISSING'


def test_health_checks_the_database_and_supports_head(client, monkeypatch):
    r = client.get('/health'); assert r.status_code == 200 and r.json()['database'] == 'ok'
    assert client.head('/health').status_code == 200
    from app import main
    class Broken:
        def execute(self, *a, **k): raise RuntimeError('db down')
        def close(self): pass
    monkeypatch.setattr(main, 'SessionLocal', lambda: Broken())
    r = client.get('/health'); assert r.status_code == 503 and r.json()['status'] == 'unhealthy' and r.json()['database'] == 'unreachable'
