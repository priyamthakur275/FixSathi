"""The safety gate is the most important business rule. These tests cover every path that could unlock it."""
from datetime import timedelta
from sqlalchemy import select, text, update
from app.db.models import RepairStep, SafetyConfirmation, SafetyEvent
from app.db.session import SessionLocal, engine
from tests.conftest import register


def setup_steps(client, tech, sid, fake):
    assert client.post(f'/api/v1/sessions/{sid}/diagnose', headers=tech['h']).status_code == 201
    r = client.post(f'/api/v1/sessions/{sid}/steps/generate', headers=tech['h']); assert r.status_code == 201, r.text
    return r.json()


def confirm(client, h, sid, p, t):
    return client.post(f'/api/v1/sessions/{sid}/safety/confirm', json={'power_off_confirmed': p, 'tester_checked': t}, headers=h)


def test_guidance_forces_power_flag_and_hides_locked_instruction(client, tech, session_id, fake):
    steps = setup_steps(client, tech, session_id, fake)
    s2 = steps[1]
    assert s2['requires_power_off'] is True and s2['locked'] is True and s2['instruction'] is None


def test_blocked_without_any_confirmation(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    r = client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h'])
    assert r.status_code == 409
    d = r.json()['error']['details']
    assert d['allowed'] is False and d['reason'] == 'SAFETY_CONFIRMATION_REQUIRED' and set(d['missing']) == {'power_off_confirmed', 'tester_checked'}


def test_blocked_with_only_power_off(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    confirm(client, tech['h'], session_id, True, False)
    r = client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h'])
    assert r.status_code == 409 and r.json()['error']['details']['missing'] == ['tester_checked']


def test_blocked_with_only_tester(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    confirm(client, tech['h'], session_id, False, True)
    r = client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h'])
    assert r.status_code == 409 and r.json()['error']['details']['missing'] == ['power_off_confirmed']


def test_allowed_only_with_both(client, tech, session_id, fake):
    s1, s2 = setup_steps(client, tech, session_id, fake)
    assert client.post(f"/api/v1/sessions/{session_id}/steps/{s1['id']}/complete", headers=tech['h']).status_code == 200  # safe step never needs it
    st = confirm(client, tech['h'], session_id, True, True).json()
    assert st['unlocked'] is True and 'cannot measure voltage' in st['disclaimer']
    r = client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h'])
    assert r.status_code == 200 and r.json()['status'] == 'completed'


def test_withdrawing_relocks(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    confirm(client, tech['h'], session_id, True, True); confirm(client, tech['h'], session_id, True, False)
    assert client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h']).status_code == 409


def test_cross_session_confirmation_does_not_unlock(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    other = client.post('/api/v1/sessions', json={'issue_description': 'another fan'}, headers=tech['h']).json()['id']
    assert confirm(client, tech['h'], other, True, True).json()['unlocked'] is True
    assert client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h']).status_code == 409


def test_cross_user_cannot_confirm_or_unlock(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    intruder = register(client, org='Acme Service')
    assert confirm(client, intruder['h'], session_id, True, True).status_code == 404
    # even a row forged directly in the DB for another user does not count
    with SessionLocal() as db:
        db.add(SafetyConfirmation(session_id=session_id, technician_id=intruder['user']['id'], power_off_confirmed=True, tester_checked=True)); db.commit()
    assert client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h']).status_code == 409


def test_stale_confirmation_expires(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    confirm(client, tech['h'], session_id, True, True)
    with engine().begin() as c:
        c.execute(text("update safety_confirmations set confirmed_at = confirmed_at - interval '3 hours'"))
    r = client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h'])
    assert r.status_code == 409 and r.json()['error']['details']['reason'] == 'SAFETY_CONFIRMATION_EXPIRED'
    assert client.get(f'/api/v1/sessions/{session_id}/safety', headers=tech['h']).json()['expired'] is True


def test_blocked_attempts_are_logged(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h'])
    client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", headers=tech['h'])
    ev = client.get(f'/api/v1/sessions/{session_id}/safety/events', headers=tech['h']).json()
    blocked = [e for e in ev if e['blocked']]
    assert len(blocked) == 2 and all(e['actor'] == 'api' and e['reason'] == 'SAFETY_CONFIRMATION_REQUIRED' for e in blocked)


def test_frontend_flags_are_ignored(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    r = client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/complete", json={'power_off_confirmed': True, 'tester_checked': True, 'allowed': True}, headers=tech['h'])
    assert r.status_code == 409


def test_step_visual_for_power_step_is_gated(client, tech, session_id, fake):
    s2 = setup_steps(client, tech, session_id, fake)[1]
    assert client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/visual", headers=tech['h']).status_code == 409
    confirm(client, tech['h'], session_id, True, True)
    r = client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/visual", headers=tech['h'])
    assert r.status_code == 201 and r.json()['kind'] == 'generated' and 'not a photo' in r.json()['meta']['label']
    again = client.post(f"/api/v1/sessions/{session_id}/steps/{s2['id']}/visual", headers=tech['h'])
    assert again.json()['id'] == r.json()['id']  # not regenerated


def test_ai_tool_cannot_bypass(client, tech, session_id, fake):
    """The live tool `give_step` is the model's only way to issue a step. It must hit the same gate."""
    import asyncio
    from app.services.live import LiveContext, run_tool
    ctx = LiveContext(session_id=__import__('uuid').UUID(session_id), user_id=__import__('uuid').UUID(tech['user']['id']))
    events = []

    async def emit(m): events.append(m)
    # model lies: says no power-off needed for a step that opens the canopy
    r = asyncio.run(run_tool(ctx, 'give_step', {'title': 'Open canopy', 'instruction': 'Remove the canopy cover and check the capacitor', 'requires_power_off': False}, emit))
    assert r['allowed'] is False and events[-1]['type'] == 'safety_blocked'
    # model has no tool that can record confirmations
    r = asyncio.run(run_tool(ctx, 'request_safety_confirmation', {}, emit))
    assert r['unlocked'] is False and events[-1]['type'] == 'safety_confirmation_required'
    r = asyncio.run(run_tool(ctx, 'confirm_safety', {'power_off_confirmed': True, 'tester_checked': True}, emit))
    assert 'error' in r
    assert client.get(f'/api/v1/sessions/{session_id}/safety', headers=tech['h']).json()['unlocked'] is False
    confirm(client, tech['h'], session_id, True, True)
    r = asyncio.run(run_tool(ctx, 'give_step', {'title': 'Open canopy', 'instruction': 'Remove the canopy cover', 'requires_power_off': False}, emit))
    assert r['allowed'] is True and events[-1]['type'] == 'step' and events[-1]['step']['requires_power_off'] is True
    with SessionLocal() as db:
        actors = {e.actor for e in db.scalars(select(SafetyEvent).where(SafetyEvent.event_type == 'action_blocked'))}
    assert actors == {'ai_tool'}
