import io, uuid
from pypdf import PdfReader
from app.api.v1.sessions import wants_pdf
from app.db.models import RepairSession
from app.db.session import SessionLocal
from app.services.sessions import chat_title
from tests.conftest import make_role, register


def _new(client, tech, text, appliance=None):
    r = client.post('/api/v1/sessions', json={'issue_description': text, 'appliance_type': appliance}, headers=tech['h'])
    assert r.status_code == 201, r.text
    return r.json()


def _pdf_text(content: bytes) -> str:
    return '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(content)).pages)


def test_chat_titles_are_short_and_meaningful():
    assert chat_title('My ceiling fan is not rotating', 'ceiling_fan') == 'Ceiling Fan Not Rotating'
    assert chat_title('LG split AC showing CH38, not cooling', 'split_ac') == 'LG Split AC Showing CH38'
    assert chat_title("The fridge isn't cooling at all since yesterday.", 'refrigerator') == 'Fridge Not Cooling'
    assert chat_title('hi', 'washing_machine') == 'Washing machine repair'
    assert chat_title('hey', 'unknown') == 'New chat'


def test_new_sessions_get_a_readable_title_and_photo_first_chats_are_named_later(client, tech):
    assert _new(client, tech, 'Washing machine is not draining water')['title'] == 'Washing Machine Not Draining Water'
    s = _new(client, tech, '', 'ceiling_fan')
    assert s['title'] == 'Ceiling fan repair'
    client.post(f"/api/v1/sessions/{s['id']}/messages", json={'text': 'Fan is making a humming noise'}, headers=tech['h'])
    assert client.get(f"/api/v1/sessions/{s['id']}", headers=tech['h']).json()['title'] == 'Fan Making Humming Noise'


def test_a_chat_opened_with_small_talk_is_named_by_the_first_real_fault(client, tech):
    s = _new(client, tech, 'hey')
    assert s['title'] == 'New chat'
    client.post(f"/api/v1/sessions/{s['id']}/messages", json={'text': 'ok'}, headers=tech['h'])
    assert client.get(f"/api/v1/sessions/{s['id']}", headers=tech['h']).json()['title'] == 'New chat'
    client.post(f"/api/v1/sessions/{s['id']}/messages", json={'text': 'LG split AC showing CH38, not cooling'}, headers=tech['h'])
    got = client.get(f"/api/v1/sessions/{s['id']}", headers=tech['h']).json()
    assert got['title'] == 'LG Split AC Showing CH38' and got['appliance_type'] == 'split_ac'
    client.post(f"/api/v1/sessions/{s['id']}/messages", json={'text': 'fridge also making noise now'}, headers=tech['h'])
    assert client.get(f"/api/v1/sessions/{s['id']}", headers=tech['h']).json()['title'] == 'LG Split AC Showing CH38'  # named once


def test_chats_named_before_this_rule_are_renamed_too(client, tech):
    from sqlalchemy import text
    from tests.conftest import engine
    s = _new(client, tech, 'hey')
    with engine().begin() as c:
        c.execute(text("update repair_sessions set title='Appliance Repair' where id=:i"), {'i': s['id']})
    client.post(f"/api/v1/sessions/{s['id']}/messages", json={'text': 'Washing machine is not draining water'}, headers=tech['h'])
    assert client.get(f"/api/v1/sessions/{s['id']}", headers=tech['h']).json()['title'] == 'Washing Machine Not Draining Water'


def test_a_title_the_technician_typed_is_never_replaced(client, tech):
    s = _new(client, tech, 'hey')
    client.patch(f"/api/v1/sessions/{s['id']}", json={'title': 'New chat'}, headers=tech['h'])
    client.post(f"/api/v1/sessions/{s['id']}/messages", json={'text': 'Washing machine is not draining water'}, headers=tech['h'])
    assert client.get(f"/api/v1/sessions/{s['id']}", headers=tech['h']).json()['title'] == 'New chat'


def test_search_finds_titles_and_message_text_and_is_scoped(client, tech):
    a = _new(client, tech, 'Refrigerator cooling problem')
    b = _new(client, tech, 'Ceiling fan not rotating')
    client.post(f"/api/v1/sessions/{b['id']}/messages", json={'text': 'capacitor looks swollen'}, headers=tech['h'])
    ids = lambda q: [x['id'] for x in client.get(f'/api/v1/sessions?mine=true&q={q}', headers=tech['h']).json()['items']]  # noqa: E731
    assert ids('refrigerator') == [a['id']]
    assert ids('SWOLLEN') == [b['id']]
    assert ids('100%25') == []  # LIKE wildcards are matched literally
    other = register(client, org='Acme Service')
    assert client.get('/api/v1/sessions?q=fan', headers=other['h']).json()['total'] == 0


def test_mine_lists_only_own_conversations_for_a_manager(client, tech, session_id):
    m = register(client, org='Acme Service'); make_role(m['user']['id'], 'manager')
    assert client.get('/api/v1/sessions', headers=m['h']).json()['total'] == 1  # team view unchanged
    assert client.get('/api/v1/sessions?mine=true', headers=m['h']).json()['total'] == 0


def test_rename_works_on_closed_conversations_but_other_edits_do_not(client, tech, session_id):
    client.post(f'/api/v1/sessions/{session_id}/cancel', headers=tech['h'])
    r = client.patch(f'/api/v1/sessions/{session_id}', json={'title': '  Hall   fan  '}, headers=tech['h'])
    assert r.status_code == 200 and r.json()['title'] == 'Hall fan'
    assert client.patch(f'/api/v1/sessions/{session_id}', json={'title': 'x', 'issue_description': 'y'}, headers=tech['h']).status_code == 409
    other = register(client, org='Acme Service')
    assert client.patch(f'/api/v1/sessions/{session_id}', json={'title': 'mine'}, headers=other['h']).status_code == 404


def test_delete_hides_the_chat_but_keeps_records(client, tech, session_id):
    client.post(f'/api/v1/sessions/{session_id}/escalate', json={'reason': 'Burnt smell from canopy'}, headers=tech['h'])
    other = register(client, org='Acme Service')
    assert client.delete(f'/api/v1/sessions/{session_id}', headers=other['h']).status_code == 404
    assert client.delete(f'/api/v1/sessions/{session_id}', headers=tech['h']).status_code == 204
    assert client.get('/api/v1/sessions?mine=true', headers=tech['h']).json()['total'] == 0
    assert client.get(f'/api/v1/sessions/{session_id}', headers=tech['h']).status_code == 404  # gone as a chat
    assert client.get(f'/api/v1/sessions/{session_id}/messages', headers=tech['h']).status_code == 404
    with SessionLocal() as db:
        s = db.get(RepairSession, uuid.UUID(session_id))
        assert s is not None and s.hidden_at is not None and s.status == 'cancelled'  # kept, and closed rather than left 'active'
    assert len(client.get('/api/v1/escalations', headers=tech['h']).json()) == 1  # records kept
    assert client.get('/api/v1/history', headers=tech['h']).json()['total'] == 1
    assert client.delete(f'/api/v1/sessions/{session_id}', headers=tech['h']).status_code == 204  # idempotent


def test_pdf_intent():
    for t in ('Generate a repair report PDF', 'Download this diagnosis', 'Create a service report', 'Give me the repair instructions as a PDF', 'pdf bana do'):
        assert wants_pdf(t), t
    for t in ('read this pdf manual', 'the service report shows E4', 'Generate the repair steps', 'generate a diagnosis', 'fan not working'):
        assert not wants_pdf(t), t


def test_asking_for_a_pdf_answers_without_gemini(client, tech, session_id):
    r = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'Generate a repair report PDF'}, headers=tech['h']).json()
    assert r['ai_status'] == 'ok' and r['assistant_message']['meta']['action'] == 'pdf_report'
    assert r['assistant_message']['meta']['ai_generated'] is False
    msgs = client.get(f'/api/v1/sessions/{session_id}/messages', headers=tech['h']).json()['items']
    assert [m['role'] for m in msgs] == ['user', 'assistant']  # persisted, so it reopens with the chat


def test_pdf_contains_real_session_data_and_hides_locked_steps(client, tech, session_id, fake):
    client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    steps = client.post(f'/api/v1/sessions/{session_id}/steps/generate', headers=tech['h']).json()
    assert any(s['locked'] for s in steps)
    r = client.get(f'/api/v1/sessions/{session_id}/report.pdf', headers=tech['h'])
    assert r.status_code == 200 and r.headers['content-type'] == 'application/pdf' and r.content.startswith(b'%PDF')
    assert 'attachment' in r.headers['content-disposition']
    text = _pdf_text(r.content)
    ref = client.get(f'/api/v1/sessions/{session_id}', headers=tech['h']).json()['reference']
    for expected in (ref, 'Ceiling fan', 'ceiling fan is slow and hums', 'Reported problem', 'Safety verification status', 'Not recorded', 'Withheld', 'Page 1 of'):
        assert expected in text, expected
    assert 'Remove canopy' not in text  # power-sensitive instruction never leaks before the safety statements
    client.post(f'/api/v1/sessions/{session_id}/safety/confirm', json={'power_off_confirmed': True, 'tester_checked': True}, headers=tech['h'])
    text = _pdf_text(client.get(f'/api/v1/sessions/{session_id}/report.pdf', headers=tech['h']).content)
    assert 'Remove canopy' in text and 'Stated by technician' in text


def test_pdf_access_is_scoped(client, tech, session_id):
    assert client.get(f'/api/v1/sessions/{session_id}/report.pdf', headers=register(client)['h']).status_code == 404
    m = register(client, org='Acme Service'); make_role(m['user']['id'], 'manager')
    assert client.get(f'/api/v1/sessions/{session_id}/report.pdf', headers=m['h']).status_code == 200
