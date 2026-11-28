"""Gemini Vision nameplate and error-display reader tests."""
import base64, io, logging, uuid
from PIL import Image
from app.core.exceptions import AIError
from app.core.logging import JsonFormatter
from app.db.models import AIUsage, Media
from app.db.session import SessionLocal
from tests.conftest import make_role, register
from tests.fakes import DIAG, png
from tests.test_dataset_pipeline import _ingest, rec


def _upload_photo(client, headers, session_id):
    r = client.post(f'/api/v1/sessions/{session_id}/files?source=capture', files={'file': ('label.png', png(), 'image/png')}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()['id']


def test_read_nameplate_extracts_fields_feeds_retrieval_and_grounds_diagnosis(client, tech, fake):
    _ingest(rec(
        record_id='t:lgch38',
        appliance_category='split_ac',
        appliance_brand='LG',
        appliance_model='LS-Q18YNZA',
        error_code='CH38',
        reported_symptoms=['CH38 error code on indoor display', 'poor cooling'],
        possible_faults=['Low refrigerant charge'],
        diagnostic_procedure=['Check indoor filter', 'Inspect flare nuts after isolating supply'],
    ))
    sid = client.post('/api/v1/sessions', json={'issue_description': 'unit not cooling', 'appliance_type': 'unknown'}, headers=tech['h']).json()['id']
    mid = _upload_photo(client, tech['h'], sid)

    fake.json['nameplate'] = {
        'readable': True,
        'appliance_type': 'split_ac',
        'brand': 'lg',
        'model': 'LS-Q18YNZA',
        'error_code': 'ch 38',
        'serial_number': '504INXX999',
        'raw_text': 'LG INVERTER V MODEL LS-Q18YNZA ERROR CH 38',
        'confidence': 0.91,
        'notes': None,
    }
    res = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': mid}, headers=tech['h'])
    assert res.status_code == 200, res.text
    d = res.json()
    assert d['status'] == 'ok' and d['ai_error'] is None
    assert d['extracted']['brand'] == 'LG'
    assert d['extracted']['model'] == 'LS-Q18YNZA'
    assert d['extracted']['error_code'] == 'CH38'
    assert d['extracted']['verified_by_technician'] is False
    assert d['retrieval']['coverage'] == 'grounded'
    assert d['retrieval']['error_codes_found'] == ['CH38']
    assert d['retrieval']['hits'][0]['record_id'] == 't:lgch38'
    assert 'repair_steps' not in d['retrieval']['hits'][0]

    # Persisted on session and grounds subsequent diagnosis retrieval.
    sess = client.get(f'/api/v1/sessions/{sid}', headers=tech['h']).json()
    assert sess['appliance_type'] == 'split_ac'
    assert sess['nameplate']['error_code'] == 'CH38'

    fake.json['diagnosis'] = {**DIAG, 'appliance_type': 'split_ac', 'possible_faults': [
        {'fault': 'Low refrigerant', 'explanation': 'CH38 match', 'confidence': 0.85, 'evidence': [], 'status': 'supported_by_records', 'record_ids': ['t:lgch38']},
    ]}
    dr = client.post(f'/api/v1/sessions/{sid}/diagnose', json={}, headers=tech['h'])
    assert dr.status_code == 201
    assert any(src['record_id'] == 't:lgch38' for src in dr.json()['sources'])
    diag_call = next(c for op, c in fake.calls if op == 'diagnosis')
    joined = ' '.join(str(x) for x in diag_call)
    assert 't:lgch38' in joined and 'CH38' in joined


def test_patch_nameplate_lets_technician_correct_and_updates_retrieval(client, tech, fake):
    _ingest(rec(
        record_id='t:lgch38',
        appliance_category='split_ac',
        appliance_brand='LG',
        error_code='CH38',
        reported_symptoms=['CH38 error'],
        possible_faults=['Low refrigerant'],
    ))
    _ingest(rec(
        record_id='t:lgch05',
        appliance_category='split_ac',
        appliance_brand='LG',
        error_code='CH05',
        reported_symptoms=['CH05 communication fault'],
        possible_faults=['Indoor-outdoor signal wiring fault'],
    ))
    sid = client.post('/api/v1/sessions', json={'issue_description': 'ac blinking error', 'appliance_type': 'split_ac'}, headers=tech['h']).json()['id']
    mid = _upload_photo(client, tech['h'], sid)

    fake.json['nameplate'] = {
        'readable': True, 'appliance_type': 'split_ac', 'brand': 'LG', 'model': 'LS-Q18',
        'error_code': 'CH38', 'raw_text': 'CH38', 'confidence': 0.65,
    }
    r1 = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': mid}, headers=tech['h']).json()
    assert r1['retrieval']['hits'][0]['record_id'] == 't:lgch38'

    # Technician corrects misread error code CH38 -> CH05.
    r2 = client.patch(f'/api/v1/sessions/{sid}/nameplate', json={'brand': 'LG', 'model': 'LS-Q18', 'error_code': 'ch-05', 'appliance_type': 'split_ac'}, headers=tech['h'])
    assert r2.status_code == 200, r2.text
    d = r2.json()
    assert d['status'] == 'ok'
    assert d['extracted']['error_code'] == 'CH05'
    assert d['extracted']['verified_by_technician'] is True
    assert d['retrieval']['hits'][0]['record_id'] == 't:lgch05'


def test_read_nameplate_graceful_fallback_when_gemini_unconfigured_never_fakes(client, tech):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'display shows error', 'appliance_type': 'split_ac'}, headers=tech['h']).json()['id']
    mid = _upload_photo(client, tech['h'], sid)

    r = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': mid}, headers=tech['h'])
    assert r.status_code == 200
    d = r.json()
    assert d['status'] == 'unavailable'
    assert d['extracted'] is None
    assert d['retrieval'] is None
    assert d['ai_error']['code'] == 'AI_NOT_CONFIGURED'

    sess = client.get(f'/api/v1/sessions/{sid}', headers=tech['h']).json()
    assert sess['nameplate'] is None


def test_read_nameplate_graceful_fallback_when_gemini_fails_never_fakes(client, tech, fake):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'rating label unreadable', 'appliance_type': 'washing_machine'}, headers=tech['h']).json()['id']
    mid = _upload_photo(client, tech['h'], sid)
    fake.fail['nameplate'] = AIError('Vision temporarily unavailable', code='AI_ERROR')

    r = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': mid}, headers=tech['h'])
    assert r.status_code == 200
    d = r.json()
    assert d['status'] == 'error'
    assert d['extracted'] is None
    assert d['ai_error']['code'] == 'AI_ERROR'

    with SessionLocal() as db:
        rows = db.query(AIUsage).filter(AIUsage.operation == 'nameplate').all()
        assert len(rows) == 1 and rows[0].ok is False and rows[0].error_code == 'AI_ERROR'


def test_read_nameplate_enforces_ownership_and_image_type(client, tech, fake):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'test', 'appliance_type': 'split_ac'}, headers=tech['h']).json()['id']
    mid = _upload_photo(client, tech['h'], sid)
    other = register(client, org='Other Co')

    assert client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': mid}, headers=other['h']).status_code in (403, 404)
    assert client.patch(f'/api/v1/sessions/{sid}/nameplate', json={'brand': 'LG'}, headers=other['h']).status_code in (403, 404)

    doc_r = client.post(f'/api/v1/sessions/{sid}/files?source=upload', files={'file': ('notes.txt', b'error code list', 'text/plain')}, headers=tech['h'])
    assert doc_r.status_code == 201, doc_r.text
    bad = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': doc_r.json()['id']}, headers=tech['h'])
    assert bad.status_code == 400 and bad.json()['error']['code'] == 'NOT_AN_IMAGE'


def test_read_nameplate_forbids_same_org_manager_ownership(client, tech, fake):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'ac error', 'appliance_type': 'split_ac'}, headers=tech['h']).json()['id']
    mid = _upload_photo(client, tech['h'], sid)
    mgr = register(client, org='Acme Service')
    make_role(mgr['user']['id'], 'manager')

    assert client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': mid}, headers=mgr['h']).status_code == 403
    assert client.patch(f'/api/v1/sessions/{sid}/nameplate', json={'brand': 'LG'}, headers=mgr['h']).status_code == 403


def test_read_nameplate_enforces_mime_and_8mb_limit_and_allows_jpeg_webp(client, tech, fake):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'ac error', 'appliance_type': 'split_ac'}, headers=tech['h']).json()['id']
    fake.json['nameplate'] = {'readable': True, 'appliance_type': 'split_ac', 'brand': 'LG', 'model': 'X1', 'error_code': 'CH38', 'raw_text': 'CH38', 'confidence': 0.9}

    for ext, fmt, mime in (('label.jpg', 'JPEG', 'image/jpeg'), ('label.webp', 'WEBP', 'image/webp')):
        up = client.post(f'/api/v1/sessions/{sid}/files?source=upload', files={'file': (ext, png(fmt=fmt), mime)}, headers=tech['h'])
        assert up.status_code == 201, up.text
        res = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': up.json()['id']}, headers=tech['h'])
        assert res.status_code == 200 and res.json()['status'] == 'ok'

    # Even if a legacy/unexpected image MIME or oversized row exists in DB, read_nameplate rejects it.
    uid = tech['user']['id']
    with SessionLocal() as db:
        bad_mime = Media(session_id=uuid.UUID(sid), uploaded_by=uuid.UUID(uid), kind='upload', storage_key='fake/key.gif', mime_type='image/gif', size_bytes=128)
        too_big = Media(session_id=uuid.UUID(sid), uploaded_by=uuid.UUID(uid), kind='upload', storage_key='fake/big.png', mime_type='image/png', size_bytes=(8 * 1024 * 1024) + 1)
        db.add_all([bad_mime, too_big])
        db.commit()
        bad_id, big_id = str(bad_mime.id), str(too_big.id)

    r_gif = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': bad_id}, headers=tech['h'])
    assert r_gif.status_code == 415 and r_gif.json()['error']['code'] == 'UNSUPPORTED_MEDIA_TYPE'

    r_big = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': big_id}, headers=tech['h'])
    assert r_big.status_code == 413 and r_big.json()['error']['code'] == 'UPLOAD_TOO_LARGE'


def test_read_nameplate_never_logs_image_bytes_or_api_key(client, tech, fake, caplog):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'ac error', 'appliance_type': 'split_ac'}, headers=tech['h']).json()['id']
    buf = io.BytesIO()
    Image.new('RGB', (40, 40), (12, 34, 56)).save(buf, 'PNG')
    raw_bytes = buf.getvalue() + b'SECRET_IMAGE_MARKER_987654'
    up = client.post(f'/api/v1/sessions/{sid}/files?source=upload', files={'file': ('label.png', raw_bytes, 'image/png')}, headers=tech['h'])
    assert up.status_code == 201
    mid = up.json()['id']

    fake_key = 'AIzaSyTestFakeKey1234567890abcdef'
    fake.json['nameplate'] = {'readable': True, 'appliance_type': 'split_ac', 'brand': 'LG', 'model': 'LS1', 'error_code': 'CH38', 'raw_text': 'CH38', 'confidence': 0.9}

    caplog.set_level(logging.DEBUG)
    r_ok = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': mid}, headers=tech['h'])
    assert r_ok.status_code == 200

    fake.fail['nameplate'] = AIError(f'Key failed: {fake_key}', code='AI_ERROR')
    r_err = client.post(f'/api/v1/sessions/{sid}/read-nameplate', json={'media_id': mid}, headers=tech['h'])
    assert r_err.status_code == 200

    fmt = JsonFormatter()
    formatted = '\n'.join(fmt.format(rec_) for rec_ in caplog.records)
    raw_lines = '\n'.join(rec_.getMessage() for rec_ in caplog.records)
    assert 'SECRET_IMAGE_MARKER_987654' not in formatted and 'SECRET_IMAGE_MARKER_987654' not in raw_lines
    b64_chunk = base64.b64encode(b'SECRET_IMAGE_MARKER_987654').decode()
    assert b64_chunk not in formatted
    assert fake_key not in formatted
    assert 'data:image' not in formatted
