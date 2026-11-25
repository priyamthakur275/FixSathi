"""Phrasings found by the offline safety evaluation (scripts/evaluate.py)."""
from app.core.power_rules import instructs_power_work


def test_take_part_out_is_withheld():
    for t in ('Take the regulator out of the switchboard and test it.', 'Take the PCB out.', 'Take out the capacitor.', 'Take it apart.'):
        assert instructs_power_work(t), t


def test_everyday_take_out_stays_readable():
    for t in ('Take the plug out of the socket.', 'Take the food out and stir it.', 'Take the filter out and wash it.'):
        assert not instructs_power_work(t), t


def test_live_voltage_checks_are_withheld():
    for t in ('Check the voltage across the compressor terminals.', 'Test the voltage between the two wires.'):
        assert instructs_power_work(t), t
    assert not instructs_power_work('Never check the voltage across the terminals with bare hands.')


# Found by the answer-quality run on the live app: a Hindi reply told the technician to open the canopy and measure
# voltage while power was locked, because the rules only read Latin script.
import pytest  # noqa: E402
from app.core.power_rules import instructs_power_work as _iw, step_text_needs_power_off as _step  # noqa: E402


@pytest.mark.parametrize('text', [
    'कैनोपी खोलकर चेक करें कि वायर टर्मिनल ब्लॉक से सही से कनेक्टेड हैं या ढीले तो नहीं हैं ।',
    'मल्टीमीटर से लाइन और न्यूट्रल के बीच वोल्टेज (230V AC) चेक करें।',
    'कैपेसिटर बदल दें।',
    'पुराना तार काटकर नया जोड़ें।',
])
def test_devanagari_live_work_is_withheld(text):
    assert _iw(text) and _step(text)


@pytest.mark.parametrize('text', [
    'पंखे को खोलने या तारों को छूने से पहले MCB/मेन स्विच बंद करें और अपने टेस्टर से वोल्टेज न होने की पुष्टि करें।',
    'तारों को कभी मत छुएं।',
    'उसी बोर्ड में दूसरा उपकरण चलाकर देखें कि मेन स्विच और फ़्यूज़/MCB ठीक है या नहीं ।',
    'क्या आपको कैनोपी टर्मिनल पर 230V सप्लाई मिल रही है?',
])
def test_devanagari_safety_reminders_and_questions_pass(text):
    assert not _iw(text)


def test_wire_used_as_a_tool_is_not_a_live_part():
    assert not _step('2. Clear the drain pipe with a thin wire or blow through it.')
    assert _step('Check the wires at the terminal block.')
    assert _step('Tighten the loose wire on the capacitor.')
