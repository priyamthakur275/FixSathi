"""Creator identity: part of the server-side system prompts (chat, voice-channel chat and Gemini Live), in every language."""
import os
import pytest
from app.agents import prompts
from app.services import live

QUESTIONS = {
    'English': ['Who created you?', 'Who made you?', 'Who is your developer?', 'Who built FixSaathi?', 'Who is behind FixSaathi?'],
    'Tamil': ['உன்னை உருவாக்கியது யார்?', 'FixSaathi-ஐ உருவாக்கியது யார்?'],
    'Kannada': ['ನಿನ್ನನ್ನು ಯಾರು ರಚಿಸಿದರು?', 'FixSaathi ಅನ್ನು ಯಾರು ನಿರ್ಮಿಸಿದರು?'],
    'Hindi': ['तुम्हें किसने बनाया?', 'FixSaathi को किसने बनाया?'],
    'Hinglish': ['Tumhe kisne banaya?', 'FixSaathi ke peeche kaun hai?'],
}
CASES = [(lang, q) for lang, qs in QUESTIONS.items() for q in qs]
LANG_SETTING = {'English': 'English', 'Tamil': 'Tamil', 'Kannada': 'Kannada', 'Hindi': 'Hindi', 'Hinglish': 'Hindi'}


def _rule_in(system: str):
    assert "gets exactly 'I was created by Prerana P Jois.'" in system
    assert "gets exactly 'FixSaathi was created by Prerana P Jois.'" in system
    assert "exactly as 'Prerana P Jois'" in system and 'Never name any other creator' in system
    assert "FixSaathi uses Google's Gemini AI" in system  # the creator is not the AI provider


@pytest.mark.parametrize('language', ['English', 'Hindi', 'Kannada', 'Tamil'])
def test_identity_is_in_every_system_prompt(language):
    _rule_in(prompts.CHAT_SYSTEM.format(language=language))
    _rule_in(prompts.LIVE_SYSTEM.format(language=language))
    _rule_in(live.build_config(language).system_instruction)  # the actual Gemini Live session config


def test_identity_names_only_the_creator():
    assert prompts.CREATOR == 'Prerana P Jois'
    assert prompts.IDENTITY.count('Prerana P Jois') == 8 and '{' not in prompts.IDENTITY


@pytest.mark.parametrize('lang,question', CASES)
@pytest.mark.parametrize('channel', ['text', 'voice'])
def test_creator_question_reaches_the_model_with_the_rule(client, tech, session_id, fake, lang, question, channel):
    client.patch('/api/v1/users/me', json={'preferred_language': LANG_SETTING[lang]}, headers=tech['h'])
    fake.text = 'I was created by Prerana P Jois.'
    r = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': question, 'channel': channel}, headers=tech['h'])
    assert r.status_code == 201, r.text
    _rule_in(fake.systems[-1])
    assert f'reply in {LANG_SETTING[lang]}' in fake.systems[-1]
    assert r.json()['assistant_message']['message'] == 'I was created by Prerana P Jois.'  # passes the safety screen unchanged


# ---- opt-in: the real Gemini model, with the real system prompt. FIXSAATHI_LIVE_TESTS=1 pytest tests/test_identity.py ----

LIVE = pytest.mark.skipif(os.environ.get('FIXSAATHI_LIVE_TESTS') != '1', reason='set FIXSAATHI_LIVE_TESTS=1 to call Gemini')


@pytest.fixture
def real_gemini(monkeypatch):
    """The suite blanks the key (conftest), so ordinary runs never call Google. Live tests read backend/.env instead."""
    from pathlib import Path
    from app.config import get_settings
    env = dict(l.split('=', 1) for l in (Path(__file__).parent.parent / '.env').read_text().splitlines() if '=' in l and not l.startswith('#'))
    s = get_settings()
    for k in ('GEMINI_API_KEY', 'GEMINI_AGENT_MODEL', 'GEMINI_AGENT_FALLBACK_MODELS'):
        monkeypatch.setattr(s, k.lower(), env.get(k, '').strip() or None)
    if not s.gemini_api_key:
        pytest.skip('no GEMINI_API_KEY in backend/.env')


async def _ask(question: str, language: str) -> str:
    from app.integrations.gemini.client import GeminiClient
    text, _ = await GeminiClient().generate_text('chat', [question], prompts.CHAT_SYSTEM.format(language=language))
    return text


@LIVE
@pytest.mark.parametrize('lang,question', [('English', 'Who created you?'), ('English', 'Who built FixSaathi?'), ('Tamil', 'உன்னை உருவாக்கியது யார்?'),
                                           ('Kannada', 'ನಿನ್ನನ್ನು ಯಾರು ರಚಿಸಿದರು?'), ('Hindi', 'तुम्हें किसने बनाया?'), ('Hindi', 'Tumhe kisne banaya?')])
def test_live_model_names_the_creator(real_gemini, lang, question):
    import asyncio
    answer = asyncio.run(_ask(question, lang))
    print(f'\n{lang} | {question} -> {answer}')
    assert 'Prerana P Jois' in answer
    if question == 'Who created you?':
        assert answer == 'I was created by Prerana P Jois.', answer
    if question == 'Who built FixSaathi?':
        assert answer == 'FixSaathi was created by Prerana P Jois.', answer
    if question == 'Tumhe kisne banaya?':  # Hinglish or Devanagari: the script follows the general language rule, not this one
        assert answer.startswith(('Mujhe Prerana P Jois ne banaya hai', 'मुझे Prerana P Jois ने बनाया है')), answer
    if 'FixSaathi' not in question:  # a question about "you" keeps the first-person form, in every language
        assert not answer.startswith('FixSaathi'), answer
    assert not any(w in answer for w in ('प्रेरणा', 'ಪ್ರೇರಣಾ', 'பிரேரணா')), answer  # never transliterated
    for other in ('Google created', 'created by Google', 'OpenAI', 'Anthropic', 'DeepMind'):
        assert other.lower() not in answer.lower()


@LIVE
@pytest.mark.parametrize('attempt', [1, 2, 3])
def test_live_answer_is_consistent(real_gemini, attempt):
    import asyncio
    answer = asyncio.run(_ask('Who created you?', 'English'))
    print(f'\nattempt {attempt}: Who created you? -> {answer}')
    assert answer == 'I was created by Prerana P Jois.', answer


@LIVE
def test_live_model_separates_creator_from_ai_provider(real_gemini):
    import asyncio
    answer = asyncio.run(_ask('Which AI model powers you?', 'English'))
    print(f'\nWhich AI model powers you? -> {answer}')
    assert 'Gemini' in answer
