"""Unit & integration tests for the Red-Team Challenger verifier:
agree, disagree (+ citation filtering + step gate), timeout/error non-blocking fallback, and safety-lock invariant."""
from app.core.exceptions import AIError
from tests.fakes import DIAG, STEPS


def _diagnose_payload(client, tech, session_id):
    r = client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    assert r.status_code == 201, r.text
    return r.json()


def test_challenger_agrees_allows_steps_and_logs_audit(client, tech, session_id, fake):
    fake.json = {
        'diagnosis': DIAG,
        'challenger': {
            'agrees': True,
            'objections': [],
            'missed_checks': [],
            'safety_concerns': [],
            'revised_confidence': 0.58,
        },
        'guidance': STEPS,
    }
    d = _diagnose_payload(client, tech, session_id)
    ch = d['challenger']
    assert ch['status'] == 'ok'
    assert ch['agrees'] is True
    assert ch['confidence_before'] == 0.6
    assert ch['revised_confidence'] == 0.58
    assert ch['model_identifier'] == 'fake-agent'
    assert isinstance(ch['latency_ms'], int)

    steps = client.post(f'/api/v1/sessions/{session_id}/steps/generate', headers=tech['h'])
    assert steps.status_code == 201


def test_challenger_disagree_blocks_steps_until_checked_and_filters_unknown_citations(client, tech, session_id, fake):
    fake.json = {
        'diagnosis': DIAG,
        'challenger': {
            'agrees': False,
            'objections': [
                {
                    'claim': 'Could be regulator or supply rather than motor windings.',
                    'claim_hi': 'यह मोटर वाइंडिंग की जगह रेगुलेटर की खराबी भी हो सकती है।',
                    'why': 'Technician reported humming without measuring supply voltage.',
                    'why_hi': 'टेक्नीशियन ने सिर्फ हमिंग बताई है, सप्लाई वोल्टेज चेक नहीं हुआ।',
                    'evidence_id': 'mfr:nonexistent-fake-id',
                },
                {
                    'claim': 'Only humming was stated by technician.',
                    'claim_hi': 'टेक्नीशियन ने केवल धीमे चलने और हमिंग की बात कही है।',
                    'why': 'No burnt smell mentioned.',
                    'why_hi': 'जलने की गंध का जिक्र नहीं है।',
                    'evidence_id': 'technician_input',
                },
            ],
            'missed_checks': ['Spin blades gently by hand when MCB is off'],
            'safety_concerns': [],
            'revised_confidence': 0.42,
        },
        'guidance': STEPS,
    }
    d = _diagnose_payload(client, tech, session_id)
    ch = d['challenger']
    assert ch['status'] == 'ok' and ch['agrees'] is False
    assert d['challenger_checked_at'] is None
    assert ch['objections'][0]['evidence_id'] is None  # hallucinated citation stripped
    assert ch['objections'][1]['evidence_id'] == 'technician_input'

    blocked = client.post(f'/api/v1/sessions/{session_id}/steps/generate', headers=tech['h'])
    assert blocked.status_code == 409
    assert blocked.json()['error']['code'] == 'CHALLENGER_CHECK_REQUIRED'

    ack = client.post(f'/api/v1/sessions/{session_id}/diagnosis/challenger-check', headers=tech['h'])
    assert ack.status_code == 200
    assert ack.json()['challenger_checked_at'] is not None

    allowed = client.post(f'/api/v1/sessions/{session_id}/steps/generate', headers=tech['h'])
    assert allowed.status_code == 201


def test_challenger_timeout_or_error_fails_open_and_never_blocks_diagnosis(client, tech, session_id, fake):
    fake.json = {'diagnosis': DIAG, 'guidance': STEPS}
    fake.fail = {'challenger': AIError('Timed out after 5s', code='AI_TIMEOUT', status=504)}

    d = _diagnose_payload(client, tech, session_id)
    ch = d['challenger']
    assert ch['status'] == 'unavailable'
    assert ch['agrees'] is None
    assert ch['error_code'] == 'AI_TIMEOUT'

    # Must not block repair steps when challenger is unavailable
    steps = client.post(f'/api/v1/sessions/{session_id}/steps/generate', headers=tech['h'])
    assert steps.status_code == 201


def test_challenger_safety_concern_forces_relock_and_never_weakens_safety_lock(client, tech, session_id, fake):
    # Unlock safety first, then run diagnosis where challenger flags a safety concern -> must force relock
    conf = client.post(f'/api/v1/sessions/{session_id}/safety/confirm',
                       json={'power_off_confirmed': True, 'tester_checked': True}, headers=tech['h'])
    assert conf.status_code == 200 and conf.json()['unlocked'] is True

    fake.json = {
        'diagnosis': DIAG,
        'challenger': {
            'agrees': False,
            'objections': [{'claim': 'Capacitor can hold charge even after switch-off', 'claim_hi': 'स्विच ऑफ के बाद भी कैपेसिटर में चार्ज रह सकता है', 'why': 'Discharge check omitted', 'why_hi': 'डिस्चार्ज जांच छूट गई', 'evidence_id': 'technician_input'}],
            'missed_checks': [],
            'safety_concerns': ['Confirm MCB off and verify terminals are discharged before touching capacitor'],
            'revised_confidence': 0.5,
        },
    }
    d = _diagnose_payload(client, tech, session_id)
    assert 'Confirm MCB off and verify terminals are discharged before touching capacitor' in d['safety_requirements']

    sf = client.get(f'/api/v1/sessions/{session_id}/safety', headers=tech['h'])
    assert sf.status_code == 200
    assert sf.json()['unlocked'] is False

    ev = client.get(f'/api/v1/sessions/{session_id}/safety/events', headers=tech['h'])
    assert any(x['actor'] == 'challenger' and x['blocked'] and x['reason'] == 'CHALLENGER_SAFETY_CONCERN' for x in ev.json())
