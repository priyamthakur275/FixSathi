def test_root_returns_service_metadata(client):
    r = client.get('/')
    assert r.status_code == 200
    body = r.json()
    assert body['service'] == 'FixSaathi API'
    assert body['status'] == 'ok'
    assert body['health'] == '/health'
    assert body['ready'] == '/ready'
    assert body['docs'] == '/docs'


def test_health_and_ready_include_security_headers(client):
    for path in ('/health', '/ready'):
        r = client.get(path)
        assert r.status_code == 200
        assert r.headers.get('x-content-type-options') == 'nosniff'
        assert r.headers.get('x-frame-options') == 'DENY'
        assert r.headers.get('referrer-policy') == 'strict-origin-when-cross-origin'
        assert 'strict-transport-security' in r.headers
        assert 'permissions-policy' in r.headers


def test_health_commit_prefers_git_commit_over_render_git_commit(client, monkeypatch):
    monkeypatch.setenv('GIT_COMMIT', 'abcdef123456')
    monkeypatch.setenv('RENDER_GIT_COMMIT', '9999999')
    assert client.get('/health').json()['commit'] == 'abcdef1'

    monkeypatch.delenv('GIT_COMMIT', raising=False)
    monkeypatch.setenv('RENDER_GIT_COMMIT', '987654321')
    assert client.get('/health').json()['commit'] == '9876543'

    monkeypatch.delenv('RENDER_GIT_COMMIT', raising=False)
    assert client.get('/health').json()['commit'] is None
