"""Tests for Customer Safety Receipt (/receipt/<id>): unguessable token, zero customer PII, expiry, QR SVG, ownership."""
from datetime import timedelta
from app.db.base import utcnow
from app.db.models import CustomerReceipt
from app.db.session import SessionLocal
from tests.conftest import register


def test_create_and_fetch_public_safety_receipt_with_qr_and_no_pii(client, tech, session_id):
    # Put a phone number and email inside the session issue description to verify scrubbing
    r_upd = client.patch(
        f'/api/v1/sessions/{session_id}',
        json={'issue_description': 'Fan hums slowly; customer Rajesh +91 9876543210 email rajesh@example.com'},
        headers=tech['h'],
    )
    assert r_upd.status_code == 200

    res = client.post(f'/api/v1/sessions/{session_id}/receipt', headers=tech['h'])
    assert res.status_code == 201, res.text
    body = res.json()
    token = body['token']
    assert len(token) >= 24
    assert body['url'] == f'/receipt/{token}'
    assert body['qr_url'] == f'/api/v1/receipts/{token}/qr'

    # Public fetch without any Authorization header
    pub = client.get(f'/api/v1/receipts/{token}')
    assert pub.status_code == 200
    rc = pub.json()['receipt']
    assert rc['technician_name'] == 'Test Tech'
    assert rc['appliance_hi'] == 'सीलिंग फैन'
    assert rc['appliance_en'] == 'Ceiling fan'
    assert '9876543210' not in rc['issue']
    assert 'rajesh@example.com' not in rc['issue']
    assert rc['safety_status']['unlocked'] is False

    # Public QR SVG
    qr = client.get(f'/api/v1/receipts/{token}/qr')
    assert qr.status_code == 200
    assert qr.headers['content-type'].startswith('image/svg+xml')
    assert '<svg' in qr.text


def test_receipt_expiry_and_unknown_tokens(client, tech, session_id):
    res = client.post(f'/api/v1/sessions/{session_id}/receipt', headers=tech['h'])
    assert res.status_code == 201
    token = res.json()['token']

    with SessionLocal() as db:
        row = db.get(CustomerReceipt, token)
        assert row is not None
        row.expires_at = utcnow() - timedelta(minutes=5)
        db.commit()

    exp = client.get(f'/api/v1/receipts/{token}')
    assert exp.status_code == 410
    assert exp.json()['error']['code'] == 'RECEIPT_EXPIRED'

    exp_qr = client.get(f'/api/v1/receipts/{token}/qr')
    assert exp_qr.status_code == 410

    missing = client.get('/api/v1/receipts/nonexistent-token-1234567890')
    assert missing.status_code == 404


def test_other_technician_cannot_mint_receipt(client, tech, session_id):
    other = register(client, name='Other Tech')
    res = client.post(f'/api/v1/sessions/{session_id}/receipt', headers=other['h'])
    assert res.status_code in (403, 404)
