"""Retrieval ranking: channel fusion, Hinglish search terms, stale-embedding refresh and record/session index independence."""
import asyncio
from sqlalchemy import func, select
from app.db.models import RepairEmbedding
from app.db.session import SessionLocal
from app.services import knowledge_base as kb
from tests.test_dataset_pipeline import _ingest, _retrieve, rec


def _embed_env(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv('GEMINI_EMBED_MODEL', 'fake-embed'); monkeypatch.setenv('GEMINI_API_KEY', 'x' * 30); get_settings.cache_clear()


def test_fusion_adds_channels_and_keeps_codes_on_top():
    rows = {'a': {'code': 0.0, 'kw': 0.2, 'emb': 0.9}, 'b': {'code': 0.0, 'kw': 0.2, 'emb': 0.0}, 'c': {'code': 0.0, 'kw': 0.0, 'emb': 0.95},
            'd': {'code': kb.CODE_SCORE, 'kw': 0.0, 'emb': 0.0}}

    class Row:
        def __init__(self, rid): self.record_id, self.appliance_category, self.verification_status, self.appliance_brand, self.data = rid, 'ceiling_fan', 'unverified', None, {}
    hits = {h.record_id: h for h in kb._fuse({k: {'row': Row(k), **v} for k, v in rows.items()}, 'ceiling_fan', None)}
    assert hits['d'].score > hits['a'].score > max(hits['b'].score, hits['c'].score)  # both channels beat either alone
    assert hits['d'].match == 'error_code' and hits['a'].match == 'keyword' and hits['c'].match == 'embedding'


def test_hinglish_terms_reach_english_records(client):
    _ingest(rec(record_id='t:fan', appliance_category='ceiling_fan', reported_symptoms=['fan runs slow'], possible_faults=['weak capacitor']))
    assert 'fan' in kb._tsquery('pankha dheema chal raha')
    r = _retrieve('pankha dheema chal raha hai', category='ceiling_fan')
    assert 't:fan' in [h.record_id for h in r['hits']]


def test_changed_record_text_is_re_embedded_in_place(client, fake, monkeypatch):
    _embed_env(monkeypatch)
    _ingest(rec(record_id='t:e1', reported_symptoms=['drum noise']))
    with SessionLocal() as db:
        first = asyncio.run(kb.index_records(db)); db.commit()
        assert first >= 1 and asyncio.run(kb.index_records(db)) == 0  # nothing changed: no API calls
    _ingest(rec(record_id='t:e1', reported_symptoms=['drum noise and slow spin']))
    with SessionLocal() as db:
        before = db.scalar(select(func.count()).select_from(RepairEmbedding))
        assert asyncio.run(kb.index_records(db, commit_each_batch=True)) == 1
        db.commit()
        assert db.scalar(select(func.count()).select_from(RepairEmbedding)) == before  # updated, not duplicated
        row = db.execute(select(RepairEmbedding.content).where(RepairEmbedding.content.like('%slow spin%'))).first()
        assert row is not None


def test_record_embeddings_used_without_session_embeddings(client, tech, fake, monkeypatch):
    _embed_env(monkeypatch)
    with SessionLocal() as db:
        asyncio.run(kb.index_records(db)); db.commit()
    calls = []
    real = fake.embed
    async def counting(texts, task='RETRIEVAL_DOCUMENT'):
        calls.append(task); return await real(texts, task)
    monkeypatch.setattr(fake, 'embed', counting)
    r = client.get('/api/v1/similar-repairs?q=ceiling+fan+slow+hum&appliance_type=ceiling_fan', headers=tech['h']).json()
    assert r['mode'] == 'keyword' and r['knowledge_mode'] == 'hybrid'  # no past sessions indexed, records still hybrid
    assert calls == ['RETRIEVAL_QUERY']  # one query embedding, for the records only


def test_devanagari_hindi_reaches_english_records(client):
    _ingest(rec(record_id='t:ac', appliance_category='split_ac', reported_symptoms=['not cooling', 'weak cooling'], possible_faults=['dirty filter']))
    from app.datasets.normalize import detect_appliance
    assert detect_appliance('एसी ठंडा नहीं कर रहा है') == 'split_ac' and detect_appliance('फ्रिज ठंडा नहीं कर रहा') == 'refrigerator'
    assert 'cool' in kb._tsquery('एसी ठंडा नहीं कर रहा है')
    r = _retrieve('एसी ठंडा नहीं कर रहा है')
    assert 't:ac' in [h.record_id for h in r['hits']]


def test_symptom_record_beats_long_code_records_that_mention_the_word(client):
    """Field weighting: a record whose reported symptom IS the problem outranks error-code records whose procedure text
    happens to contain the same words many times."""
    long_proc = ['Check the drain hose', 'Clean the drain pump filter', 'Make sure the drain hose is not blocked', 'Drain the water first']
    for i in range(4):
        _ingest(rec(record_id=f't:code{i}', appliance_category='washing_machine', error_code=f'Z{i}', reported_symptoms=[f'Error code Z{i} shown on the display'],
                    diagnostic_procedure=long_proc))
    _ingest(rec(record_id='t:nodrain', appliance_category='washing_machine', reported_symptoms=['not draining', 'water remains'],
                possible_faults=['Blocked drain filter']))
    ids = [h.record_id for h in _retrieve('washing machine not draining, water stays in the drum', category='washing_machine')['hits']]
    assert 't:nodrain' in ids and all(ids.index('t:nodrain') < ids.index(f't:code{i}') for i in range(4) if f't:code{i}' in ids)


def test_rare_query_words_count_more_than_common_ones(client):
    """'Kent RO keeps beeping': every Kent record says 'RO purifier'; only one is about beeping, and it must rank first."""
    for i, sym in enumerate(['water leaking from RO purifier', 'low water pressure from RO purifier', 'no water from RO purifier']):
        _ingest(rec(record_id=f't:ro{i}', appliance_category='water_purifier', appliance_brand='Kent', reported_symptoms=[sym]))
    _ingest(rec(record_id='t:beep', appliance_category='water_purifier', appliance_brand='Kent', reported_symptoms=['purifier beeping continuously']))
    r = _retrieve('Kent RO keeps beeping', category='water_purifier')
    assert r['hits'][0].record_id == 't:beep'


def test_everyday_synonyms_reach_record_words(client):
    _ingest(rec(record_id='t:tt', appliance_category='microwave_oven', reported_symptoms=['turntable noisy or sticking']))
    assert 'turntable' in kb._tsquery('microwave plate not rotating')
    assert 't:tt' in [h.record_id for h in _retrieve('microwave plate not rotating properly', category='microwave_oven')['hits']]


def test_without_a_code_a_symptom_record_wins_a_tie_with_a_code_record(client):
    _ingest(rec(record_id='t:sym', appliance_category='split_ac', reported_symptoms=['AC not cooling']))
    _ingest(rec(record_id='t:ch', appliance_category='split_ac', error_code='CH99', reported_symptoms=['CH99 shown', 'AC not cooling']))
    ids = [h.record_id for h in _retrieve('AC not cooling', category='split_ac')['hits']]
    assert ids.index('t:sym') < ids.index('t:ch')
    ids = [h.record_id for h in _retrieve('AC not cooling, CH99 on the display', category='split_ac')['hits']]
    assert ids[0] == 't:ch'  # the code, when given, still decides


def test_similar_repair_titles_say_what_the_record_is_about():
    from app.services.retrieval import record_title
    assert record_title({'appliance_category': 'split_ac', 'appliance_brand': 'LG', 'error_code': 'CH38', 'reported_symptoms': ['CH38 shown']}) == 'LG split ac: code CH38'
    assert record_title({'appliance_category': 'ceiling_fan', 'reported_symptoms': ['fan wobbling or shaking']}) == 'ceiling fan: fan wobbling or shaking'
    assert record_title({'appliance_category': 'ceiling_fan', 'possible_faults': ['Weak capacitor']}) == 'ceiling fan: Weak capacitor'
    assert record_title({'appliance_category': 'ceiling_fan'}) == 'ceiling fan'


def test_hinglish_and_hindi_shaking_reach_wobble_records(client):
    """'pankha hil raha hai': the records say wobbling or shaking, never 'vibration'."""
    _ingest(rec(record_id='t:wob', appliance_category='ceiling_fan', reported_symptoms=['fan wobbling or shaking']),
            rec(record_id='t:dead', appliance_category='ceiling_fan', reported_symptoms=['fan completely dead']))
    for q in ('pankha hil raha hai bahut zyada', 'पंखा बहुत हिल रहा है'):
        assert _retrieve(q, category='ceiling_fan')['hits'][0].record_id == 't:wob', q
