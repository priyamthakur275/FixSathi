"""Dataset pipeline, knowledge base and RAG grounding. Fixtures below are written for the tests; they are not real records."""
import asyncio, csv, json, os
from datetime import date
from pathlib import Path
import pytest
from app.datasets import normalize as N
from app.datasets.importers import appliancedb, curated, openrepair
from app.datasets.pipeline import content_key, validate
from app.datasets.schema import RepairRecord
from app.db.session import SessionLocal
from app.services import knowledge_base as kb
from tests.fakes import DIAG

ROOT = Path(__file__).resolve().parents[2]


def rec(**kw):
    base = dict(record_id='t:1', appliance_category='washing_machine', reported_symptoms=['not draining'], source_name='Test fixture',
                source_url='https://example.org/x', source_license='CC0', source_record_id='1', verification_status='unverified', last_updated=date.today())
    base.update(kw); return base


# ---------- schema and validation ----------

def test_schema_accepts_valid_and_keeps_unknowns_null():
    r = RepairRecord.model_validate(rec())
    assert r.appliance_brand is None and r.model_year is None and r.estimated_repair_duration_minutes is None


@pytest.mark.parametrize('bad,why', [
    (dict(appliance_category='toaster'), 'unknown appliance_category'),
    (dict(reported_symptoms=[], possible_faults=[], error_code=None, repair_steps=[]), 'no symptom'),
    (dict(source_license=''), 'source_license'),
    (dict(source_url=None), 'source_url'),
    (dict(verification_status='synthetic_demo'), 'synthetic'),
    (dict(source_name='SYNTHETIC thing'), 'synthetic'),
    (dict(model_year=1800), 'model_year'),
    (dict(severity='catastrophic'), 'severity'),
])
def test_invalid_records_rejected(bad, why):
    ok, rej = validate([rec(**bad)])
    assert not ok and rej[0]['reason'] == 'invalid' and any(why.split()[0] in e for e in rej[0]['errors']) or why in str(rej)


def test_duplicate_detection_respects_model_brand_market():
    a = rec(record_id='t:a', appliance_brand='Samsung', market='US', error_code='4C', possible_faults=['No water'])
    same = rec(record_id='t:b', appliance_brand='Samsung', market='US', error_code='4C', possible_faults=['No water'])
    other_market = rec(record_id='t:c', appliance_brand='Samsung', market='UK', error_code='4C', possible_faults=['No water'])
    other_model = rec(record_id='t:d', appliance_brand='Samsung', market='US', appliance_model='WF45', error_code='4C', possible_faults=['No water'])
    dup_id = rec(record_id='t:a', appliance_brand='LG')
    ok, rej = validate([a, same, other_market, other_model, dup_id])
    assert [r.record_id for r in ok] == ['t:a', 't:c', 't:d']
    assert {x['reason'] for x in rej} == {'duplicate_content', 'duplicate_record_id'}
    assert content_key(RepairRecord.model_validate(a)) != content_key(RepairRecord.model_validate(other_market))


def test_normalisation():
    assert N.brand(' lg ') == 'LG' and N.brand('Unknown') is None and N.brand('bluestar') == 'Blue Star'
    assert N.error_code('e-21') == 'E21' and N.error_code(' 4c ') == '4C'
    assert N.category('Washer') == 'washing_machine' and N.category('Aircon/dehumidifier') == 'aircon_dehumidifier'
    assert N.component('NTC thermistor') == 'thermistor'
    assert 'not draining' in N.symptoms("Water stays in the drum, won't drain")
    assert N.extract_codes('LG fridge showing code ER IF') == ['IF', 'ERIF']
    assert N.extract_codes('machine 10kg not spinning at 24 degrees') == []
    assert N.extract_codes('Samsung washer showing 4C error') == ['4C']


# ---------- importers (real ApplianceDB sample if present, plus small fixtures) ----------

@pytest.mark.skipif(not (ROOT / 'data/raw/appliancedb/error_codes.csv').exists(), reason='ApplianceDB not downloaded')
def test_appliancedb_import_attribution_and_scope():
    cands, skipped = appliancedb.load(ROOT / 'data/raw/appliancedb')
    ok, rej = validate(cands)
    assert ok and not rej
    assert {r.appliance_category for r in ok} == {'washing_machine', 'refrigerator'}
    assert all(r.source_url and r.source_url.startswith('http') and 'ODbL' in r.source_license and r.source_record_id for r in ok)
    assert {r.verification_status for r in ok} <= {'verified_source', 'unverified'}
    assert all(s['reason'].startswith('out_of_scope') for s in skipped)
    # same code, different market -> separate records
    s4c = [r for r in ok if r.appliance_brand == 'Samsung' and r.error_code == '4C']
    assert len({r.market for r in s4c}) == len(s4c) >= 2


def test_openrepair_importer(tmp_path):
    f = tmp_path / 'ords.csv'
    rows = [
        {'id': '1', 'data_provider': 'Test Cafe', 'country': 'GBR', 'product_category': 'Large home electrical', 'partner_product_category': 'Washing machine',
         'brand': 'hotpoint', 'year_of_manufacture': '2015', 'problem': 'Will not drain, water stays in drum', 'repair_status': 'Fixed', 'event_date': '2024-01-01'},
        {'id': '2', 'data_provider': 'Test Cafe', 'country': 'GBR', 'product_category': 'Large home electrical', 'partner_product_category': 'Cooker',
         'brand': 'x', 'year_of_manufacture': '', 'problem': 'Hob not heating', 'repair_status': 'End of life', 'event_date': '2024-01-01'},
        {'id': '3', 'data_provider': 'Test Cafe', 'country': 'GBR', 'product_category': 'Aircon/dehumidifier', 'partner_product_category': '',
         'brand': 'unknown', 'year_of_manufacture': 'abc', 'problem': 'Not cooling at all', 'repair_status': '2', 'event_date': '2024-01-01'},
        {'id': '4', 'data_provider': 'Test Cafe', 'country': 'GBR', 'product_category': 'Mobile', 'partner_product_category': '',
         'brand': 'x', 'year_of_manufacture': '', 'problem': 'Cracked screen', 'repair_status': 'Fixed', 'event_date': '2024-01-01'},
    ]
    with f.open('w', newline='') as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    cands, skipped = openrepair.load(f)
    ok, rej = validate(cands)
    assert [(r.appliance_category, r.appliance_brand, r.repair_outcome, r.model_year) for r in ok] == [
        ('washing_machine', 'Hotpoint', 'fixed', 2015), ('aircon_dehumidifier', None, 'repairable', None)]
    assert all(r.verification_status == 'unverified' and 'CC BY-SA' in r.source_license for r in ok)
    assert len(skipped) == 2


def test_curated_migration_keeps_every_entry():
    p = Path(__file__).resolve().parents[1] / 'app/knowledge/faults.json'
    ok, rej = validate(curated.load(p)[0])
    assert len(ok) == len(json.loads(p.read_text())['entries']) and not rej
    assert all(r.verification_status == 'unverified' and r.provenance['authored_by'] == 'FixSaathi team' for r in ok)


def test_synthetic_file_is_labelled_and_separate():
    syn = ROOT / 'data/synthetic/demo_records.jsonl'
    ok, rej = validate([json.loads(l) for l in syn.read_text().splitlines() if l.strip()])
    assert ok and not rej and all(r.verification_status == 'synthetic_demo' and 'SYNTHETIC' in r.source_name for r in ok)
    proc = ROOT / 'data/processed/repair_records.jsonl'
    if proc.exists():
        assert 'synthetic_demo' not in proc.read_text()


# ---------- knowledge base retrieval ----------

def _ingest(*records):
    with SessionLocal() as db:
        kb.ingest(db, [RepairRecord.model_validate(r) for r in records]); db.commit()


def _retrieve(q, **kw):
    with SessionLocal() as db:
        return asyncio.run(kb.retrieve(db, q, **kw))


def test_retrieval_by_code_brand_and_category(client):
    _ingest(rec(record_id='t:s4c', appliance_brand='Samsung', error_code='4C', possible_faults=['Water supply problem during fill']),
            rec(record_id='t:lg4c', appliance_brand='LG', error_code='4C', possible_faults=['Something else']),
            rec(record_id='t:fr', appliance_category='refrigerator', error_code='4C', possible_faults=['Fridge thing']))
    r = _retrieve('Samsung washer showing 4C', category='washing_machine')
    ids = [h.record_id for h in r['hits']]
    assert ids[0] == 't:s4c' and 't:fr' not in ids and 't:lg4c' not in ids
    assert r['coverage'] == 'grounded' and r['hits'][0].match == 'error_code'
    assert r['hits'][0].citation()['source_url'] == 'https://example.org/x'


def test_unknown_code_is_reported_not_guessed(client):
    r = _retrieve('IFB washer showing code E9', category='washing_machine')
    assert r['error_codes_unknown'] == ['E9'] and r['coverage'] == 'none'
    assert 'do not state what they mean' in kb.context_block(r)


def test_keyword_fallback_and_related_category(client):
    _ingest(rec(record_id='t:dh', appliance_category='aircon_dehumidifier', reported_symptoms=['not cooling'], observed_conditions=['Unit runs but air not cold']))
    r = _retrieve('split AC not cooling, air not cold', category='split_ac')
    assert r['mode'] == 'keyword' and r['fallback_reason']
    rel = [h for h in r['hits'] if h.record_id == 't:dh'][0]
    assert rel.related and 'RELATED_CATEGORY' in rel.flags
    assert r['hits'][0].record_id.startswith('fixsaathi:')  # primary-category curated entry outranks related category


def test_synthetic_excluded_by_default(client):
    _ingest(rec(record_id='synthetic:x', source_name='SYNTHETIC DEMO DATA', verification_status='synthetic_demo', source_url=None,
                reported_symptoms=['zzqx unique symptom'], provenance={'authored_by': 'test'}))
    assert not _retrieve('zzqx unique symptom', category='washing_machine')['hits']
    h = _retrieve('zzqx unique symptom', category='washing_machine', include_synthetic=True)['hits']
    assert h and 'SYNTHETIC_DEMO' in h[0].flags and 'SYNTHETIC DEMO, NOT REAL' in kb.context_block({'coverage': 'partial', 'error_codes_unknown': [], 'brand': None, 'hits': h})


def test_embeddings_hybrid_mode(client, fake, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv('GEMINI_EMBED_MODEL', 'fake-embed'); monkeypatch.setenv('GEMINI_API_KEY', 'x' * 30); get_settings.cache_clear()
    with SessionLocal() as db:
        n = asyncio.run(kb.index_records(db)); db.commit()
    assert n >= 12
    r = _retrieve('ceiling fan slow and hums', category='ceiling_fan')
    assert r['mode'] == 'hybrid' and r['hits'][0].record_id == 'fixsaathi:fan_slow_hum'


def test_knowledge_api(client, tech):
    r = client.get('/api/v1/knowledge/search?q=fan+slow+hum&appliance_type=ceiling_fan', headers=tech['h']).json()
    assert r['results'][0]['record_id'] == 'fixsaathi:fan_slow_hum' and r['results'][0]['license']
    s = client.get('/api/v1/knowledge/stats', headers=tech['h']).json()
    assert s['total'] >= 12 and 'synthetic_demo' in s['verification_meaning']
    assert client.get('/api/v1/knowledge/search?q=fan').status_code == 401


# ---------- RAG grounding through the API ----------

def test_diagnosis_citations_validated(client, tech, session_id, fake):
    d = json.loads(json.dumps(DIAG))
    d['possible_faults'][1]['status'] = 'supported_by_records'; d['possible_faults'][1]['record_ids'] = ['fixsaathi:fan_slow_hum', 'appliancedb:999999-invented']
    d['possible_faults'][0]['status'] = 'supported_by_records'; d['possible_faults'][0]['record_ids'] = ['made:up']
    fake.json['diagnosis'] = d
    out = client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h']).json()
    cap = next(f for f in out['faults'] if f['fault'] == 'Weak capacitor'); bear = next(f for f in out['faults'] if f['fault'] == 'Worn bearings')
    assert cap['record_ids'] == ['fixsaathi:fan_slow_hum'] and cap['status'] == 'supported_by_records'
    assert bear['record_ids'] == [] and bear['status'] == 'unverified_hypothesis'  # invented citation removed, claim downgraded
    assert out['knowledge_coverage'] == 'grounded' and [s['record_id'] for s in out['sources']] == ['fixsaathi:fan_slow_hum']
    prompt = str(fake.calls[-1][1])
    assert '[fixsaathi:fan_slow_hum]' in prompt and 'Retrieval coverage' in prompt


def test_missing_knowledge_handled(client, tech, fake):
    sid = client.post('/api/v1/sessions', json={'issue_description': 'IFB washer showing code E9', 'appliance_type': 'washing_machine'}, headers=tech['h']).json()['id']
    d = json.loads(json.dumps(DIAG)); d['follow_up_questions'] = []; fake.json['diagnosis'] = d
    out = client.post(f'/api/v1/sessions/{sid}/diagnose', headers=tech['h']).json()
    assert out['knowledge_coverage'] == 'none'
    assert all(f['status'] == 'unverified_hypothesis' for f in out['faults'])
    assert any('E9' in m for m in out['missing_information']) and out['follow_up_questions']


def test_chat_strips_invented_citations(client, tech, session_id, fake):
    fake.text = 'A weak capacitor is the likely cause [fixsaathi:fan_slow_hum], see [lg:fake-123] too.'
    r = client.post(f'/api/v1/sessions/{session_id}/messages', json={'text': 'fan slow and humming'}, headers=tech['h']).json()
    m = r['assistant_message']
    assert '[fixsaathi:fan_slow_hum]' in m['message'] and 'lg:fake-123' not in m['message']
    assert [s['record_id'] for s in m['meta']['sources']] == ['fixsaathi:fan_slow_hum'] and m['meta']['removed_invalid_citations'] == 1


def test_unverified_source_steps_still_gated(client, tech, session_id, fake):
    """Steps drawn from unverified records never become trusted: power-sensitive wording is re-checked by the server."""
    client.post(f'/api/v1/sessions/{session_id}/diagnose', headers=tech['h'])
    fake.json['guidance'] = {'steps': [{'title': 'Swap part', 'instruction': 'Unscrew the canopy and replace the capacitor', 'kind': 'safe_action', 'requires_power_off': False}],
                             'record_ids': ['fixsaathi:fan_slow_hum', 'invented:1']}
    st = client.post(f'/api/v1/sessions/{session_id}/steps/generate', headers=tech['h']).json()
    assert st[0]['requires_power_off'] is True and st[0]['locked'] is True
    assert client.post(f"/api/v1/sessions/{session_id}/steps/{st[0]['id']}/complete", headers=tech['h']).status_code == 409
