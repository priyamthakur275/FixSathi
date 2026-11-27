"""Server-screened SSE streaming tests."""
import json
from starlette.requests import Request
from app.core.exceptions import AIError
from app.db.models import AIUsage, SafetyEvent
from app.db.session import SessionLocal
from app.services.safety import LOCK_NOTE, WITHHELD_MARK
from tests.test_dataset_pipeline import _ingest, rec


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in raw.replace('\r\n', '\n').split('\n\n'):
        if not block.strip():
            continue
        ev = 'message'
        lines: list[str] = []
        for line in block.split('\n'):
            if line.startswith('event:'):
                ev = line[6:].strip()
            elif line.startswith('data:'):
                lines.append(line[5:].lstrip())
        if lines:
            events.append((ev, json.loads('\n'.join(lines))))
    return events


def test_stream_withholds_power_sensitive_step_while_locked(client, tech, session_id, fake):
    fake.stream_chunks = [
        'Fan may have a weak capacitor. ',
        '1. Open the ',
        'canopy and touch the ',
        'capacitor wires.\n',
        'Check blades visually for wobble.',
    ]
    with client.stream('POST', f'/api/v1/sessions/{session_id}/messages/stream', json={'text': 'fan hums'}, headers=tech['h']) as r:
        assert r.status_code == 200
        assert 'text/event-stream' in r.headers['content-type']
        raw = r.read().decode('utf-8')

    events = _parse_sse(raw)
    deltas = [p['text'] for ev, p in events if ev == 'delta']
    joined = ''.join(deltas)
    for d in deltas:
        assert 'open the canopy' not in d.lower()
        assert 'touch the capacitor wires' not in d.lower()
    assert 'open the canopy' not in joined.lower()
    assert WITHHELD_MARK in joined
    assert LOCK_NOTE in joined
    assert 'Fan may have a weak capacitor.' in joined
    assert 'Check blades visually for wobble.' in joined

    done = [p for ev, p in events if ev == 'done'][0]['assistant_message']
    assert done['meta']['safety_withheld'] >= 1
    assert joined == done['message']

    with SessionLocal() as db:
        blocks = db.query(SafetyEvent).filter(SafetyEvent.blocked.is_(True)).all()
        assert len(blocks) >= 1


def test_stream_allows_power_sensitive_step_after_isolation_confirmed(client, tech, session_id, fake):
    client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json={'power_off_confirmed': True, 'tester_checked': True}, headers=tech['h'])
    fake.stream_chunks = [
        '1. Open the ',
        'canopy and touch the ',
        'capacitor wires.\n',
        'Measure capacitance.',
    ]
    with client.stream('POST', f'/api/v1/sessions/{session_id}/messages/stream', json={'text': 'fan hums'}, headers=tech['h']) as r:
        assert r.status_code == 200
        events = _parse_sse(r.read().decode('utf-8'))

    joined = ''.join(p['text'] for ev, p in events if ev == 'delta')
    assert 'Open the canopy and touch the capacitor wires.' in joined
    assert WITHHELD_MARK not in joined
    assert LOCK_NOTE not in joined


def test_stream_final_saved_message_matches_deltas_seen_by_user(client, tech, session_id, fake):
    _ingest(rec(record_id='t:fan1', appliance_category='ceiling_fan', reported_symptoms=['fan hums'], possible_faults=['Weak run capacitor']))
    fake.stream_chunks = [
        'Likely cause is a weak capacitor [t:fan1, bogus:fake99]. ',
        'Listen closely ',
        'for bearing hum.',
    ]
    with client.stream('POST', f'/api/v1/sessions/{session_id}/messages/stream', json={'text': 'fan hums'}, headers=tech['h']) as r:
        assert r.status_code == 200
        events = _parse_sse(r.read().decode('utf-8'))

    deltas = [p['text'] for ev, p in events if ev == 'delta']
    joined = ''.join(deltas)
    done_msg = [p for ev, p in events if ev == 'done'][0]['assistant_message']
    saved = [m for m in client.get(f'/api/v1/sessions/{session_id}/messages', headers=tech['h']).json()['items'] if m['role'] == 'assistant']

    assert len(saved) == 1
    assert joined == done_msg['message'] == saved[0]['message']
    assert '[t:fan1]' in joined
    assert 'bogus:fake99' not in joined


def test_stream_dropped_connection_leaves_no_half_saved_message(client, tech, session_id, fake, monkeypatch):
    fake.stream_chunks = ['First safe sentence. ', 'Second sentence. ', 'Third sentence.']
    checks = {'n': 0}

    async def fake_is_disconnected(self):
        checks['n'] += 1
        return checks['n'] >= 2  # drop after first chunk check

    monkeypatch.setattr(Request, 'is_disconnected', fake_is_disconnected)
    with client.stream('POST', f'/api/v1/sessions/{session_id}/messages/stream', json={'text': 'fan hums'}, headers=tech['h']) as r:
        assert r.status_code == 200
        events = _parse_sse(r.read().decode('utf-8'))

    assert not any(ev == 'done' for ev, _ in events)
    items = client.get(f'/api/v1/sessions/{session_id}/messages', headers=tech['h']).json()['items']
    assert [m['role'] for m in items] == ['user']


def test_stream_gemini_error_mid_stream_emits_clean_error_and_no_partial_message(client, tech, session_id, fake):
    fake.stream_chunks = ['First safe sentence. ', 'Second sentence. ']
    fake.stream_fail_after = (1, AIError('Upstream stream reset', code='PROVIDER_UNAVAILABLE'))

    with client.stream('POST', f'/api/v1/sessions/{session_id}/messages/stream', json={'text': 'fan hums'}, headers=tech['h']) as r:
        assert r.status_code == 200
        events = _parse_sse(r.read().decode('utf-8'))

    err_events = [p for ev, p in events if ev == 'error']
    assert len(err_events) == 1
    assert err_events[0]['ai_error']['code'] == 'PROVIDER_UNAVAILABLE'
    assert not any(ev == 'done' for ev, _ in events)

    items = client.get(f'/api/v1/sessions/{session_id}/messages', headers=tech['h']).json()['items']
    assert [m['role'] for m in items] == ['user']
    with SessionLocal() as db:
        rows = db.query(AIUsage).filter(AIUsage.operation == 'chat').all()
        assert any(row.ok is False and row.error_code == 'PROVIDER_UNAVAILABLE' for row in rows)
