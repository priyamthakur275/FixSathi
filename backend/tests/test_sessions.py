from tests.conftest import make_role, register


def test_create_get_list_patch(client, tech, session_id):
    r = client.get(f'/api/v1/sessions/{session_id}', headers=tech['h'])
    assert r.status_code == 200 and r.json()['status'] == 'active' and r.json()['reference'].startswith('FS-')
    assert client.get('/api/v1/sessions', headers=tech['h']).json()['total'] == 1
    p = client.patch(f'/api/v1/sessions/{session_id}', json={'title': 'Hall fan'}, headers=tech['h'])
    assert p.json()['title'] == 'Hall fan'


def test_appliance_guessed(client, tech):
    r = client.post('/api/v1/sessions', json={'issue_description': 'My split AC is not cooling'}, headers=tech['h'])
    assert r.json()['appliance_type'] == 'split_ac'


def test_cross_user_access_rejected(client, session_id):
    other = register(client, org='Acme Service')
    assert client.get(f'/api/v1/sessions/{session_id}', headers=other['h']).status_code == 404
    assert client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'hi'}, headers=other['h']).status_code == 404
    assert client.get('/api/v1/sessions', headers=other['h']).json()['total'] == 0


def test_manager_scoped_to_organisation(client, tech, session_id):
    m = register(client, org='Acme Service'); make_role(m['user']['id'], 'manager')
    outsider = register(client, org='Other Co'); make_role(outsider['user']['id'], 'manager')
    assert client.get(f'/api/v1/sessions/{session_id}', headers=m['h']).status_code == 200
    assert client.get(f'/api/v1/sessions/{session_id}', headers=outsider['h']).status_code == 404
    # managers can read but not act on a technician's session
    assert client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json={'power_off_confirmed': True, 'tester_checked': True}, headers=m['h']).status_code == 403


def test_invalid_transition_and_closed_session(client, tech, session_id):
    assert client.post(f'/api/v1/sessions/{session_id}/cancel', headers=tech['h']).json()['status'] == 'cancelled'
    r = client.patch(f'/api/v1/sessions/{session_id}', json={'status': 'active'}, headers=tech['h'])
    assert r.status_code == 409 and r.json()['error']['code'] == 'SESSION_CLOSED'
    assert client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'hi'}, headers=tech['h']).json()['error']['code'] == 'SESSION_CLOSED'


def test_messages_persist_without_ai(client, tech, session_id):
    r = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Fan hums'}, headers=tech['h'])
    assert r.status_code == 201
    body = r.json()
    assert body['ai_status'] == 'unavailable' and body['ai_error']['code'] == 'AI_NOT_CONFIGURED' and body['assistant_message'] is None
    msgs = client.get(f'/api/v1/sessions/{session_id}/messages', headers=tech['h']).json()
    assert [m['message'] for m in msgs['items']] == ['Fan hums']


def test_messages_with_ai(client, tech, session_id, fake):
    r = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Fan hums'}, headers=tech['h']).json()
    assert r['ai_status'] == 'ok' and r['assistant_message']['meta']['ai_generated'] is True
    assert client.get(f'/api/v1/sessions/{session_id}/messages', headers=tech['h']).json()['total'] == 2
    # technician text reaches the model wrapped as data, not as instructions
    assert any('<technician_input>' in str(c) for _, c in fake.calls)


def test_pagination_validation(client, tech):
    assert client.get('/api/v1/sessions?limit=0', headers=tech['h']).status_code == 422
    assert client.get('/api/v1/sessions/not-a-uuid', headers=tech['h']).status_code == 422

def test_delete_own_session(client, tech, session_id):
    assert client.delete(f'/api/v1/sessions/{session_id}', headers=tech['h']).status_code == 204
    assert client.get(f'/api/v1/sessions/{session_id}', headers=tech['h']).status_code == 404
    assert client.get('/api/v1/sessions', headers=tech['h']).json()['total'] == 0


def test_delete_other_users_session_rejected(client, session_id):
    other = register(client, org='Acme Service')
    assert client.delete(f'/api/v1/sessions/{session_id}', headers=other['h']).status_code == 404
