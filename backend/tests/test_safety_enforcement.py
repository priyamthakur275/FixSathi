"""Server-side enforcement for free-text AI output: chat replies, spoken live replies and live steps cannot carry
power-sensitive instructions past a locked safety gate, and microwave internals are never allowed. No network calls."""
import asyncio, base64, json
import pytest
from google.genai import types
from sqlalchemy import select
from app.core.power_rules import instructs_power_work, mentions_microwave_internals, step_needs_power_off
from app.db.models import Conversation, SafetyEvent
from app.db.session import SessionLocal
from app.services import live
from tests.test_live import ORIGIN, FakeLive, recv_until

CONFIRM = {'power_off_confirmed': True, 'tester_checked': True}


# ---------- the shared rules ----------

@pytest.mark.parametrize('text', [
    'Open the canopy and check the capacitor.', 'Disconnect the capacitor wires and measure it with a multimeter.',
    'Remove the back panel.', 'Short the terminals with a screwdriver to discharge it.', 'Bypass the door switch.',
    'Canopy kholiye aur capacitor nikaal dijiye.', 'Before opening the cover, switch off. Then unscrew the cover.'])
def test_instructions_are_detected(text):
    assert instructs_power_work(text)


@pytest.mark.parametrize('text', [
    'Likely a weak capacitor or worn bearings.', 'Never open the microwave cabinet.', 'Do not touch the terminals.',
    'Before opening the canopy, switch off at the MCB and check with your tester.', 'Canopy kholne se pehle MCB off karo.',
    'Spin the blades by hand: do they turn freely?', 'Cover mat kholna.'])
def test_diagnosis_prohibitions_and_reminders_pass(text):
    assert not instructs_power_work(text)


def test_step_rule_is_broad_and_shared():
    from app.datasets import normalize as N
    from app.services import live as L
    assert step_needs_power_off('Check the capacitor') and step_needs_power_off('Probe the supply')
    assert N.POWER_WORDS is L.POWER_WORDS  # one definition everywhere
    assert mentions_microwave_internals('Remove the cover to reach the magnetron') and not mentions_microwave_internals('Never open the cabinet')


# ---------- chat ----------

def _chat(client, tech, sid, text='Fan is slow'):
    r = client.post(f'/api/v1/sessions/{sid}/messages', json={'text': text}, headers=tech['h'])
    assert r.status_code == 201, r.text
    return r.json()


def _assistant(sid):
    import uuid
    with SessionLocal() as db:
        return db.scalars(select(Conversation).where(Conversation.session_id == uuid.UUID(sid), Conversation.role == 'assistant')
                          .order_by(Conversation.created_at.desc())).first()


def test_chat_withholds_power_steps_while_locked(client, tech, session_id, fake):
    fake.text = 'Likely a weak capacitor.\n1. Spin the blades by hand.\n2. Unscrew the canopy and disconnect the capacitor wires.'
    _chat(client, tech, session_id)
    m = _assistant(session_id)
    assert 'Unscrew the canopy' not in m.message and 'disconnect' not in m.message  # never stored, so never shown
    assert 'weak capacitor' in m.message and 'Spin the blades' in m.message and 'Power-sensitive step withheld' in m.message
    assert m.meta['safety_withheld'] == 1 and m.meta['safety_reason'] == 'SAFETY_CONFIRMATION_REQUIRED'
    with SessionLocal() as db:
        ev = db.scalars(select(SafetyEvent).where(SafetyEvent.actor == 'chat')).all()
        assert ev and ev[-1].blocked


def test_chat_shows_power_steps_after_confirmation(client, tech, session_id, fake):
    client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json=CONFIRM, headers=tech['h'])
    fake.text = 'Unscrew the canopy and disconnect the capacitor wires.'
    _chat(client, tech, session_id)
    m = _assistant(session_id)
    assert m.message == 'Unscrew the canopy and disconnect the capacitor wires.' and m.meta['safety_withheld'] == 0
    with SessionLocal() as db:
        assert db.scalars(select(SafetyEvent).where(SafetyEvent.actor == 'chat', SafetyEvent.blocked.is_(False))).first()


def test_chat_keeps_safety_reminders(client, tech, session_id, fake):
    fake.text = 'Before opening the canopy, switch off at the MCB and check with your own tester. Never touch the terminals live.'
    _chat(client, tech, session_id)
    assert _assistant(session_id).message == fake.text


def test_chat_voice_channel_has_spoken_note(client, tech, session_id, fake):
    fake.text = 'Open the canopy and check the capacitor.'
    client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Fan slow', 'channel': 'voice'}, headers=tech['h'])
    m = _assistant(session_id)
    assert 'Open the canopy' not in m.message and '**' not in m.message and 'safety panel' in m.message


def test_chat_microwave_internals_always_escalated(client, tech, fake):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'microwave not heating', 'appliance_type': 'microwave_oven'}, headers=tech['h']).json()['id']
    client.post(f'/api/v1/sessions/{sid}/safety/confirm', json=CONFIRM, headers=tech['h'])  # even when unlocked
    fake.text = 'Check the door seal. Remove the outer cover and test the magnetron.'
    _chat(client, tech, sid, 'microwave not heating')
    m = _assistant(sid)
    assert 'magnetron' not in m.message.lower() and 'authorised service' in m.message and 'door seal' in m.message
    assert m.meta['microwave_escalated'] == 1


# ---------- live ----------

class ScriptedLive(FakeLive):
    script: list = []

    async def send_realtime_input(self, **kw):
        self.sent.append(kw)
        if kw.get('text') == 'go':
            for m in ScriptedLive.script:
                await self.q.put(m)


def _spoken(text, audio=True):
    SC, P = types.LiveServerContent, types.Part
    parts = [P(inline_data=types.Blob(data=b'\x01\x02', mime_type='audio/pcm;rate=24000'))] if audio else []
    return [types.LiveServerMessage(server_content=SC(model_turn=types.Content(parts=parts) if parts else None,
                                                      output_transcription=types.Transcription(text=text) if text else None)),
            types.LiveServerMessage(server_content=SC(turn_complete=True))]


@pytest.fixture
def scripted(fake):
    FakeLive.instances = []
    live.set_connector(lambda m, c: ScriptedLive(m, c)); yield ScriptedLive; live.set_connector(None)


def _run_live(client, tech, sid, script):
    ScriptedLive.script = script
    got = []
    with client.websocket_connect(f'/api/v1/live/{sid}', headers=ORIGIN) as ws:
        ws.send_text(json.dumps({'type': 'auth', 'token': tech['access_token']}))
        recv_until(ws, 'session_ready')
        ws.send_text(json.dumps({'type': 'text_input', 'text': 'go'}))
        while True:
            m = json.loads(ws.receive_text()); got.append(m)
            if m['type'] == 'turn_complete':
                break
        ws.send_text(json.dumps({'type': 'end_session'}))
        recv_until(ws, 'session_ended')
    return got


def test_live_spoken_power_step_withheld_while_locked(client, tech, session_id, scripted):
    got = _run_live(client, tech, session_id, _spoken('Unscrew the canopy and pull out the capacitor wires.'))
    types_ = [m['type'] for m in got]
    assert 'audio_chunk' not in types_  # the audio was never played
    assert not any('Unscrew' in (m.get('text') or '') for m in got)
    blocked = next(m for m in got if m['type'] == 'safety_blocked'); assert blocked['reason'] == 'SAFETY_CONFIRMATION_REQUIRED'
    assert any(s.get('text') == live.SAFETY_NUDGE for s in FakeLive.instances[-1].sent)
    with SessionLocal() as db:
        saved = ' '.join(c.message for c in db.scalars(select(Conversation).where(Conversation.role == 'assistant')))
        assert 'Unscrew' not in saved and 'safety panel' in saved
        assert db.scalars(select(SafetyEvent).where(SafetyEvent.actor == 'live', SafetyEvent.blocked.is_(True))).first()


def test_live_safe_reply_is_released_in_order(client, tech, session_id, scripted):
    got = _run_live(client, tech, session_id, _spoken('Spin the blades by hand and tell me if they turn freely.'))
    order = [m['type'] for m in got if m['type'] in ('audio_chunk', 'transcription', 'turn_complete')]
    assert order == ['audio_chunk', 'transcription', 'turn_complete'] or order == ['transcription', 'audio_chunk', 'turn_complete']
    assert base64.b64decode(next(m for m in got if m['type'] == 'audio_chunk')['data']) == b'\x01\x02'


def test_live_streams_power_step_after_confirmation(client, tech, session_id, scripted):
    client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json=CONFIRM, headers=tech['h'])
    got = _run_live(client, tech, session_id, _spoken('Now unscrew the canopy.'))
    assert any(m['type'] == 'audio_chunk' for m in got) and not any(m['type'] == 'safety_blocked' for m in got)


def test_live_unscreenable_audio_fails_closed(client, tech, session_id, scripted):
    got = _run_live(client, tech, session_id, _spoken('', audio=True))
    assert 'audio_chunk' not in [m['type'] for m in got]
    assert next(m for m in got if m['type'] == 'safety_blocked')['reason'] == 'UNSCREENED_AUDIO'


def test_live_give_step_microwave_internal_refused_even_when_unlocked(client, tech, scripted):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'microwave dead', 'appliance_type': 'microwave_oven'}, headers=tech['h']).json()['id']
    client.post(f'/api/v1/sessions/{sid}/safety/confirm', json=CONFIRM, headers=tech['h'])
    call = types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[types.FunctionCall(
        id='c1', name='give_step', args={'title': 'Check HV capacitor', 'instruction': 'Remove the cover and discharge the high-voltage capacitor', 'requires_power_off': True})]))
    got = _run_live(client, tech, sid, [call, types.LiveServerMessage(server_content=types.LiveServerContent(turn_complete=True))])
    assert next(m for m in got if m['type'] == 'safety_blocked')['reason'] == 'MICROWAVE_INTERNAL' and not any(m['type'] == 'step' for m in got)
    resp = FakeLive.instances[-1].tool_responses[0][0].response
    assert resp['allowed'] is False and 'authorised service' in resp['say']


# ---------- generated steps ----------

def test_generated_power_sensitive_kind_is_locked_even_without_keywords(client, tech, session_id, fake):
    fake.json['guidance'] = {'steps': [{'title': 'Check it', 'instruction': 'Look closely at the part', 'kind': 'power_sensitive', 'requires_power_off': False}]}
    client.post(f'/api/v1/sessions/{session_id}/diagnose', json={}, headers=tech['h'])
    steps = client.post(f'/api/v1/sessions/{session_id}/steps/generate', headers=tech['h']).json()
    assert steps[0]['requires_power_off'] and steps[0]['locked'] and steps[0]['instruction'] is None


def test_gemini_error_scrubs_new_key_format():
    from app.integrations.gemini.errors import scrub
    assert 'AQ.' not in scrub('bad key AQ.FAKE0000000000000000000000000000_test in request')


def test_chat_list_steps_use_broad_rule_real_reply(client, tech, session_id, fake):
    # Shape of a real Gemini reply that slipped past a verb-only check: "Lower the canopy ... to expose the capacitor housing."
    fake.text = ('Since the fan is humming and slow, a weak capacitor is the most likely cause.\n\n'
                 '1. **Access the capacitor:** Lower the canopy (the cover near the ceiling) to expose the capacitor housing.\n'
                 '2. **Check the regulator:** Try the fan at every regulator setting and note the speed.\n'
                 '3. **Check the rating:** Note the microfarad rating printed on the existing capacitor.')
    _chat(client, tech, session_id)
    m = _assistant(session_id).message
    assert 'Lower the canopy' not in m and 'expose' not in m and 'microfarad' not in m
    assert 'weak capacitor is the most likely cause' in m and 'every regulator setting' in m
    assert m.count('power-sensitive step withheld') == 2


def test_multi_id_citation_brackets_are_validated():
    from app.services.ai import _clean_citations
    text, used, invented = _clean_citations('Weak capacitor [fixsaathi:fan_slow_hum, mfr:made-up, 57].', {'fixsaathi:fan_slow_hum'})
    assert text == 'Weak capacitor [fixsaathi:fan_slow_hum].' and used == ['fixsaathi:fan_slow_hum'] and invented == ['mfr:made-up', '57']


def test_consecutive_withheld_steps_collapse(client, tech, session_id, fake):
    fake.text = '1. Open the canopy.\n2. Disconnect the capacitor.\n3. Fit the new capacitor.'
    _chat(client, tech, session_id)
    m = _assistant(session_id).message
    assert m.count('power-sensitive step withheld: see') == 1 and 'canopy' not in m


# ---------- causes stay visible, only power work is withheld (live replies 21 Nov hid whole cause lists) ----------

FRIDGE_REPLY = ('A clicking sound from the compressor usually means the overload protector (OLP) is tripping.\n\n'
                '**Likely Causes:**\n'
                '1. **Faulty PTC starter relay or OLP** (burnt or cracked ceramic disc).\n'
                '2. **Weak start capacitor** on the compressor terminals.\n'
                '3. **Low supply voltage** under load.\n\n'
                '**Step-by-Step Checks:**\n'
                '1. Listen for the compressor clicking every few minutes and note the interval.\n'
                '2. Note any error code on the display panel.\n'
                '3. Unplug the fridge, remove the relay cover and pull the PTC relay off the compressor terminals.\n'
                '4. Measure the relay with a multimeter for continuity.\n\n'
                'Check the relay first and tell me if it rattles!')


def test_chat_cause_list_stays_visible_while_power_steps_are_withheld(client, tech, session_id, fake):
    fake.text = FRIDGE_REPLY
    _chat(client, tech, session_id, 'Fridge not cooling, compressor clicks')
    m = _assistant(session_id)
    # suspected causes and the diagnosis: visible
    for kept in ('Faulty PTC starter relay or OLP', 'Weak start capacitor', 'Low supply voltage', 'overload protector (OLP) is tripping'):
        assert kept in m.message, kept
    # safe, non-electrical checks: visible
    assert 'Listen for the compressor clicking' in m.message and 'error code on the display panel' in m.message
    # power-sensitive work: withheld on the server and never stored
    assert 'pull the PTC relay off' not in m.message and 'multimeter' not in m.message and 'remove the relay cover' not in m.message
    assert 'Check the relay first' not in m.message  # reaching the relay means opening the compressor terminal cover
    assert m.message.count('power-sensitive step withheld: see') == 2 and 'Power-sensitive step withheld' in m.message
    assert m.meta['safety_withheld'] == 3 and m.meta['safety_reason'] == 'SAFETY_CONFIRMATION_REQUIRED'


def test_chat_cause_list_without_heading_and_inline_instruction(client, tech, session_id, fake):
    fake.text = ('Here are the most likely causes to check:\n'
                 '- Worn drive belt or seized drum bearing.\n'
                 '- Faulty motor capacitor — measure it with a multimeter after discharging it.\n'
                 '- Stuck door lock.\n\n'
                 'Next steps:\n'
                 '- Spin the drum by hand with the machine unplugged.\n'
                 '- Remove the back panel and check the belt.')
    _chat(client, tech, session_id, 'Washer drum not spinning, motor hums')
    m = _assistant(session_id).message
    assert 'Worn drive belt or seized drum bearing' in m and 'Faulty motor capacitor —' in m and 'Stuck door lock' in m
    assert 'Spin the drum by hand' in m
    assert 'discharging' not in m and 'Remove the back panel' not in m


def test_fault_named_items_are_causes_even_without_a_heading(client, tech, session_id, fake):
    fake.text = '1. Weak capacitor.\n2. Worn bearings.\n3. Open the canopy and replace the capacitor.'
    _chat(client, tech, session_id)
    m = _assistant(session_id).message
    assert 'Weak capacitor.' in m and 'Worn bearings.' in m and 'Open the canopy' not in m


def test_checking_a_live_part_in_prose_is_withheld(client, tech, session_id, fake):
    fake.text = 'A weak capacitor is the likely cause. Check the capacitor terminals for burn marks.'
    _chat(client, tech, session_id)
    m = _assistant(session_id).message
    assert 'weak capacitor is the likely cause' in m and 'burn marks' not in m and 'Power-sensitive step withheld' in m


def test_cause_list_full_reply_after_both_confirmations(client, tech, session_id, fake):
    client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json=CONFIRM, headers=tech['h'])
    fake.text = FRIDGE_REPLY
    _chat(client, tech, session_id, 'Fridge not cooling')
    m = _assistant(session_id)
    assert m.message == FRIDGE_REPLY and m.meta['safety_withheld'] == 0


def test_one_confirmation_is_not_enough(client, tech, session_id, fake):
    client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json={'power_off_confirmed': True, 'tester_checked': False}, headers=tech['h'])
    fake.text = FRIDGE_REPLY
    _chat(client, tech, session_id, 'Fridge not cooling')
    m = _assistant(session_id).message
    assert 'multimeter' not in m and 'Faulty PTC starter relay' in m


@pytest.mark.parametrize('text', ['Note the error code on the display panel.', 'Listen for the compressor clicking.',
                                  'Spin the blades by hand.', 'Check the regulator at every setting.', 'Watch whether the compressor starts after the click.'])
def test_safe_steps_pass_the_step_rule(text):
    from app.core.power_rules import step_text_needs_power_off
    assert not step_text_needs_power_off(text)


@pytest.mark.parametrize('text', ['Note the microfarad rating printed on the existing capacitor.', 'Tighten the motor mounting bolts.',
                                  'Feel whether the compressor body is hot.', 'Check the wiring at the terminal block.',
                                  'Lower the canopy to expose the capacitor housing.', 'Never open the cabinet, then touch the board.',
                                  'Unplug the PTC starter from the compressor and shake it.', 'Clean the drain pump filter at the front.',
                                  'Look inside the motor housing for burn marks.'])
def test_power_steps_fail_the_step_rule(text):
    from app.core.power_rules import step_text_needs_power_off
    assert step_text_needs_power_off(text)


LIVE_REPLY_21_NOV = (  # gemini-3.6-flash, verbatim shape: causes as bold items, what-to-do as indented sub-items
    'When the compressor clicks every few minutes, it usually means the compressor is tripping on the overload protector (OLP).\n\n'
    '**Safety First:** Before removing the terminal cover or touching any wiring, switch off at the MCB and test with your meter.\n\n'
    'Here are the most likely causes and what to check:\n\n'
    '1. **Defective Start Relay / PTC Starter:** \n'
    ' - Unplug the PTC starter from the compressor and shake it. If it rattles inside, the ceramic disc is shattered and needs replacement.\n'
    '2. **Faulty Run Capacitor (if fitted):** \n'
    ' - Check the capacitor for bulging or leaking oil.\n'
    '3. **Incorrect Supply Voltage:** \n'
    ' - Check the socket voltage with the fridge running. Low voltage prevents the compressor from starting.\n'
    '4. **Seized / Locked Rotor Compressor:** \n'
    ' - Measure the winding resistance between the C, S and R pins.')


def test_live_reply_causes_visible_and_sub_item_instructions_withheld(client, tech, session_id, fake):
    fake.text = LIVE_REPLY_21_NOV
    _chat(client, tech, session_id, 'Fridge compressor clicks')
    m = _assistant(session_id).message
    for kept in ('Defective Start Relay / PTC Starter', 'Faulty Run Capacitor', 'Incorrect Supply Voltage', 'Seized / Locked Rotor Compressor',
                 'tripping on the overload protector'):
        assert kept in m, kept
    for gone in ('Unplug the PTC starter', 'shake it', 'bulging or leaking', 'winding resistance'):
        assert gone not in m, gone
