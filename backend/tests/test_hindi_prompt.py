"""Hindi quality pass: spoken Hindi/Hinglish with everyday technician part names and server safety intact."""
from app.agents import prompts
from app.services.safety import LOCK_NOTE, WITHHELD_MARK


def test_hindi_prompts_use_spoken_part_names_and_keep_identity():
    chat_sys = prompts.CHAT_SYSTEM.format(language='Hindi')
    live_sys = prompts.LIVE_SYSTEM.format(language='Hindi')

    for sys_txt in (chat_sys, live_sys):
        assert prompts.CREATOR in sys_txt
        for part in ('capacitor', 'PCB', 'MCB', 'compressor', 'relay', 'thermostat', 'drain pipe', 'tester', 'multimeter'):
            assert part in sys_txt
        assert 'spoken Hindi' in sys_txt

    assert 'reply in Hindi' in chat_sys
    assert 'संधारित्र' in chat_sys and 'परिपथ' in chat_sys  # explicitly listed as formal terms to avoid


def test_hindi_chat_sends_spoken_hindi_rule_and_enforces_safety_lock(client, tech, session_id, fake):
    client.patch('/api/v1/users/me', json={'preferred_language': 'Hindi'}, headers=tech['h'])
    fake.text = 'कैपेसिटर कमजोर हो सकता है।\n1. कैनोपी खोल कर कैपेसिटर का तार निकालें।'

    locked_res = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'पंखा धीरे चल रहा है'}, headers=tech['h'])
    assert locked_res.status_code == 201
    sys_used = fake.systems[-1]
    assert 'reply in Hindi' in sys_used and 'drain pipe' in sys_used
    msg_locked = locked_res.json()['assistant_message']['message']
    assert 'कैपेसिटर कमजोर हो सकता है।' in msg_locked
    assert 'खोल कर' not in msg_locked
    assert WITHHELD_MARK in msg_locked and LOCK_NOTE in msg_locked

    client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json={'power_off_confirmed': True, 'tester_checked': True}, headers=tech['h'])
    unlocked_res = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'MCB बंद करके टेस्टर से चेक कर लिया'}, headers=tech['h'])
    assert unlocked_res.status_code == 201
    msg_unlocked = unlocked_res.json()['assistant_message']['message']
    assert 'कैनोपी खोल कर कैपेसिटर का तार निकालें।' in msg_unlocked
    assert WITHHELD_MARK not in msg_unlocked
