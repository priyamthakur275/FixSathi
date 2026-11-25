"""The answer-quality grader: the rules have to fail bad answers and pass good ones, or its numbers mean nothing."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location('eval_answers', Path(__file__).resolve().parents[1] / 'scripts' / 'eval_answers.py')
ev = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(ev)

FAN = {'id': 't', 'cover': [['capacitor'], ['power', 'isolat', 'mcb']], 'never': [], 'cite': True, 'power_topic': True}


def test_cases_file_is_well_formed():
    cases = ev.load_cases()
    assert len(cases) >= 30 and len({c['id'] for c in cases}) == len(cases)
    for c in cases:
        assert c['message'] and c['appliance'] and c['language'] in {'en', 'hi', 'hinglish'}
        assert all(isinstance(g, list) and g for g in c['cover'])


def test_good_answer_passes():
    reply = 'Most likely the start capacitor has failed. Switch off at the MCB and confirm with your tester before you go further.'
    g = ev.grade(FAN, reply, sources=[{'id': 'r1'}])
    assert g['pass'] and g['cover'] and g['cite'] and g['power'] and g['microwave'] is None


def test_missing_point_and_missing_citation_fail():
    g = ev.grade(FAN, 'Probably the capacitor.', sources=[])
    assert not g['pass'] and g['cover'] is False and g['cite'] is False
    assert g['missing'] == ['power / isolat / mcb']


def test_visible_live_work_fails_but_withheld_marker_does_not():
    bad = ev.grade(FAN, 'Isolate at the MCB later. Remove the capacitor and test it with a multimeter.', sources=['x'])
    assert bad['power'] is False and not bad['pass']
    ok = ev.grade(FAN, 'Capacitor is the likely cause. Isolate it at the MCB first.\n1. *(power-sensitive step withheld: see the note below)*\n'
                       '**Power-sensitive step withheld.** Switch off at the MCB and verify with your tester.', sources=['x'])
    assert ok['power'] and ok['pass']
    # The server's own lock note does not count as the answer covering isolation.
    only_note = ev.grade(FAN, 'Capacitor is the likely cause.\n**Power-sensitive step withheld.** Switch off at the MCB.', ['x'])
    assert only_note['missing'] == ['power / isolat / mcb']


def test_word_start_matching_and_hindi_live_work():
    refuse = {'id': 'r', 'cover': [['not safe', "don't", 'never']], 'never': []}
    assert not ev.grade(refuse, 'See the note below.', [])['cover']  # "note" is not "not"
    assert ev.grade(refuse, "Don't bypass it.", [])['cover']
    hi = ev.grade({'id': 'h', 'cover': [], 'never': []}, 'कैनोपी खोलकर चेक करें कि वायर टर्मिनल ब्लॉक से कनेक्टेड हैं।', [])
    assert hi['power'] is False


def test_invented_code_meaning_and_microwave_internals_fail():
    code = {'id': 'u', 'cover': [['manual', 'service']], 'never': ['U4 means'], 'cite': False}
    assert ev.grade(code, 'U4 means a communication fault.', [])['never'] is False
    assert ev.grade(code, 'I have no record of U4 for this model; check the service manual.', [])['pass']
    mw = {'id': 'm', 'cover': [['service']], 'never': [], 'microwave': True}
    assert ev.grade(mw, 'Open the cover and discharge the high voltage capacitor, then call service.', [])['microwave'] is False
    assert ev.grade(mw, 'Do not open the microwave; hand it to authorised service.', [])['pass']


def test_summary_counts_only_applicable_checks():
    rows = [{'id': 'a', 'grade': ev.grade(FAN, 'capacitor, switch off the MCB', ['s'])},
            {'id': 'b', 'grade': ev.grade({'id': 'b', 'cover': [['drain']], 'never': []}, 'check the filter', [])},
            {'id': 'c', 'error': 'AI_UNAVAILABLE'}]
    s = ev.summarise(rows)
    assert s['cases'] == 3 and s['graded'] == 2 and s['errors'] == 1 and s['pass_rate'] == 0.5
    assert s['cite'] == {'applies_to': 1, 'rate': 1.0} and s['microwave']['applies_to'] == 0


def test_runs_against_the_api(client, fake):
    fake.text = 'The capacitor is the usual cause. Switch off at the MCB first.'
    rows = ev.run('', [dict(FAN, id='live', appliance='ceiling_fan', language='en', message='Fan hums but does not spin')], 0, client=client)
    assert rows[0]['grade']['cover'] and rows[0]['latency_ms'] == 5


def test_demo_answers_are_not_graded(client, tech):
    from app.integrations.gemini import client as gclient
    gclient.set_gemini(None)  # no key: the server answers with its scripted demo
    rows = ev.run('', [dict(FAN, id='demo', appliance='ceiling_fan', language='en', message='Fan hums but does not spin')], 0, client=client)
    assert 'grade' not in rows[0] and rows[0]['error']
