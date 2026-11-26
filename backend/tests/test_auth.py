from datetime import timedelta
import jwt
from app.config import get_settings
from app.core.security import create_access_token
from tests.conftest import register


def test_register_login_me(client):
    d = register(client, email='a@example.com')
    assert 'password_hash' not in d['user'] and d['user']['role'] == 'technician'
    r = client.post('/api/v1/auth/login', json={'email': 'A@example.com', 'password': 'correct horse 1'})
    assert r.status_code == 200
    me = client.get('/api/v1/auth/me', headers={'Authorization': f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200 and me.json()['email'] == 'a@example.com' and 'password' not in me.text


def test_duplicate_email(client):
    register(client, email='dup@example.com')
    r = client.post('/api/v1/auth/register', json={'full_name': 'X Y', 'email': 'dup@example.com', 'password': 'correct horse 1'})
    assert r.status_code == 409 and r.json()['error']['code'] == 'EMAIL_TAKEN'


def test_wrong_password(client):
    register(client, email='b@example.com')
    r = client.post('/api/v1/auth/login', json={'email': 'b@example.com', 'password': 'nope'})
    assert r.status_code == 401 and r.json()['error']['code'] == 'INVALID_CREDENTIALS'


def test_invalid_and_missing_token(client):
    assert client.get('/api/v1/auth/me').status_code == 401
    assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer garbage'}).json()['error']['code'] == 'TOKEN_INVALID'
    forged = jwt.encode({'sub': '00000000-0000-0000-0000-000000000000', 'type': 'access'}, 'wrong-key-wrong-key-wrong-key-wrong', algorithm='HS256')
    assert client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {forged}'}).status_code == 401


def test_expired_token(client):
    d = register(client)
    t = create_access_token(d['user']['id'], 'technician', minutes=-1)
    r = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {t}'})
    assert r.status_code == 401 and r.json()['error']['code'] == 'TOKEN_EXPIRED'


def test_refresh_rotation_and_logout(client):
    d = register(client)
    r1 = client.post('/api/v1/auth/refresh', json={'refresh_token': d['refresh_token']}); assert r1.status_code == 200
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': d['refresh_token']}).status_code == 401  # reused token rejected
    new = r1.json()['refresh_token']
    assert client.post('/api/v1/auth/logout', json={'refresh_token': new}).status_code == 204
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': new}).status_code == 401


def test_login_rate_limited(client, monkeypatch):
    monkeypatch.setenv('AUTH_RATE_LIMIT_PER_MINUTE', '3'); get_settings.cache_clear()
    codes = [client.post('/api/v1/auth/login', json={'email': 'x@example.com', 'password': 'bad'}).status_code for _ in range(5)]
    assert codes[:3] == [401, 401, 401] and codes[3] == 429


def test_self_registration_cannot_pick_role(client):
    r = client.post('/api/v1/auth/register', json={'full_name': 'Eve E', 'email': 'eve@example.com', 'password': 'correct horse 1', 'role': 'admin'})
    assert r.status_code == 201 and r.json()['user']['role'] == 'technician'


def test_update_language(client):
    d = register(client)
    r = client.patch('/api/v1/users/me', json={'preferred_language': 'Kannada'}, headers=d['h'])
    assert r.json()['preferred_language'] == 'Kannada'
    assert client.patch('/api/v1/users/me', json={'preferred_language': 'Klingon'}, headers=d['h']).status_code == 422
