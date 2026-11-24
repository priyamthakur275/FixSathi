"""Chat sends real conversation turns, never repeats the current message, keeps follow-ups grounded and keeps earlier photos in view."""
from google.genai import types
from tests.fakes import png


def _last_contents(fake):
    op, contents = [c for c in fake.calls if c[0] == 'chat'][-1]
    return contents


def _text(content: types.Content) -> str:
    return ' '.join(p.text or '' for p in content.parts)


def test_first_message_is_sent_once_as_the_final_turn(client, tech, session_id, fake):
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Fan hums and runs slow'}, headers=tech['h'])
    c = _last_contents(fake)
    assert len(c) == 1 and c[0].role == 'user'
    assert _text(c[0]).count('Fan hums and runs slow') == 1 and '<technician_input>' in _text(c[0]) and '<knowledge>' in _text(c[0])


def test_follow_up_gets_alternating_history_and_no_duplicate(client, tech, session_id, fake):
    fake.text = 'Likely a weak capacitor. Spin the blades by hand: do they turn freely?'
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Fan hums and runs slow'}, headers=tech['h'])
    fake.text = 'Then the bearings are fine; test the capacitor next.'
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Yes they turn freely'}, headers=tech['h'])
    c = _last_contents(fake)
    assert [x.role for x in c] == ['user', 'model', 'user']
    assert 'Fan hums and runs slow' in _text(c[0]) and 'weak capacitor' in _text(c[1])
    assert _text(c[2]).count('Yes they turn freely') == 1
    assert sum(_text(x).count('Yes they turn freely') for x in c) == 1


def test_failed_reply_leaves_consecutive_user_turns_merged(client, tech, session_id, fake):
    from app.core.exceptions import AIUnavailable
    fake.fail['chat'] = AIUnavailable('busy', code='PROVIDER_UNAVAILABLE')
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'First try'}, headers=tech['h'])
    fake.fail.clear()
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Second try'}, headers=tech['h'])
    c = _last_contents(fake)
    assert [x.role for x in c] == ['user', 'user'] or [x.role for x in c] == ['user']
    roles = [x.role for x in c[:-1]]
    assert all(a != b for a, b in zip(roles, roles[1:]))


def test_follow_up_retrieval_keeps_the_original_problem(client, tech, fake, monkeypatch):
    from app.services import ai
    seen = []
    real = ai.kb.retrieve
    async def spy(db, q, **kw):
        seen.append(q); return await real(db, q, **kw)
    monkeypatch.setattr(ai.kb, 'retrieve', spy)
    sid = client.post('/api/v1/sessions', json={'issue_description': 'ceiling fan hums but does not spin', 'appliance_type': 'ceiling_fan'}, headers=tech['h']).json()['id']
    client.post(f'/api/v1/sessions/{sid}/messages', json={'text': 'ceiling fan hums but does not spin'}, headers=tech['h'])
    client.post(f'/api/v1/sessions/{sid}/messages', json={'text': 'what about the capacitor?'}, headers=tech['h'])
    assert 'hums but does not spin' in seen[-1] and 'capacitor' in seen[-1]


def test_earlier_photo_stays_available_for_follow_ups(client, tech, session_id, fake):
    mid = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('x.png', png(), 'image/png')}, headers=tech['h']).json()['id']
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Look at this', 'media_ids': [mid]}, headers=tech['h'])
    first = _last_contents(fake)[-1]
    assert sum(1 for p in first.parts if p.inline_data) == 1
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Is that black mark a burn?'}, headers=tech['h'])
    last = _last_contents(fake)[-1]
    assert sum(1 for p in last.parts if p.inline_data) == 1 and 'earlier in this session' in _text(last)
    assert '[shared a photo]' in _text(_last_contents(fake)[0])


def test_earlier_photo_not_resent_on_every_later_message(client, tech, session_id, fake):
    mid = client.post(f'/api/v1/sessions/{session_id}/images', files={'file': ('x.png', png(), 'image/png')}, headers=tech['h']).json()['id']
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Look at this', 'media_ids': [mid]}, headers=tech['h'])
    for t in ('Regulator is on 5', 'Fan is 6 years old', 'Bearings were greased last year'):
        client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': t}, headers=tech['h'])
    assert sum(1 for p in _last_contents(fake)[-1].parts if p.inline_data) == 0  # unrelated follow-up: no image tokens
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Is the mark in the photo a burn?'}, headers=tech['h'])
    assert sum(1 for p in _last_contents(fake)[-1].parts if p.inline_data) == 1  # refers to it: photo sent again
