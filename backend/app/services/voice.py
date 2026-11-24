"""Spoken replies: the technician's own ElevenLabs voice first, Gemini text-to-speech as the fallback.

Only stored assistant messages are spoken, so the audio always matches text that already passed the server-side safety screen.
Withheld power steps stay withheld: their on-screen marker is dropped and the written lock note is replaced by the spoken one.
"""
import io, logging, re, wave
from collections import OrderedDict
from ..config import get_settings
from ..core.logging import log
from ..db.models import Conversation
from ..integrations.gemini.client import TTS_SAMPLE_RATE, TTS_VOICES, get_gemini
from .pdf_report import _CITATION
from .safety import LOCK_NOTE, LOCK_NOTE_VOICE, WITHHELD_MARK

MAX_CHARS = 3000
_CACHE: OrderedDict[tuple[str, str], tuple[bytes, str, str]] = OrderedDict()  # (message id, voice) -> audio. Replays cost nothing.
_CACHE_SIZE = 40
logger = logging.getLogger('voice')


def spoken_text(message: str) -> str:
    t = (message or '').replace(LOCK_NOTE, LOCK_NOTE_VOICE).replace(WITHHELD_MARK, '')
    t = _CITATION.sub('', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)                 # [label](url) -> label
    t = re.sub(r'`([^`]+)`', r'\1', t)
    t = re.sub(r'(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1', r'\2', t)      # bold / italic
    t = re.sub(r'^\s*#{1,6}\s+', '', t, flags=re.M)
    t = re.sub(r'^\s*[-*•]\s+', '', t, flags=re.M)                  # bullets read as sentences
    t = re.sub(r'^\s*(\d+)[.)]\s+', r'\1. ', t, flags=re.M)
    t = re.sub(r'(?m)([^.!?:;\s])\s*$', r'\1.', t)                  # each line ends a sentence, so the voice pauses there
    t = re.sub(r'[ \t]+', ' ', re.sub(r'\n{2,}', '\n', t)).strip()
    if len(t) > MAX_CHARS:
        cut = max(t.rfind('. ', 0, MAX_CHARS), t.rfind('\n', 0, MAX_CHARS))
        t = t[:cut + 1 if cut > MAX_CHARS // 2 else MAX_CHARS]
    return t


# ---- delivery: one natural-language direction per reply (Gemini TTS is steered in words; one request per reply) ----

PERSONA = ('You are FixSaathi, a friendly, sharp field-technician assistant talking to a technician in India. Speak like a skilled '
           'colleague standing beside them: warm, confident and natural, at a relaxed but brisk conversational pace, with natural '
           'pitch movement, realistic pauses between sentences and emphasis on the words that matter. Never sound like a narrator '
           'reading a list, and never exaggerate.')
_KANNADA = re.compile(r'[\u0C80-\u0CFF]')
_TAMIL = re.compile(r'[\u0B80-\u0BFF]')
_DEVANAGARI = re.compile(r'[\u0900-\u097F]')
# Common Hindi words written in Roman letters: two or more mean the reply is Hinglish.
_HINGLISH = re.compile(r'\b(hai|hain|nahi|nahin|karo|karein|kijiye|kya|toh|aur|ke|ki|ko|mein|se|pehle|phir|abhi|agar|lekin|bhi|wala|wali|'
                       r'dekho|dekhiye|chalu|band|thik|theek|accha|achha|haan|ji|aap|apna|yeh|woh|kuch|zaroor|bilkul|bas)\b', re.I)
_SAFETY = re.compile(r'(switch(ed)? off|turn (it )?off|isolat\w*|\bMCB\b|tester|unplug|do not|don\'t|never|danger\w*|shock|live (wire|line|terminal)|'
                     r'high[- ]voltage|lethal|held back a power-sensitive step|authorised service|'
                     r'बंद कर|मत |कभी नहीं|खतरा|झटका|ಆಫ್ ಮಾಡಿ|ಬೇಡ|ಅಪಾಯ|அணைத்|வேண்டாம்|ஆபத்து)', re.I)
# Non-Latin words are matched without \b: Python's word boundary is unreliable after Devanagari/Kannada vowel signs.
_GREETING = re.compile(r'^\W*(?:(?:hi|hello|hey|namaste|namaskar|welcome|good (?:morning|afternoon|evening))\b|नमस्ते|नमस्कार|ನಮಸ್ಕಾರ|வணக்கம்)', re.I)
_DONE = re.compile(r'\b(?:well done|great (?:job|work)|nice work|good job|that fixed it|it\'?s fixed|problem (?:is )?(?:solved|resolved)|resolved|'
                   r'shabash|(?:bahut )?badhiya)\b|बढ़िया|शाबाश|ಚೆನ್ನಾಗಿದೆ|ಶಭಾಷ್|அருமை', re.I)
_STEPS = re.compile(r'(^|\n)\s*\d+\.\s')


def language_of(text: str) -> str:
    t = text or ''
    letters = sum(c.isalpha() for c in t) or 1
    if len(_KANNADA.findall(t)) / letters > 0.2: return 'kannada'
    if len(_TAMIL.findall(t)) / letters > 0.2: return 'tamil'
    if len(_DEVANAGARI.findall(t)) / letters > 0.2: return 'hindi'
    if len(_HINGLISH.findall(t)) >= 2: return 'hinglish'
    return 'english'


_ACCENT = {
    'english': 'Speak clear, professional Indian English with a natural Indian accent.',
    'hindi': 'Speak natural, everyday Hindi with native pronunciation. Say English technical words (MCB, capacitor, tester) the way Indian technicians say them.',
    'hinglish': ('This is Hinglish: Hindi written in Roman letters, mixed with English. Pronounce the Hindi words as natural Hindi and the '
                 'English words with an Indian English accent, flowing as one natural voice without switching accent mid-sentence.'),
    'kannada': 'Speak natural, everyday Kannada with native pronunciation. Say English technical words (MCB, capacitor, tester) the way technicians in Karnataka say them.',
    'tamil': 'Speak natural, everyday Tamil with native pronunciation. Say English technical words the way technicians in Tamil Nadu say them.',
}


def direction(text: str) -> str:
    """How this reply should sound. Safety wording always gets the firm tone, whatever else the reply contains."""
    tone = []
    if _GREETING.search(text): tone.append('Open warmly and welcoming.')
    if _STEPS.search(text): tone.append('Give the steps patiently and conversationally, with a short pause after each step, easy to follow.')
    else: tone.append('Explain the likely cause calmly, confidently and clearly.')
    if _SAFETY.search(text):
        tone.append('Say every safety warning (switching off, isolating, testing, anything they must not do) in a firm, serious, '
                    'unhurried tone with clear emphasis. Never sound cheerful about safety.')
    if _DONE.search(text): tone.append('Finish on a positive, encouraging note.')
    return ' '.join([PERSONA, _ACCENT[language_of(text)], *tone, 'Read only the text below.'])


def wav(pcm: bytes, rate: int = TTS_SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    return buf.getvalue()


PERSONAL = 'personal'  # the technician's own ElevenLabs voice clone


def voice_name(requested: str | None) -> str:
    """'personal' (ElevenLabs) when asked for or by default when it is configured; otherwise a Gemini prebuilt voice."""
    from ..integrations import elevenlabs
    if requested == PERSONAL or (not requested and elevenlabs.configured()):
        return PERSONAL if elevenlabs.configured() else get_settings().gemini_tts_voice
    v = requested or get_settings().gemini_tts_voice
    return v if v in TTS_VOICES else 'Charon'


async def _gemini(text: str, v: str) -> tuple[bytes, str, str]:
    pcm, _ = await get_gemini().speech(text, v, direction(text))
    return wav(pcm), 'audio/wav', v


def provider_of(voice_used: str) -> str:
    return 'elevenlabs' if voice_used == PERSONAL else 'gemini'


async def speak(m: Conversation, voice: str | None, strict: bool = False) -> tuple[bytes, str, str]:
    """(audio, media type, voice used). Personal voice first; if ElevenLabs fails, the Gemini voice; the app falls back to the
    device voice when both fail. strict=True: no fallback, the ElevenLabs error is raised (used to verify the cloned voice).
    Each (message, voice) is generated once and cached. Every answer logs which provider actually produced the audio."""
    from ..core.exceptions import AppError
    from ..integrations import elevenlabs
    v = voice_name(voice)
    strict = strict or (v == PERSONAL and get_settings().voice_strict)
    if strict and v != PERSONAL:
        raise AppError('The personal voice is not configured on the server.', code='MODEL_NOT_CONFIGURED', status=503)
    key = (str(m.id), v)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        log(logger, 'speech_provider', provider=provider_of(_CACHE[key][2]), voice=_CACHE[key][2], cached=True, message=str(m.id))
        return _CACHE[key]
    text = spoken_text(m.message)
    if not text:
        raise AppError('This message has nothing to read aloud.', code='NOTHING_TO_SPEAK')
    if v == PERSONAL:
        try:
            out = (await elevenlabs.synthesize(text, language_of(text)), elevenlabs.MEDIA_TYPE, PERSONAL)
            log(logger, 'speech_provider', provider='elevenlabs', voice_id=get_settings().elevenlabs_voice_id,
                model=elevenlabs.model_for(language_of(text)), language=language_of(text), message=str(m.id), bytes=len(out[0]))
        except AppError as e:
            http = (e.details or {}).get('provider_http')
            if strict or not get_settings().gemini_tts_model:
                log(logger, 'speech_provider', logging.WARNING, provider='none', wanted='elevenlabs', voice_id=get_settings().elevenlabs_voice_id,
                    http=http, reason=e.code, strict=strict, message=str(m.id))
                e.details = {**(e.details or {}), 'strict': strict}
                raise
            log(logger, 'speech_fallback', logging.WARNING, wanted='elevenlabs', voice_id=get_settings().elevenlabs_voice_id, http=http, reason=e.code,
                used='gemini', message=str(m.id))
            out = await _gemini(text, get_settings().gemini_tts_voice)  # keep a natural voice when ElevenLabs is unavailable
            log(logger, 'speech_provider', provider='gemini', voice=out[2], fallback_from='elevenlabs', message=str(m.id))
    else:
        out = await _gemini(text, v)
        log(logger, 'speech_provider', provider='gemini', voice=out[2], message=str(m.id))
    _CACHE[(str(m.id), out[2])] = out
    if len(_CACHE) > _CACHE_SIZE:
        _CACHE.popitem(last=False)
    return out
