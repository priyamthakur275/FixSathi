"""Manufacturer-documented records, appliance-aware retrieval, code aliases and the microwave server rule.
Retrieval tests load the real processed dataset (data/processed/repair_records.jsonl), so they check the shipped records."""
import asyncio, json
from collections import Counter
from pathlib import Path
import pytest
from app.datasets import normalize as N
from app.datasets.importers import manufacturer_docs
from app.datasets.pipeline import validate
from app.db.session import SessionLocal
from app.services import knowledge_base as kb
from app.services.sessions import guess_appliance

ROOT = Path(__file__).resolve().parents[2]
MFR = ROOT / 'data' / 'raw' / 'manufacturer_docs'
PROCESSED = ROOT / 'data' / 'processed' / 'repair_records.jsonl'


def _processed():
    return [json.loads(l) for l in PROCESSED.read_text().splitlines() if l.strip()]


@pytest.fixture
def loaded(client):
    recs, rej = validate(_processed())
    assert not rej
    with SessionLocal() as db:
        kb.ingest(db, recs); db.commit()
    return recs


def _retrieve(q, **kw):
    with SessionLocal() as db:
        return asyncio.run(kb.retrieve(db, q, **kw))


# ---------- dataset quality ----------

def test_every_manufacturer_record_is_valid_sourced_and_unique():
    cands, skipped = manufacturer_docs.load(MFR)
    ok, rej = validate(cands)
    assert not skipped and not rej and len(ok) == len(cands)
    assert all(r.source_url and r.source_url.startswith('https://') for r in ok)
    assert all(r.provenance['evidence_level'] and r.provenance['source_type'] and r.provenance['accessed'] for r in ok)
    assert len({r.record_id for r in ok}) == len(ok)
    assert all(r.possible_faults or r.diagnostic_procedure or r.recommended_repair for r in ok)


def test_secondary_hosted_manuals_are_not_marked_verified():
    cands, _ = manufacturer_docs.load(MFR)
    for c in cands:
        hosted_elsewhere = c['provenance']['evidence_level'] == 'manufacturer_manual_secondary_host'
        assert (c['verification_status'] == 'unverified') == hosted_elsewhere, c['record_id']


def test_processed_dataset_keeps_original_records_and_covers_six_appliances():
    recs = _processed()
    ids = [r['record_id'] for r in recs]
    assert len(ids) == len(set(ids))
    cats = Counter(r['appliance_category'] for r in recs)
    for c in ('washing_machine', 'split_ac', 'refrigerator', 'ceiling_fan', 'microwave_oven', 'water_purifier'):
        assert cats[c] >= 15, (c, cats[c])
    assert sum(1 for i in ids if i.startswith('appliancedb:')) == 280 and sum(1 for i in ids if i.startswith('fixsaathi:')) == 12


def test_microwave_records_carry_the_cabinet_warning():
    cands, _ = manufacturer_docs.load(MFR)
    mw = [c for c in cands if c['appliance_category'] == 'microwave_oven']
    assert mw and all(any('high-voltage capacitor' in p for p in c['fixsaathi_safety_policy']) for c in mw)


# ---------- appliance detection ----------

@pytest.mark.parametrize('text,cat', [
    ('fridge not cooling', 'refrigerator'),  # used to be guessed as split_ac because of the word "cooling"
    ('Samsung refrigerator freezer ice', 'refrigerator'),
    ('AC indoor fan not running', 'split_ac'),
    ('split ac cooling nahi ho raha', 'split_ac'),
    ('ceiling fan hums but does not spin', 'ceiling_fan'),
    ('pankha slow chal raha hai', 'ceiling_fan'),
    ('microwave sparks inside', 'microwave_oven'),
    ('Kent RO no water coming', 'water_purifier'),
    ('water purifier leaking', 'water_purifier'),
    ('washing machine drum not spinning', 'washing_machine'),
    ('mcb trips again and again', 'mcb_electrical'),
    ('it is broken', 'unknown'),
])
def test_detect_appliance(text, cat):
    assert N.detect_appliance(text) == cat and guess_appliance(text) == cat


def test_lg_spaced_code_is_extracted():
    assert N.extract_codes('LG AC showing CH 38') == ['CH38']
    assert N.extract_codes('display par CH38 aa raha') == ['CH38']


# ---------- retrieval: one realistic query per appliance, category isolation ----------

@pytest.mark.parametrize('query,cat,expect', [
    ('My Samsung washing machine drum is not spinning and makes a humming sound', 'washing_machine', None),
    ('LG split AC showing CH38 and not cooling', 'split_ac', 'mfr:lg-ac-ch38'),
    ('Samsung direct cool fridge low cooling, ice build-up in freezer', 'refrigerator', 'mfr:samsung-fridge-directcool-ice'),
    ('ceiling fan smells like burning', 'ceiling_fan', 'mfr:orient-fan-burning-smell'),
    ('Samsung microwave runs but does not heat, timer counts down very fast', 'microwave_oven', 'mfr:samsung-mw-demo-mode'),
    ('Kent Sterling Plus purifier beeping continuously', 'water_purifier', 'mfr:kent-sterling-beeping'),
])
def test_retrieval_per_appliance_stays_in_category(loaded, query, cat, expect):
    for session_cat in (cat, None):  # with the session's appliance, and detected from the text when the session has none
        r = _retrieve(query, category=session_cat)
        assert r['hits'], query
        assert all(h.category == cat for h in r['hits']), [(h.record_id, h.category) for h in r['hits']]
        assert r['coverage'] == 'grounded'
        if expect:
            assert expect in [h.record_id for h in r['hits'][:3]], [h.record_id for h in r['hits']]
        for h in r['hits']:
            c = h.citation()
            assert c['source_name'] and c['license'] and c['record_id'] == h.record_id
    assert _retrieve(query, category=None)['category_detected'] == cat


def test_refrigerator_question_never_gets_washing_machine_records(loaded):
    r = _retrieve('fridge making loud noise and not cooling')
    assert r['category'] == 'refrigerator' and r['hits'] and all(h.category == 'refrigerator' for h in r['hits'])


def test_code_alias_matches_whole_tokens_only(loaded):
    r = _retrieve('LG AC showing F4', category='split_ac')
    ids = [h.record_id for h in r['hits']]
    assert 'mfr:lg-ac-ch38' in ids and r['error_codes_found'] == ['F4']
    r = _retrieve('LG AC code E1', category='split_ac')
    assert 'mfr:lg-ac-sensor-codes' in [h.record_id for h in r['hits']]
    r = _retrieve('LG AC code E10', category='split_ac')
    assert 'mfr:lg-ac-sensor-codes' not in [h.record_id for h in r['hits'] if h.match == 'error_code']
    assert r['error_codes_unknown'] == ['E10']


def test_other_brand_codes_do_not_answer(loaded):
    r = _retrieve('Voltas AC showing CH38', category='split_ac')
    assert 'mfr:lg-ac-ch38' not in [h.record_id for h in r['hits']] and r['error_codes_unknown'] == ['CH38']


# ---------- server-side rules ----------

def test_microwave_cabinet_steps_become_escalation(client, tech, fake):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'microwave not heating', 'appliance_type': 'microwave_oven'}, headers=tech['h']).json()['id']
    fake.json['diagnosis'] = {**fake.json['diagnosis'], 'appliance_type': 'microwave_oven'}
    fake.json['guidance'] = {'steps': [
        {'title': 'Check settings', 'instruction': 'Make sure demo mode is off', 'kind': 'observation', 'requires_power_off': False},
        {'title': 'Test the magnetron', 'instruction': 'Remove the outer cabinet and check the high-voltage diode', 'kind': 'diagnostic_check', 'requires_power_off': False}]}
    assert client.post(f'/api/v1/sessions/{sid}/diagnose', headers=tech['h']).status_code == 201
    r = client.post(f'/api/v1/sessions/{sid}/steps/generate', headers=tech['h']); assert r.status_code == 201, r.text
    steps = r.json() if isinstance(r.json(), list) else r.json()['steps']
    assert steps[0]['kind'] == 'observation'
    assert steps[1]['kind'] == 'escalation' and 'Do not open the microwave' in (steps[1].get('instruction') or steps[1].get('title'))
    assert 'diode' not in json.dumps(steps).lower()


def test_diagnosis_returns_tools_and_escalation_reason(client, tech, session_id, fake):
    fake.json['diagnosis'] = {**fake.json['diagnosis'], 'required_tools': ['Voltage tester', 'Multimeter'], 'requires_escalation': True,
                              'escalation_reason': 'Burnt wiring at the ceiling rose'}
    d = client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h']).json()
    assert d['required_tools'] == ['Voltage tester', 'Multimeter'] and d['escalation_reason'] == 'Burnt wiring at the ceiling rose'
    fake.json['diagnosis'] = {**fake.json['diagnosis'], 'requires_escalation': False}
    d = client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h']).json()
    assert d['escalation_reason'] is None


# ---------- stemming and citation clean-up ----------

def test_word_forms_match_with_english_stemming(loaded):
    r = _retrieve('there are burn marks on the ceiling around the fan', category='ceiling_fan')
    assert 'mfr:orient-fan-burning-smell' in [h.record_id for h in r['hits']]
    r = _retrieve('fan hums but blades do not spin', category='ceiling_fan')
    assert any(h.record_id in ('mfr:crompton-fan-no-start-power', 'fixsaathi:fan_slow_hum', 'mfr:orient-fan-hum') for h in r['hits'][:4])


def test_removed_citation_leaves_no_stray_space():
    from app.services.ai import _clean_citations
    text, used, invented = _clean_citations('It overheats [mfr:made-up]. Check the terminal [mfr:ok-1], then the capacitor.', {'mfr:ok-1'})
    assert text == 'It overheats. Check the terminal [mfr:ok-1], then the capacitor.' and used == ['mfr:ok-1'] and invented == ['mfr:made-up']


def test_no_embedding_call_without_an_index(client, fake, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv('GEMINI_EMBED_MODEL', 'fake-embed'); monkeypatch.setenv('GEMINI_API_KEY', 'x' * 30); monkeypatch.setenv('VECTOR_SEARCH_MODE', 'auto'); get_settings.cache_clear()
    calls = []
    real = fake.embed
    async def counting(texts, task='RETRIEVAL_DOCUMENT'):
        calls.append(task); return await real(texts, task)
    monkeypatch.setattr(fake, 'embed', counting)
    r = _retrieve('fan hums', category='ceiling_fan')
    assert calls == [] and r['mode'] == 'keyword' and 'index_knowledge' in r['fallback_reason']
