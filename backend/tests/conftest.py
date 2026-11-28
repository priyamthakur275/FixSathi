import io, os, uuid
os.environ.setdefault('SECRET_KEY', 'test-secret-key-0123456789-abcdefghijklmnop')
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://postgres@/fixsaathi_test?host=/tmp')
os.environ['CORS_ORIGINS'] = 'http://localhost:5173'
os.environ['LOCAL_STORAGE_PATH'] = '/tmp/fixsaathi-test-uploads'
os.environ['AUTH_RATE_LIMIT_PER_MINUTE'] = '1000'
# Empty (not unset): environment variables win over backend/.env, so a real key there is never used by tests.
for k in ('GEMINI_API_KEY', 'GEMINI_AGENT_MODEL', 'GEMINI_FAST_MODEL', 'GEMINI_LIVE_MODEL', 'GEMINI_EMBED_MODEL', 'NANO_BANANA_MODEL', 'GEMINI_AGENT_FALLBACK_MODELS',
          'GEMINI_TTS_MODEL', 'ELEVENLABS_API_KEY', 'ELEVENLABS_VOICE_ID', 'ELEVENLABS_MODEL_KANNADA'):
    os.environ[k] = ''
os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'false'
os.environ['VOICE_STRICT'] = 'false'  # a local diagnostic setting in backend/.env must not change test behaviour

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text
from app.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.integrations.gemini import client as gclient
from app.integrations.storage.local import reset_storage

from tests.fakes import DIAG, STEPS, FakeGemini, png  # noqa: F401

HERE = os.path.dirname(os.path.dirname(__file__))


def _assert_disposable_database() -> None:
    """The fixture below wipes the whole schema. Refuse unless DATABASE_URL is clearly a local, throwaway test database,
    so an exported production URL (Neon, Render, AlloyDB...) can never be erased by running pytest."""
    from sqlalchemy.engine import make_url
    u = make_url(get_settings().database_url)
    socket = (u.query or {}).get('host', '')
    local = (u.host in (None, '', 'localhost', '127.0.0.1', '::1')) and (not socket or str(socket).startswith('/'))
    if not (u.database or '').endswith('_test') or not local:
        pytest.exit(f'Refusing to run: tests DROP the schema of DATABASE_URL, which must be a local database whose name ends in "_test" '
                    f'(got database={u.database!r}, host={u.host!r}).', returncode=2)


@pytest.fixture(scope='session', autouse=True)
def migrate():
    _assert_disposable_database()
    cfg = Config(os.path.join(HERE, 'alembic.ini')); cfg.set_main_option('script_location', os.path.join(HERE, 'alembic'))
    with engine().begin() as c:
        c.execute(text('DROP SCHEMA public CASCADE; CREATE SCHEMA public'))
    command.upgrade(cfg, 'head')  # migrations are exercised, not create_all
    yield


@pytest.fixture(autouse=True)
def clean(migrate):
    with engine().begin() as c:
        c.execute(text('TRUNCATE ' + ', '.join(t.name for t in reversed(Base.metadata.sorted_tables)) + ' RESTART IDENTITY CASCADE'))
    from app.core.security import auth_limiter
    from app.core import quota
    from app.services import knowledge_base as kb
    auth_limiter.hits.clear(); quota.reset(); kb.clear_cache(); reset_storage(); gclient.set_gemini(None); gclient.COOLDOWN.clear(); gclient.RELAXED_SCHEMA.clear(); get_settings.cache_clear()
    yield
    gclient.set_gemini(None)


@pytest.fixture
def client():
    from app.main import create_app
    with TestClient(create_app()) as c:
        yield c


def register(c, email=None, org=None, name='Test Tech'):
    r = c.post('/api/v1/auth/register', json={'full_name': name, 'email': email or f'{uuid.uuid4().hex[:8]}@example.com', 'password': 'correct horse 1', 'organisation_name': org})
    assert r.status_code == 201, r.text
    d = r.json(); d['h'] = {'Authorization': f"Bearer {d['access_token']}"}
    return d


def make_role(user_id, role):
    with engine().begin() as c:
        c.execute(text('update users set role=:r where id=:i'), {'r': role, 'i': user_id})


@pytest.fixture
def tech(client): return register(client, org='Acme Service')


@pytest.fixture
def session_id(client, tech):
    r = client.post('/api/v1/sessions', json={'issue_description': 'ceiling fan is slow and hums', 'appliance_type': 'ceiling_fan'}, headers=tech['h'])
    assert r.status_code == 201
    return r.json()['id']


@pytest.fixture
def fake():
    f = FakeGemini(); f.json = {'diagnosis': DIAG, 'guidance': STEPS}
    gclient.set_gemini(f)
    yield f
