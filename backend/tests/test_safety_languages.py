"""Safety screening only reads English, Hinglish and Devanagari Hindi. Replies in other scripts (Kannada, Tamil...) cannot be
checked, so while the power is locked they are withheld, and the AI is asked to answer in English instead. No network calls."""
import pytest
from app.core.power_rules import instructs_power_work, mentions_microwave_internals, step_needs_power_off, step_text_needs_power_off, unscreenable
from tests.test_safety_enforcement import CONFIRM, _assistant, _chat

KANNADA_STEP = 'ಕ್ಯಾನೋಪಿ ತೆಗೆದು ಕೆಪಾಸಿಟರ್ ವೈರ್‌ಗಳನ್ನು ಬಿಚ್ಚಿ.'  # "remove the canopy and disconnect the capacitor wires"
TAMIL_STEP = 'கேனோபியைத் திறந்து கெபாசிட்டர் வயர்களை அவிழ்க்கவும்.'


@pytest.mark.parametrize('text', [KANNADA_STEP, TAMIL_STEP, 'ক্যাপাসিটর খুলুন', 'కెపాసిటర్ తీసివేయండి'])
def test_unreadable_scripts_are_power_sensitive(text):
    assert unscreenable(text)
    assert instructs_power_work(text) and step_text_needs_power_off(text) and step_needs_power_off(text)
    assert mentions_microwave_internals(text)


@pytest.mark.parametrize('text', ['Spin the blades by hand.', 'पंखे को हाथ से घुमाकर देखें।', 'Pankha haath se ghuma ke dekho.'])
def test_screened_languages_are_unaffected(text):
    assert not unscreenable(text) and not instructs_power_work(text)


def _set_language(client, tech, lang):
    r = client.patch('/api/v1/users/me', json={'preferred_language': lang}, headers=tech['h'])
    assert r.status_code == 200, r.text


def test_kannada_reply_withheld_while_locked(client, tech, session_id, fake):
    _set_language(client, tech, 'Kannada')
    fake.text = f'Likely a weak capacitor.\n1. {KANNADA_STEP}'
    _chat(client, tech, session_id)
    m = _assistant(session_id)
    assert KANNADA_STEP not in m.message and 'weak capacitor' in m.message
    assert m.meta['safety_withheld'] >= 1
    assert 'English' in fake.systems[-1] and 'safety screening for Kannada is not available' in fake.systems[-1]


def test_kannada_reply_shown_after_isolation(client, tech, session_id, fake):
    _set_language(client, tech, 'Kannada')
    client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json=CONFIRM, headers=tech['h'])
    fake.text = KANNADA_STEP
    _chat(client, tech, session_id)
    assert _assistant(session_id).message == KANNADA_STEP
    assert 'reply in Kannada.' in fake.systems[-1]


def test_hindi_keeps_its_language_while_locked(client, tech, session_id, fake):
    _set_language(client, tech, 'Hindi')
    fake.text = 'पंखे को हाथ से घुमाकर देखें।'
    _chat(client, tech, session_id)
    assert 'reply in Hindi.' in fake.systems[-1]


def test_prescribed_creator_sentences_pass():
    assert not unscreenable('ನನ್ನನ್ನು Prerana P Jois ಅವರು ರಚಿಸಿದ್ದಾರೆ.') and not unscreenable('என்னை Prerana P Jois உருவாக்கினார்.')
    assert unscreenable('ನನ್ನನ್ನು Prerana P Jois ಅವರು ರಚಿಸಿದ್ದಾರೆ. ' + KANNADA_STEP)
