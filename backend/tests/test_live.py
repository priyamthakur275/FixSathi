"""Live relay tests with a fake Gemini Live session built from real google-genai types. No network calls."""
import asyncio, base64, json, uuid
import pytest
from google.genai import types
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect
from app.db.models import Conversation, SafetyEvent
from app.db.session import SessionLocal
from app.services import live
from tests.conftest import register

ORIGIN = {'origin': 'http://localhost:5173'}


class FakeLive:
    instances: list = []

    def __init__(self, model, config, fail=False):
        self.model, self.config, self.fail = model, config, fail
        self.sent: list = []; self.tool_responses: list = []
        FakeLive.instances.append(self)

    async def __aenter__(self):
        if self.fail:
            raise ConnectionError('gemini down')
        self.q: asyncio.Queue = asyncio.Queue(); return self

    async def __aexit__(self, *a): return False

    async def send_realtime_input(self, **kw):
        self.sent.append(kw)
        if kw.get('text') == 'go':
            for m in script():
                await self.q.put(m)

    async def send_tool_response(self, function_responses):
        self.tool_responses.append(function_responses)

    async def receive(self):
        while True:
            yield await self.q.get()


def script():
    SC, P = types.LiveServerContent, types.Part
    return [
        types.LiveServerMessage(server_content=SC(input_transcription=types.Transcription(text='pankha slow hai'))),
        types.LiveServerMessage(server_content=SC(model_turn=types.Content(parts=[P(inline_data=types.Blob(data=b'\x01\x02\x03\x04', mime_type='audio/pcm;rate=24000'))]),
                                                  output_transcription=types.Transcription(text='Canopy kholne se pehle MCB off karo'))),
        types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[types.FunctionCall(id='c1', name='give_step',
                                args={'title': 'Open canopy', 'instruction': 'Unscrew the canopy cover', 'requires_power_off': False})])),
        types.LiveServerMessage(server_content=SC(turn_complete=True)),
    ]


@pytest.fixture
def live_ok(fake, monkeypatch):
    FakeLive.instances = []
    live.set_connector(lambda m, c: FakeLive(m, c)); yield; live.set_connector(None)


def recv_until(ws, t, limit=20):
    for _ in range(limit):
        m = json.loads(ws.receive_text())
        if m['type'] == t:
            return m
    raise AssertionError(f'{t} not received')


def test_rejects_bad_origin(client, session_id, live_ok):
    with pytest.raises(WebSocketDisconnect) as e:
        with client.websocket_connect(f'/api/v1/live/{session_id}', headers={'origin': 'https://evil.example'}) as ws:
            ws.receive_text()
    assert e.value.code == 4403


def test_requires_auth_first(client, session_id, live_ok):
    with client.websocket_connect(f'/api/v1/live/{session_id}', headers=ORIGIN) as ws:
        ws.send_text(json.dumps({'type': 'audio_chunk', 'data': ''}))
        m = json.loads(ws.receive_text())
    assert m['type'] == 'error' and m['code'] == 'AUTH_REQUIRED' and m['fatal']


def test_other_users_session_rejected(client, session_id, live_ok):
    other = register(client)
    with client.websocket_connect(f'/api/v1/live/{session_id}', headers=ORIGIN) as ws:
        ws.send_text(json.dumps({'type': 'auth', 'token': other['access_token']}))
        assert json.loads(ws.receive_text())['code'] == 'NOT_FOUND'


def test_ai_not_configured(client, tech, session_id):
    with client.websocket_connect(f'/api/v1/live/{session_id}', headers=ORIGIN) as ws:
        ws.send_text(json.dumps({'type': 'auth', 'token': tech['access_token']}))
        assert json.loads(ws.receive_text())['code'] == 'AI_NOT_CONFIGURED'


def test_gemini_failure_reported(client, tech, session_id, fake):
    live.set_connector(lambda m, c: FakeLive(m, c, fail=True))
    try:
        with client.websocket_connect(f'/api/v1/live/{session_id}', headers=ORIGIN) as ws:
            ws.send_text(json.dumps({'type': 'auth', 'token': tech['access_token']}))
            m = json.loads(ws.receive_text())
        assert m['code'] == 'LIVE_FAILED' and 'gemini' not in m['message'].lower().replace('ai', '')
    finally:
        live.set_connector(None)


def test_full_flow_validation_tools_and_transcripts(client, tech, session_id, live_ok):
    with client.websocket_connect(f'/api/v1/live/{session_id}', headers=ORIGIN) as ws:
        ws.send_text(json.dumps({'type': 'auth', 'token': tech['access_token'], 'language': 'Hindi'}))
        ready = recv_until(ws, 'session_ready'); assert ready['model'] == 'fake-live'
        ws.send_text('not json'); assert recv_until(ws, 'error')['code'] == 'INVALID_JSON'
        ws.send_text(json.dumps({'type': 'audio_chunk', 'data': '!!!'})); assert recv_until(ws, 'error')['code'] == 'INVALID_PAYLOAD'
        ws.send_text(json.dumps({'type': 'audio_chunk', 'data': base64.b64encode(b'\x00').decode()})); assert recv_until(ws, 'error')['code'] == 'INVALID_AUDIO'
        ws.send_text(json.dumps({'type': 'video_frame', 'data': base64.b64encode(b'GIF89a').decode()})); assert recv_until(ws, 'error')['code'] == 'INVALID_IMAGE'
        ws.send_text(json.dumps({'type': 'video_frame', 'data': 'A' * 900_000})); assert recv_until(ws, 'error')['code'] == 'PAYLOAD_TOO_LARGE'
        ws.send_text(json.dumps({'type': 'audio_chunk', 'data': base64.b64encode(b'\x00\x00' * 160).decode()}))
        ws.send_text(json.dumps({'type': 'text_input', 'text': 'go'}))
        assert recv_until(ws, 'transcription')['text'] == 'pankha slow hai'
        audio = recv_until(ws, 'audio_chunk'); assert base64.b64decode(audio['data']) == b'\x01\x02\x03\x04' and '24000' in audio['mime_type']
        blocked = recv_until(ws, 'safety_blocked'); assert blocked['allowed'] is False and blocked['reason'] == 'SAFETY_CONFIRMATION_REQUIRED'
        recv_until(ws, 'turn_complete')
        ws.send_text(json.dumps({'type': 'end_session'}))
        assert recv_until(ws, 'session_ended')
    f = FakeLive.instances[-1]
    assert 'Hindi' in f.config.system_instruction and f.config.response_modalities == ['AUDIO']
    audio_sent = [s['audio'] for s in f.sent if 'audio' in s]
    assert len(audio_sent) == 1 and audio_sent[0].mime_type == 'audio/pcm;rate=16000'
    resp = f.tool_responses[0][0]; assert resp.name == 'give_step' and resp.response['allowed'] is False
    with SessionLocal() as db:
        msgs = db.scalars(select(Conversation).where(Conversation.session_id == uuid.UUID(session_id), Conversation.message_type == 'voice_transcript')).all()
        assert {m.role for m in msgs} == {'user', 'assistant'}
        assert db.scalars(select(SafetyEvent).where(SafetyEvent.actor == 'ai_tool', SafetyEvent.blocked.is_(True))).first() is not None
    assert client.get(f'/api/v1/sessions/{session_id}', headers=tech['h']).json()['status'] == 'awaiting_confirmation'


def test_closed_session_rejected(client, tech, session_id, live_ok):
    client.post(f'/api/v1/sessions/{session_id}/cancel', headers=tech['h'])
    with client.websocket_connect(f'/api/v1/live/{session_id}', headers=ORIGIN) as ws:
        ws.send_text(json.dumps({'type': 'auth', 'token': tech['access_token']}))
        assert json.loads(ws.receive_text())['code'] == 'SESSION_CLOSED'
