from app.core.exceptions import AIError
from tests.conftest import DIAG, png, register


def test_diagnosis_validated_sorted_and_image_evidence_stripped(client, tech, session_id, fake):
    r = client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    assert r.status_code == 201
    d = r.json()
    assert [f['fault'] for f in d['faults']] == ['Weak capacitor', 'Worn bearings']
    assert all(e['source'] != 'observed_in_image' for f in d['faults'] for e in f['evidence'])  # no image was sent
    assert 'not calibrated' in d['confidence_note']
    assert client.get(f'/api/v1/sessions/{session_id}/diagnosis', headers=tech['h']).json()['id'] == d['id']


def test_diagnosis_keeps_image_evidence_when_image_sent(client, tech, session_id, fake):
    m = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('a.png', png(), 'image/png')}, headers=tech['h']).json()
    d = client.post(f'/api/v1/sessions/{session_id}/diagnose', json={'media_ids': [m['id']]}, headers=tech['h']).json()
    assert any(e['source'] == 'observed_in_image' for f in d['faults'] for e in f['evidence'])


def test_invalid_model_json(client, tech, session_id, fake):
    fake.json['diagnosis'] = '{"possible_faults": "not a list"'
    r = client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    assert r.status_code == 502 and r.json()['error']['code'] == 'AI_INVALID_OUTPUT'
    assert client.get(f'/api/v1/sessions/{session_id}', headers=tech['h']).json()['status'] == 'active'


def test_out_of_range_confidence_rejected(client, tech, session_id, fake):
    bad = dict(DIAG); bad['possible_faults'] = [{'fault': 'x', 'explanation': 'y', 'confidence': 1.7, 'evidence': []}]
    fake.json['diagnosis'] = bad
    assert client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h']).json()['error']['code'] == 'AI_INVALID_OUTPUT'


def test_timeout_and_quota_translated(client, tech, session_id, fake):
    fake.fail['diagnosis'] = AIError('The AI model took too long to respond.', code='AI_TIMEOUT')
    assert client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h']).json()['error']['code'] == 'AI_TIMEOUT'
    fake.fail['diagnosis'] = AIError('quota', code='AI_QUOTA_EXCEEDED', status=503)
    r = client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    assert r.status_code == 503 and r.json()['error']['code'] == 'AI_QUOTA_EXCEEDED'


def test_missing_key_is_clear(client, tech, session_id):
    r = client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    assert r.status_code == 503 and r.json()['error']['code'] == 'AI_NOT_CONFIGURED'
    h = client.get('/health').json()
    assert h['ai']['configured'] is False and 'GEMINI' not in str(h).upper().replace('AI', '')


def test_model_not_configured_is_not_substituted(client, tech, session_id, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv('GEMINI_API_KEY', 'x' * 30); get_settings.cache_clear()
    r = client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    assert r.status_code == 503 and r.json()['error']['code'] == 'MODEL_NOT_CONFIGURED'


def test_steps_need_diagnosis(client, tech, session_id, fake):
    r = client.post(f'/api/v1/sessions/{session_id}/steps/generate', headers=tech['h'])
    assert r.status_code == 409 and r.json()['error']['code'] == 'DIAGNOSIS_REQUIRED'


def test_component_identification(client, tech, session_id, fake):
    m = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('a.png', png(), 'image/png')}, headers=tech['h']).json()
    fake.json['part_locator'] = {'found': True, 'component_name': 'Capacitor', 'explanation': 'visible', 'box': {'x_min': 100, 'y_min': 200, 'x_max': 300, 'y_max': 400}, 'confidence': 0.5}
    r = client.post(f'/api/v1/sessions/{session_id}/identify-component', json={'media_id': m['id'], 'query': 'capacitor'}, headers=tech['h'])
    assert r.status_code == 201 and r.json()['box']['x_max'] == 300 and '0-1000' in r.json()['coordinate_system']
    fake.json['part_locator'] = {'found': True, 'component_name': 'X', 'explanation': 'e', 'box': {'x_min': 500, 'y_min': 0, 'x_max': 100, 'y_max': 1200}, 'confidence': 0.5}
    assert client.post(f'/api/v1/sessions/{session_id}/identify-component', json={'media_id': m['id']}, headers=tech['h']).json()['error']['code'] == 'AI_INVALID_OUTPUT'
    fake.json['part_locator'] = {'found': False, 'explanation': 'not visible', 'box': {'x_min': 1, 'y_min': 1, 'x_max': 2, 'y_max': 2}, 'confidence': 0.1}
    assert client.post(f'/api/v1/sessions/{session_id}/identify-component', json={'media_id': m['id']}, headers=tech['h']).json()['box'] is None


def test_upload_validation(client, tech, session_id):
    ok = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('x.jpg', png(fmt='JPEG'), 'image/jpeg')}, headers=tech['h'])
    assert ok.status_code == 201 and ok.json()['mime_type'] == 'image/jpeg'
    lie = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('evil.png', b'<script>alert(1)</script>', 'image/png')}, headers=tech['h'])
    assert lie.status_code == 415
    big = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('b.png', b'\x89PNG' + b'0' * (9 * 1024 * 1024), 'image/png')}, headers=tech['h'])
    assert big.status_code == 413
    assert client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('x.png', png(), 'image/png')}).status_code == 401
    other = register(client)
    assert client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('x.png', png(), 'image/png')}, headers=other['h']).status_code == 404
    mid = ok.json()['id']
    assert client.get(f'/api/v1/media/{mid}', headers=tech['h']).headers['content-type'] == 'image/jpeg'
    assert client.get(f'/api/v1/media/{mid}', headers=other['h']).status_code == 404
