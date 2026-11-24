"""Spoken replies: typed messages are answered in text only; Gemini TTS speaks stored, safety-screened replies on request."""
import asyncio, uuid
import pytest
from sqlalchemy import select
from app.core.exceptions import AIUnavailable
from app.db.models import Conversation
from app.db.session import SessionLocal
from app.integrations.gemini import client as gclient
from app.services import voice

CONFIRM = {'power_off_confirmed': True, 'tester_checked': True}


@pytest.fixture(autouse=True)
def _clear_cache():
    voice._CACHE.clear(); yield; voice._CACHE.clear()


def _send(client, tech, sid, text, channel=None):
    body = {'text': text} | ({'channel': channel} if channel else {})
    r = client.post(f'/api/v1/sessions/{sid}/messages', json=body, headers=tech['h'])
    assert r.status_code == 201, r.text
    return r.json()


def test_typed_message_reply_is_marked_text(client, tech, session_id, fake):
    r = _send(client, tech, session_id, 'Hi FixSaathi')
    assert r['assistant_message']['meta']['channel'] == 'text' and r['user_message']['meta']['channel'] == 'text'
    assert not any(c[0] == 'tts' for c in fake.calls)  # answering never generates audio by itself


def test_voice_message_reply_is_marked_voice(client, tech, session_id, fake):
    r = _send(client, tech, session_id, 'fan hums and is slow', channel='voice')
    assert r['assistant_message']['meta']['channel'] == 'voice'
    assert not any(c[0] == 'tts' for c in fake.calls)  # audio is made only when the app asks for it


def test_pdf_reply_keeps_the_channel(client, tech, session_id, fake):
    r = _send(client, tech, session_id, 'Generate a repair report PDF', channel='voice')
    assert r['assistant_message']['meta']['channel'] == 'voice'


def test_speech_endpoint_returns_wav_and_caches(client, tech, session_id, fake):
    mid = _send(client, tech, session_id, 'fan slow')['assistant_message']['id']
    url = f'/api/v1/sessions/{session_id}/messages/{mid}/speech'
    r = client.get(url, headers=tech['h'])
    assert r.status_code == 200 and r.headers['content-type'] == 'audio/wav' and r.content[:4] == b'RIFF' and r.headers['x-voice'] == 'Charon'
    client.get(url, headers=tech['h'])
    assert sum(1 for c in fake.calls if c[0] == 'tts') == 1  # second play served from the cache
    r = client.get(url + '?voice=Kore', headers=tech['h'])
    assert r.headers['x-voice'] == 'Kore' and fake.calls[-1][2] == 'Kore'


def test_speech_unknown_voice_falls_back_to_default(client, tech, session_id, fake):
    mid = _send(client, tech, session_id, 'fan slow')['assistant_message']['id']
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech?voice=MadeUpVoice', headers=tech['h'])
    assert r.status_code == 200 and r.headers['x-voice'] == 'Charon'


def test_speech_only_for_assistant_messages_in_readable_sessions(client, tech, session_id, fake):
    from tests.conftest import register
    other_tech = register(client, org='Other Org')
    r = _send(client, tech, session_id, 'fan slow')
    um, am = r['user_message']['id'], r['assistant_message']['id']
    assert client.get(f'/api/v1/sessions/{session_id}/messages/{um}/speech', headers=tech['h']).status_code == 404
    assert client.get(f'/api/v1/sessions/{session_id}/messages/{uuid.uuid4()}/speech', headers=tech['h']).status_code == 404
    assert client.get(f'/api/v1/sessions/{session_id}/messages/{am}/speech', headers=other_tech['h']).status_code in (403, 404)
    assert client.get(f'/api/v1/sessions/{session_id}/messages/{am}/speech').status_code == 401


def test_spoken_text_keeps_power_steps_withheld(client, tech, session_id, fake):
    fake.text = 'A **weak capacitor** is the likely cause [fixsaathi:fan_slow_hum].\n1. Spin the blades by hand.\n2. Unscrew the canopy and disconnect the capacitor wires.'
    mid = _send(client, tech, session_id, 'fan slow')['assistant_message']['id']
    client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech', headers=tech['h'])
    spoken = next(c[1] for c in fake.calls if c[0] == 'tts')
    assert 'weak capacitor' in spoken and '**' not in spoken and 'fixsaathi:' not in spoken and 'Spin the blades by hand' in spoken
    assert 'Unscrew' not in spoken and 'disconnect' not in spoken and 'withheld: see the note below' not in spoken
    assert 'held back a power-sensitive step' in spoken  # the spoken lock note, not the written one


def test_speech_quota_error_lets_the_app_fall_back(client, tech, session_id, fake):
    mid = _send(client, tech, session_id, 'fan slow')['assistant_message']['id']
    fake.fail['tts'] = AIUnavailable('limit', code='QUOTA_EXCEEDED')
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech', headers=tech['h'])
    assert r.status_code == 503 and r.json()['error']['code'] == 'QUOTA_EXCEEDED'


def test_speech_not_configured_without_tts_model(client, tech, session_id, monkeypatch):
    from app.config import get_settings
    from tests.fakes import FakeGemini
    f = FakeGemini(); gclient.set_gemini(f)
    fake_text = _send(client, tech, session_id, 'fan slow')['assistant_message']['id']
    monkeypatch.setattr(get_settings(), 'gemini_tts_model', None)
    g = gclient.GeminiClient(client=object()); gclient.set_gemini(g)
    monkeypatch.setattr(get_settings(), 'gemini_api_key', 'test')
    r = client.get(f'/api/v1/sessions/{session_id}/messages/{fake_text}/speech', headers=tech['h'])
    assert r.status_code == 503 and r.json()['error']['code'] == 'MODEL_NOT_CONFIGURED'


def test_tts_model_cooling_down_is_not_called(monkeypatch):
    import time
    from app.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_tts_model', 'tts-m')
    called = []

    class Models:
        async def generate_content(self, **kw):
            called.append(kw); raise AssertionError('must not be called')
    g = gclient.GeminiClient(client=type('C', (), {'aio': type('A', (), {'models': Models()})()})())
    gclient.COOLDOWN['tts-m'] = time.time() + 600
    with pytest.raises(AIUnavailable) as e:
        asyncio.run(g.speech('hello', 'Charon'))
    assert e.value.code == 'QUOTA_EXCEEDED' and not called


def test_tts_request_uses_prebuilt_voice_and_audio_modality(monkeypatch):
    from app.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_tts_model', 'tts-m')
    seen = {}

    class Part:
        inline_data = type('D', (), {'mime_type': 'audio/L16;codec=pcm;rate=24000', 'data': b'\x01\x02'})()

    class Models:
        async def generate_content(self, model, contents, config):
            seen.update(model=model, contents=contents, config=config)
            return type('R', (), {'candidates': [type('Cn', (), {'content': type('Ct', (), {'parts': [Part()]})()})()], 'usage_metadata': None})()
    g = gclient.GeminiClient(client=type('C', (), {'aio': type('A', (), {'models': Models()})()})())
    pcm, meta = asyncio.run(g.speech('Switch off the MCB.', 'Kore'))
    assert pcm == b'\x01\x02' and seen['model'] == 'tts-m'
    assert seen['config'].response_modalities == ['AUDIO'] and seen['config'].speech_config.voice_config.prebuilt_voice_config.voice_name == 'Kore'
    assert seen['contents'].endswith('Switch off the MCB.') and seen['contents'].startswith(gclient.TTS_STYLE)
    with pytest.raises(Exception) as e:
        asyncio.run(g.speech('x', 'NotAVoice'))
    assert e.value.code == 'VOICE_NOT_SUPPORTED'


# ---------- delivery direction: language and tone come from the reply itself ----------

@pytest.mark.parametrize('text,lang', [
    ('A weak capacitor is the most likely cause.', 'english'),
    ('Pehle MCB band karo, phir tester se check karo ki line live nahi hai.', 'hinglish'),
    ('पहले MCB बंद करें, फिर टेस्टर से जाँचें।', 'hindi'),
    ('ಮೊದಲು MCB ಆಫ್ ಮಾಡಿ, ನಂತರ ಟೆಸ್ಟರ್‌ನಿಂದ ಪರಿಶೀಲಿಸಿ.', 'kannada'),
    ('முதலில் MCB-ஐ அணைத்து, டெஸ்டரால் சரிபார்க்கவும்.', 'tamil'),
    ('Check the regulator and the capacitor.', 'english')])  # English words alone are not Hinglish
def test_language_is_detected_from_the_reply(text, lang):
    assert voice.language_of(text) == lang


def test_safety_warnings_always_get_the_firm_tone():
    for t in ('Switch off the MCB and confirm with your tester.', 'Never touch the terminals.', 'Pehle MCB band karo.',
              'ಮೊದಲು MCB ಆಫ್ ಮಾಡಿ.', voice.spoken_text(voice.LOCK_NOTE)):
        d = voice.direction(t)
        assert 'firm, serious' in d and 'Never sound cheerful about safety' in d, t
    assert 'firm, serious' not in voice.direction('A weak capacitor is the most likely cause.')


def test_tone_follows_the_content():
    assert 'warmly' in voice.direction('Hello! How can I help with your repair today?')
    assert 'steps patiently' in voice.direction('1. Spin the blades.\n2. Note the speed.')
    assert 'positive, encouraging' in voice.direction('Great job, that fixed it!')
    assert 'Hinglish' in voice.direction('Capacitor kharab hai, isko badal do aur phir fan chalu karo.')
    assert voice.direction('x').endswith('Read only the text below.')


def test_speech_request_carries_the_direction(client, tech, session_id, fake):
    fake.text = 'Switch off the MCB first. A weak capacitor is the likely cause.'
    mid = _send(client, tech, session_id, 'fan slow')['assistant_message']['id']
    client.get(f'/api/v1/sessions/{session_id}/messages/{mid}/speech', headers=tech['h'])
    call = next(c for c in fake.calls if c[0] == 'tts')
    assert 'Indian English' in call[3] and 'firm, serious' in call[3]


def test_tts_empty_audio_is_retried_once(monkeypatch):
    """22 Nov: the preview TTS model sometimes answers STOP without audio; the identical request then succeeds."""
    from app.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, 'gemini_api_key', 'test'); monkeypatch.setattr(s, 'gemini_tts_model', 'tts-m')
    calls = []

    class Part:
        inline_data = type('D', (), {'mime_type': 'audio/L16;codec=pcm;rate=24000', 'data': b'\x01\x02'})()

    def resp(parts):
        return type('R', (), {'candidates': [type('Cn', (), {'content': type('Ct', (), {'parts': parts})(), 'finish_reason': 'STOP'})()], 'usage_metadata': None})()

    class Models:
        async def generate_content(self, **kw):
            calls.append(1)
            return resp(None if len(calls) == 1 else [Part()])
    g = gclient.GeminiClient(client=type('C', (), {'aio': type('A', (), {'models': Models()})()})())
    pcm, _ = asyncio.run(g.speech('Switch off the MCB.', 'Charon'))
    assert pcm == b'\x01\x02' and len(calls) == 2

    calls.clear()

    class Empty:
        async def generate_content(self, **kw):
            calls.append(1); return resp(None)
    g = gclient.GeminiClient(client=type('C', (), {'aio': type('A', (), {'models': Empty()})()})())
    with pytest.raises(Exception) as e:
        asyncio.run(g.speech('x', 'Charon'))
    assert e.value.code == 'AI_EMPTY' and len(calls) == 2  # retried once, then the app falls back to the device voice
