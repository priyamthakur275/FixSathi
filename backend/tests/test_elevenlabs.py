"""ElevenLabs personal voice: request format, language-specific model, error mapping, fallbacks. No network: httpx.MockTransport."""
import asyncio, json, time
import httpx, pytest
from app.config import get_settings
from app.core.exceptions import AIUnavailable
from app.integrations import elevenlabs
from app.services import voice

KEY, VID = 'sk_test_not_a_real_key', 'FxJljbvZS4JCiZ8h8VRh'


@pytest.fixture
def el(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, 'elevenlabs_api_key', KEY); monkeypatch.setattr(s, 'elevenlabs_voice_id', VID)
    monkeypatch.setattr(s, 'elevenlabs_model', 'eleven_multilingual_v2'); monkeypatch.setattr(s, 'elevenlabs_model_kannada', None)
    elevenlabs._BLOCKED_UNTIL['t'] = 0; voice._CACHE.clear()
    yield s
    elevenlabs._BLOCKED_UNTIL['t'] = 0; voice._CACHE.clear()


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_request_format(el):
    seen = {}

    def handler(req: httpx.Request):
        seen.update(url=str(req.url), key=req.headers.get('xi-api-key'), accept=req.headers.get('accept'), body=json.loads(req.content))
        return httpx.Response(200, content=b'ID3fake-mp3', headers={'content-type': 'audio/mpeg'})
    audio = asyncio.run(elevenlabs.synthesize('Switch off the MCB first.', 'english', client=_client(handler)))
    assert audio == b'ID3fake-mp3'
    assert seen['url'] == f'https://api.elevenlabs.io/v1/text-to-speech/{VID}?output_format=mp3_44100_128'
    assert seen['key'] == KEY and seen['accept'] == 'audio/mpeg'
    assert seen['body']['text'] == 'Switch off the MCB first.' and seen['body']['model_id'] == 'eleven_multilingual_v2'
    assert set(seen['body']['voice_settings']) == {'stability', 'similarity_boost', 'style', 'use_speaker_boost'}


def test_kannada_can_use_its_own_model(el, monkeypatch):
    monkeypatch.setattr(el, 'elevenlabs_model_kannada', 'eleven_v3')
    assert elevenlabs.model_for('kannada') == 'eleven_v3'
    assert elevenlabs.model_for('hindi') == 'eleven_multilingual_v2' and elevenlabs.model_for('hinglish') == 'eleven_multilingual_v2'


@pytest.mark.parametrize('status,body,code', [
    (401, {'detail': {'status': 'missing_permissions', 'message': 'The API key you used is missing the permission text_to_speech'}}, 'TTS_KEY_PERMISSION'),
    (401, {'detail': {'status': 'invalid_api_key', 'message': 'Invalid API key'}}, 'INVALID_API_KEY'),
    (402, {'detail': {'status': 'quota_exceeded', 'message': 'quota'}}, 'QUOTA_EXCEEDED'),
    (429, {'detail': {'status': 'too_many_concurrent_requests', 'message': 'busy'}}, 'QUOTA_EXCEEDED'),
    (404, {'detail': {'status': 'voice_not_found', 'message': 'voice not found'}}, 'MODEL_NOT_FOUND'),
    (500, {'detail': 'boom'}, 'PROVIDER_UNAVAILABLE')])
def test_errors_are_mapped_and_never_contain_the_key(el, status, body, code):
    with pytest.raises(Exception) as e:
        asyncio.run(elevenlabs.synthesize('hi', client=_client(lambda r: httpx.Response(status, json=body))))
    assert e.value.code == code
    assert KEY not in str(e.value) and KEY not in json.dumps(e.value.details)


def test_account_errors_pause_elevenlabs(el):
    calls = []

    def handler(r):
        calls.append(1); return httpx.Response(401, json={'detail': {'status': 'missing_permissions', 'message': 'no'}})
    with pytest.raises(AIUnavailable):
        asyncio.run(elevenlabs.synthesize('hi', client=_client(handler)))
    with pytest.raises(AIUnavailable):
        asyncio.run(elevenlabs.synthesize('hi', client=_client(handler)))
    assert len(calls) == 1 and elevenlabs._BLOCKED_UNTIL['t'] > time.time()  # no repeated failing calls


def test_network_error(el):
    def handler(r): raise httpx.ConnectError('down')
    with pytest.raises(AIUnavailable) as e:
        asyncio.run(elevenlabs.synthesize('hi', client=_client(handler)))
    assert e.value.code == 'NETWORK_ERROR'


def test_voice_choice(el, monkeypatch):
    assert voice.voice_name(None) == 'personal' and voice.voice_name('personal') == 'personal'
    assert voice.voice_name('Kore') == 'Kore'  # a Gemini voice chosen in Settings still works
    monkeypatch.setattr(el, 'elevenlabs_api_key', None)
    assert voice.voice_name(None) == 'Charon' and voice.voice_name('personal') == 'Charon'  # not configured: Gemini default


# ---- through the speech endpoint ----

def _reply(client, tech, sid, text='Switch off the MCB. A weak capacitor is the likely cause.'):
    from tests.fakes import FakeGemini  # noqa: F401
    r = client.post(f'/api/v1/sessions/{sid}/messages', json={'text': 'fan slow', 'channel': 'voice'}, headers=tech['h'])
    return r.json()['assistant_message']['id']


def test_endpoint_uses_personal_voice(client, tech, session_id, fake, el, monkeypatch):
    got = {}

    async def fake_synth(text, language='english', client=None):
        got.update(text=text, language=language); return b'ID3personal'
    monkeypatch.setattr(elevenlabs, 'synthesize', fake_synth)
    fake.text = 'पहले MCB बंद करें। कैपेसिटर कमज़ोर हो सकता है।'
    mid = _reply(client, tech, session_id)
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech', headers=tech['h'])
    assert r.status_code == 200 and r.headers['content-type'] == 'audio/mpeg' and r.headers['x-voice'] == 'personal' and r.content == b'ID3personal'
    assert got['language'] == 'hindi' and 'MCB' in got['text']
    assert not any(c[0] == 'tts' for c in fake.calls)  # Gemini TTS not used


def test_endpoint_falls_back_to_gemini_voice(client, tech, session_id, fake, el, monkeypatch):
    async def broken(text, language='english', client=None):
        raise AIUnavailable('no', code='TTS_KEY_PERMISSION')
    monkeypatch.setattr(elevenlabs, 'synthesize', broken)
    monkeypatch.setattr(el, 'gemini_tts_model', 'fake-tts')
    mid = _reply(client, tech, session_id)
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech', headers=tech['h'])
    assert r.status_code == 200 and r.headers['content-type'] == 'audio/wav' and r.headers['x-voice'] == 'Charon'


def test_endpoint_reports_error_when_no_natural_voice_works(client, tech, session_id, fake, el, monkeypatch):
    async def broken(text, language='english', client=None):
        raise AIUnavailable('no', code='TTS_KEY_PERMISSION')
    monkeypatch.setattr(elevenlabs, 'synthesize', broken)
    monkeypatch.setattr(el, 'gemini_tts_model', None)
    mid = _reply(client, tech, session_id)
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech', headers=tech['h'])
    assert r.status_code == 503 and r.json()['error']['code'] == 'TTS_KEY_PERMISSION'  # the app then uses the device voice


def test_gemini_voice_still_selectable(client, tech, session_id, fake, el, monkeypatch):
    async def must_not(text, language='english', client=None):
        raise AssertionError('ElevenLabs must not be called for a Gemini voice')
    monkeypatch.setattr(elevenlabs, 'synthesize', must_not)
    monkeypatch.setattr(el, 'gemini_tts_model', 'fake-tts')
    mid = _reply(client, tech, session_id)
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech?voice=Kore', headers=tech['h'])
    assert r.status_code == 200 and r.headers['x-voice'] == 'Kore'


def test_typed_reply_never_generates_audio(client, tech, session_id, fake, el, monkeypatch):
    called = []

    async def spy(text, language='english', client=None):
        called.append(text); return b'x'
    monkeypatch.setattr(elevenlabs, 'synthesize', spy)
    r = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Hi FixSaathi'}, headers=tech['h'])
    assert r.status_code == 201 and r.json()['assistant_message']['meta']['channel'] == 'text' and not called


def test_strict_speech_does_not_fall_back(client, tech, session_id, fake, el, monkeypatch):
    async def broken(text, language='english', client=None):
        raise AIUnavailable('The ElevenLabs API key is not allowed to generate speech.', code='TTS_KEY_PERMISSION')
    monkeypatch.setattr(elevenlabs, 'synthesize', broken)
    monkeypatch.setattr(el, 'gemini_tts_model', 'fake-tts')  # a Gemini fallback exists, but strict must not use it
    mid = _reply(client, tech, session_id)
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech?strict=true', headers=tech['h'])
    assert r.status_code == 503 and r.json()['error']['code'] == 'TTS_KEY_PERMISSION'
    assert not any(c[0] == 'tts' for c in fake.calls)
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech', headers=tech['h'])  # normal mode still falls back
    assert r.status_code == 200 and r.headers['x-voice-provider'] == 'gemini'


def test_voice_test_endpoint(client, tech, el, monkeypatch):
    async def ok(text, language='english', client=None):
        assert 'own voice' in text and language == 'english'; return b'ID3cloned'
    monkeypatch.setattr(elevenlabs, 'synthesize', ok)
    r = client.post('/api/v1/voice/test-personal', headers=tech['h'])
    assert r.status_code == 200 and r.content == b'ID3cloned' and r.headers['content-type'] == 'audio/mpeg'
    assert r.headers['x-voice-provider'] == 'elevenlabs' and r.headers['x-voice-id'] == VID and r.headers['x-voice-model'] == 'eleven_multilingual_v2'
    assert KEY not in str(r.headers)
    assert client.post('/api/v1/voice/test-personal').status_code == 401  # signed-in users only


def test_voice_test_endpoint_reports_the_real_error(client, tech, el, monkeypatch):
    async def broken(text, language='english', client=None):
        raise AIUnavailable('The ElevenLabs API key is not allowed to generate speech.', code='TTS_KEY_PERMISSION')
    monkeypatch.setattr(elevenlabs, 'synthesize', broken)
    r = client.post('/api/v1/voice/test-personal', headers=tech['h'])
    assert r.status_code == 503 and r.json()['error']['code'] == 'TTS_KEY_PERMISSION' and KEY not in r.text


def test_voice_strict_setting_blocks_all_fallbacks(client, tech, session_id, fake, el, monkeypatch):
    async def broken(text, language='english', client=None):
        raise AIUnavailable('not allowed', code='TTS_KEY_PERMISSION', details={'provider': 'elevenlabs', 'provider_http': 401, 'voice_id': VID})
    monkeypatch.setattr(elevenlabs, 'synthesize', broken)
    monkeypatch.setattr(el, 'gemini_tts_model', 'fake-tts'); monkeypatch.setattr(el, 'voice_strict', True)
    mid = _reply(client, tech, session_id)
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech', headers=tech['h'])
    d = r.json()['error']
    assert r.status_code == 503 and d['code'] == 'TTS_KEY_PERMISSION'
    assert d['details']['strict'] is True and d['details']['provider_http'] == 401 and d['details']['voice_id'] == VID  # the app shows this, no device voice
    assert not any(c[0] == 'tts' for c in fake.calls)


def test_voice_status_reports_without_the_key(client, tech, el):
    r = client.get('/api/v1/voice/status', headers=tech['h']).json()
    assert r['preferred'] == 'elevenlabs' and r['elevenlabs']['voice_id'] == VID and r['elevenlabs']['key_loaded'] is True
    assert len(r['elevenlabs']['key_fingerprint']) == 10 and KEY not in json.dumps(r)
    assert client.get('/api/v1/voice/status').status_code == 401


def test_elevenlabs_error_details_carry_status_and_voice(el):
    with pytest.raises(Exception) as e:
        asyncio.run(elevenlabs.synthesize('hi', client=_client(lambda r: httpx.Response(400, json={'detail': {'status': 'api_key_id_used_as_api_key', 'message': 'API key ID used as API key'}}))))
    assert e.value.details['provider_http'] == 400 and e.value.details['voice_id'] == VID and e.value.details['provider'] == 'elevenlabs'


def test_key_id_instead_of_key_is_explained(el):
    with pytest.raises(Exception) as e:
        asyncio.run(elevenlabs.synthesize('hi', client=_client(lambda r: httpx.Response(400, json={'detail': {'status': 'api_key_id_used_as_api_key', 'message': 'x'}}))))
    assert e.value.code == 'INVALID_API_KEY' and 'sk_' in e.value.message
