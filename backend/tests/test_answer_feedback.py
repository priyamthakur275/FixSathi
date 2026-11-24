"""Thumbs up / down on individual AI answers, and the counts the manager dashboard shows."""
import uuid
from tests.conftest import make_role, register


def _answer(client, tech, session_id):
    r = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Fan hums but does not spin'}, headers=tech['h']).json()
    return r['assistant_message'], r['user_message']


def test_rate_answer_and_clear(client, tech, session_id, fake):
    a, _ = _answer(client, tech, session_id)
    url = f'/api/v1/sessions/{session_id}/messages/{a["id"]}/feedback'
    r = client.put(url, json={'helpful': False, 'comment': '  capacitor was fine, it was the winding  '}, headers=tech['h'])
    assert r.status_code == 200
    fb = r.json()['meta']['feedback']
    assert fb['helpful'] is False and fb['comment'] == 'capacitor was fine, it was the winding' and fb['at']
    # the rating is saved with the conversation
    items = client.get(f'/api/v1/sessions/{session_id}/messages', headers=tech['h']).json()['items']
    assert next(m for m in items if m['id'] == a['id'])['meta']['feedback']['helpful'] is False
    # changing and clearing it
    up = client.put(url, json={'helpful': True}, headers=tech['h']).json()['meta']['feedback']
    assert up['helpful'] is True and up['comment'] is None
    cleared = client.put(url, json={'helpful': None}, headers=tech['h']).json()
    assert 'feedback' not in cleared['meta'] and cleared['meta']['ai_generated'] is True


def test_only_assistant_answers_can_be_rated(client, tech, session_id, fake):
    _, user_msg = _answer(client, tech, session_id)
    r = client.put(f'/api/v1/sessions/{session_id}/messages/{user_msg["id"]}/feedback', json={'helpful': True}, headers=tech['h'])
    assert r.status_code == 404
    r = client.put(f'/api/v1/sessions/{session_id}/messages/{uuid.uuid4()}/feedback', json={'helpful': True}, headers=tech['h'])
    assert r.status_code == 404


def test_other_users_cannot_rate(client, tech, session_id, fake):
    a, _ = _answer(client, tech, session_id)
    url = f'/api/v1/sessions/{session_id}/messages/{a["id"]}/feedback'
    outsider = register(client, org='Other Co')
    assert client.put(url, json={'helpful': True}, headers=outsider['h']).status_code == 404
    manager = register(client, org='Acme Service'); make_role(manager['user']['id'], 'manager')
    assert client.put(url, json={'helpful': True}, headers=manager['h']).status_code == 403


def test_comment_length_limited(client, tech, session_id, fake):
    a, _ = _answer(client, tech, session_id)
    r = client.put(f'/api/v1/sessions/{session_id}/messages/{a["id"]}/feedback', json={'helpful': False, 'comment': 'x' * 501}, headers=tech['h'])
    assert r.status_code == 422


def test_dashboard_counts_answer_feedback(client, tech, session_id, fake):
    manager = register(client, org='Acme Service'); make_role(manager['user']['id'], 'manager')
    before = client.get('/api/v1/dashboard/overview', headers=manager['h']).json()
    assert before['answers_rated'] == 0 and before['answer_helpful_rate'] is None
    ids = [_answer(client, tech, session_id)[0]['id'] for _ in range(3)]
    for mid, ok in zip(ids, (True, True, False)):
        client.put(f'/api/v1/sessions/{session_id}/messages/{mid}/feedback', json={'helpful': ok}, headers=tech['h'])
    o = client.get('/api/v1/dashboard/overview', headers=manager['h']).json()
    assert o['answers_rated'] == 3 and o['answers_helpful'] == 2 and o['answer_helpful_rate'] == 0.667
