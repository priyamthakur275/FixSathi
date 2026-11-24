"""ElevenLabs text-to-speech: the technician's own cloned voice for spoken replies. Gemini still writes every reply.

Server-side only: the API key comes from ELEVENLABS_API_KEY and is never logged, returned or sent to the browser.
API: POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128 with {text, model_id, voice_settings}.
"""
import logging, time
import httpx
from ..config import get_settings
from ..core.exceptions import AIError, AIUnavailable
from ..core.logging import log

logger = logging.getLogger('elevenlabs')
BASE = 'https://api.elevenlabs.io'
OUTPUT_FORMAT = 'mp3_44100_128'
MEDIA_TYPE = 'audio/mpeg'
# Clear, steady delivery that stays close to the cloned voice. Documented voice_settings fields.
VOICE_SETTINGS = {'stability': 0.5, 'similarity_boost': 0.8, 'style': 0.15, 'use_speaker_boost': True}
# After "not allowed" or "out of credits", skip ElevenLabs for a while instead of failing on every reply.
_BLOCKED_UNTIL = {'t': 0.0}


def configured() -> bool:
    s = get_settings()
    return bool(s.elevenlabs_api_key and s.elevenlabs_voice_id)


def model_for(language: str) -> str:
    """Kannada can be served by a different model than the rest (see ELEVENLABS_MODEL_KANNADA in .env.example)."""
    s = get_settings()
    return (s.elevenlabs_model_kannada if language == 'kannada' and s.elevenlabs_model_kannada else s.elevenlabs_model)


def _error(r: httpx.Response) -> AIError:
    try:
        d = (r.json() or {}).get('detail') or {}
    except ValueError:
        d = {}
    status = d.get('status') if isinstance(d, dict) else None
    msg = (d.get('message') if isinstance(d, dict) else str(d)) or r.text[:200]
    if r.status_code == 401 and status == 'missing_permissions':
        return AIUnavailable('The ElevenLabs API key is not allowed to generate speech. In ElevenLabs > Developers > API Keys, set '
                             '"Text to Speech" to "Access" for this key (or create a new key with it), then restart the backend.', code='TTS_KEY_PERMISSION',
                             details={'hint': 'In ElevenLabs > Developers > API Keys, enable "Text to Speech: Access" for this key.'})
    if status == 'api_key_id_used_as_api_key':
        return AIUnavailable('ELEVENLABS_API_KEY holds the key ID, not the key. Use the value that starts with "sk_" (shown once when the key is '
                             'created or rotated).', code='INVALID_API_KEY')
    if r.status_code == 401:
        return AIUnavailable('The ElevenLabs API key was rejected.', code='INVALID_API_KEY')
    if r.status_code in (402, 429) or status in ('quota_exceeded', 'too_many_concurrent_requests'):
        return AIUnavailable('ElevenLabs is out of credits or rate-limited right now.', code='QUOTA_EXCEEDED')
    if r.status_code == 404:
        return AIUnavailable('The ElevenLabs voice or model was not found.', code='MODEL_NOT_FOUND', details={'provider_message': msg[:160]})
    if r.status_code == 422 or r.status_code == 400:
        return AIError('ElevenLabs rejected the speech request.', code='INVALID_REQUEST', details={'provider_message': msg[:160]})
    return AIUnavailable('ElevenLabs is temporarily unavailable.', code='PROVIDER_UNAVAILABLE', details={'provider_http': r.status_code})


async def synthesize(text: str, language: str = 'english', client: httpx.AsyncClient | None = None) -> bytes:
    """MP3 audio of text in the configured voice."""
    s = get_settings()
    if not configured():
        raise AIUnavailable('ElevenLabs is not configured.', code='MODEL_NOT_CONFIGURED')
    if _BLOCKED_UNTIL['t'] > time.time():
        raise AIUnavailable('ElevenLabs is paused after an account error.', code='QUOTA_EXCEEDED')
    model = model_for(language)
    url = f'{BASE}/v1/text-to-speech/{s.elevenlabs_voice_id}'
    body = {'text': text, 'model_id': model, 'voice_settings': VOICE_SETTINGS}
    headers = {'xi-api-key': s.elevenlabs_api_key, 'accept': MEDIA_TYPE}
    t0 = time.perf_counter()
    own = client is None
    c = client or httpx.AsyncClient(timeout=s.elevenlabs_timeout_seconds)
    try:
        r = await c.post(url, params={'output_format': OUTPUT_FORMAT}, json=body, headers=headers)
    except httpx.HTTPError as e:
        log(logger, 'elevenlabs_failed', logging.WARNING, model=model, error=type(e).__name__)
        raise AIUnavailable('Cannot reach ElevenLabs.', code='NETWORK_ERROR') from e
    finally:
        if own:
            await c.aclose()
    ms = int((time.perf_counter() - t0) * 1000)
    if r.status_code != 200 or not r.content:
        err = _error(r) if r.status_code != 200 else AIError('ElevenLabs returned no audio.', code='AI_EMPTY')
        err.details = {**(err.details or {}), 'provider': 'elevenlabs', 'provider_http': r.status_code, 'voice_id': s.elevenlabs_voice_id, 'model': model}
        if err.code in ('TTS_KEY_PERMISSION', 'INVALID_API_KEY', 'QUOTA_EXCEEDED'):
            _BLOCKED_UNTIL['t'] = time.time() + 600
        log(logger, 'elevenlabs_failed', logging.WARNING, voice_id=s.elevenlabs_voice_id, model=model, http=r.status_code, code=err.code, ms=ms)
        raise err
    log(logger, 'elevenlabs_tts', voice_id=s.elevenlabs_voice_id, model=model, language=language, http=r.status_code, ms=ms, chars=len(text), bytes=len(r.content),
        cost=r.headers.get('character-cost'))
    return r.content
