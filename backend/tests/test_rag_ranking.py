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
