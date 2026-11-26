from tests.conftest import make_role, register


def test_report_never_marks_unperformed_steps(client, tech, session_id, fake):
    client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    s1, s2 = client.post(f'/api/v1/sessions/{session_id}/steps/generate', headers=tech['h']).json()
    client.post(f"/api/v1/sessions/{session_id}/steps/{s1['id']}/complete", headers=tech['h'])
    r = client.post(f'/api/v1/sessions/{session_id}/reports', json={'outcome': 'not_resolved', 'notes': 'part not in stock'}, headers=tech['h'])
    assert r.status_code == 201, r.text
    d = r.json()
    assert d['resolution_status'] == 'not_resolved'
    assert [x['title'] for x in d['data']['steps_performed']] == ['Observe']
    assert [x['title'] for x in d['data']['steps_not_performed']] == ['Open canopy']
    assert d['data']['resolution']['first_time_fix'] is None
    assert 'cannot measure voltage' in d['data']['safety']['disclaimer']
    assert client.post(f'/api/v1/sessions/{session_id}/reports', json={'outcome': 'resolved'}, headers=tech['h']).status_code == 409
    assert client.get(f"/api/v1/reports/{d['id']}", headers=tech['h']).status_code == 200
    assert client.get('/api/v1/reports', headers=tech['h']).json()['total'] == 1
    other = register(client)
    assert client.get(f"/api/v1/reports/{d['id']}", headers=other['h']).status_code == 404


def test_feedback_and_escalation(client, tech, session_id):
    assert client.post(f'/api/v1/sessions/{session_id}/feedback', json={'rating': 6}, headers=tech['h']).status_code == 422
    assert client.post(f'/api/v1/sessions/{session_id}/feedback', json={'rating': 4, 'guidance_correct': True}, headers=tech['h']).status_code == 201
    e = client.post(f'/api/v1/sessions/{session_id}/escalate', json={'reason': 'Burnt smell from canopy'}, headers=tech['h'])
    assert e.status_code == 201 and client.get(f'/api/v1/sessions/{session_id}', headers=tech['h']).json()['status'] == 'escalated'
    assert client.post(f'/api/v1/sessions/{session_id}/escalate', json={'reason': 'again'}, headers=tech['h']).status_code == 409
    assert client.patch(f"/api/v1/escalations/{e.json()['id']}", json={'status': 'resolved'}, headers=tech['h']).status_code == 403
    m = register(client, org='Acme Service'); make_role(m['user']['id'], 'manager')
    assert len(client.get('/api/v1/escalations', headers=m['h']).json()) == 1
    r = client.patch(f"/api/v1/escalations/{e.json()['id']}", json={'status': 'resolved', 'resolution_notes': 'Replace wiring'}, headers=m['h'])
    assert r.json()['status'] == 'resolved'
    assert client.get(f'/api/v1/sessions/{session_id}', headers=tech['h']).json()['status'] == 'active'


def test_dashboard_real_data_and_roles(client, tech, session_id, fake):
    assert client.get('/api/v1/dashboard/overview', headers=tech['h']).status_code == 403
    m = register(client, org='Acme Service'); make_role(m['user']['id'], 'manager')
    o = client.get('/api/v1/dashboard/overview', headers=m['h']).json()
    assert o['total_sessions'] == 1 and o['active'] == 1 and o['first_time_fix_rate'] is None and o['ai_cost_per_repair'] is None
    assert o['funnel'] == {'sessions': 1, 'diagnosed': 0, 'isolated': 0, 'fixed_first_time': 0}
    client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json={'power_off_confirmed': True, 'tester_checked': True}, headers=tech['h'])
    client.post(f'/api/v1/sessions/{session_id}/reports', json={'outcome': 'resolved', 'first_time_fix': True}, headers=tech['h'])
    o = client.get('/api/v1/dashboard/overview', headers=m['h']).json()
    assert o['completed'] == 1 and o['first_time_fix_rate'] == 1.0 and o['first_time_fix_sample'] == 1
    assert o['funnel'] == {'sessions': 1, 'diagnosed': 1, 'isolated': 1, 'fixed_first_time': 1}
    t = client.get('/api/v1/dashboard/repairs', headers=m['h']).json()
    assert len(t) == 7 and sum(x['sessions'] for x in t) == 1
    assert client.get('/api/v1/dashboard/technicians', headers=m['h']).json()[0]['sessions'] == 1
    outsider = register(client, org='Other'); make_role(outsider['user']['id'], 'manager')
    assert client.get('/api/v1/dashboard/overview', headers=outsider['h']).json()['total_sessions'] == 0


def test_similar_repairs_keyword_fallback_and_scope(client, tech, session_id):
    client.post(f'/api/v1/sessions/{session_id}/reports', json={'outcome': 'resolved', 'first_time_fix': True}, headers=tech['h'])
    r = client.get('/api/v1/similar-repairs?q=fan+slow+hum', headers=tech['h']).json()
    assert r['mode'] == 'keyword' and r['fallback_reason']
    assert any(x['source_type'] == 'session' for x in r['results']) and any(x['source_type'] == 'knowledge' for x in r['results'])
    other = register(client)
    r2 = client.get('/api/v1/similar-repairs?q=fan+slow+hum', headers=other['h']).json()
    assert not any(x['source_type'] == 'session' for x in r2['results'])  # no leakage across users


def test_similar_repairs_embeddings(client, tech, session_id, fake, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv('GEMINI_EMBED_MODEL', 'fake-embed'); monkeypatch.setenv('GEMINI_API_KEY', 'x' * 30); get_settings.cache_clear()
    client.post(f'/api/v1/sessions/{session_id}/reports', json={'outcome': 'resolved'}, headers=tech['h'])
    r = client.get('/api/v1/similar-repairs?q=slow+fan+hum', headers=tech['h']).json()
    assert r['mode'] == 'embeddings' and r['results'][0]['source_type'] == 'session'


def test_every_route_commits_before_the_response(client):
    """Live run 21 Nov: a report read right after it was created returned 404, because get_db committed after the response
    was sent (FastAPI's default 'request' scope). Every route must get the session with scope='function'."""
    from fastapi.routing import APIRoute
    from app.db.session import get_db
    from app.main import create_app

    def walk(dep, out):
        for sub in dep.dependencies:
            if sub.call is get_db:
                out.append(sub.scope)
            walk(sub, out)
        return out
    def routes(rs):  # included routers may stay nested (FastAPI _IncludedRouter)
        for r in rs:
            if isinstance(r, APIRoute):
                yield r
            elif hasattr(r, 'original_router') or hasattr(r, 'routes'):
                yield from routes(getattr(r, 'original_router', r).routes)
    found = list(routes(create_app().routes))
    scopes = [s for r in found for s in walk(r.dependant, [])]
    assert len(found) > 40 and scopes and set(scopes) == {'function'}


def test_report_readable_right_after_creation(client, tech, session_id):
    r = client.post(f'/api/v1/sessions/{session_id}/reports', json={'outcome': 'resolved', 'first_time_fix': True}, headers=tech['h'])
    assert r.status_code == 201
    g = client.get(f"/api/v1/reports/{r.json()['id']}", headers=tech['h'])
    assert g.status_code == 200 and g.json()['resolution_status'] == 'resolved'
