"""Repair knowledge base over `repair_records`.

retrieve(): structured filters (category, brand, model, error code) → PostgreSQL full-text keyword ranking →
optional Gemini-embedding re-ranking. Synthetic demo records are excluded unless include_synthetic=True.
Every hit carries its record_id, source, licence and verification status so answers can cite it.
"""
import logging, re
from dataclasses import dataclass, field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ..config import get_settings
from ..core.exceptions import AppError
from ..core.logging import log
from ..datasets import normalize as N
from ..datasets.schema import RELATED, VERIFICATION_MEANING, RepairRecord
from ..db.models import RepairEmbedding, RepairRecordRow
from ..integrations.gemini.client import get_gemini
from .knowledge import cosine

logger = logging.getLogger('knowledge_base')
WORD = re.compile(r'[a-z0-9]{2,}')
STOP = {'the', 'and', 'is', 'it', 'my', 'not', 'of', 'to', 'in', 'on', 'with', 'hai', 'nahi', 'ka', 'ki', 'raha', 'rahi', 'but', 'its', 'this', 'that', 'was', 'are', 'code', 'error', 'err', 'showing', 'shows',
        'display', 'machine', 'washing', 'washer', 'fridge', 'refrigerator', 'ac', 'split', 'appliance', 'unit', 'please', 'help', 'kya', 'karu', 'problem', 'issue', 'microwave', 'purifier', 'oven'}
VERIFICATION_WEIGHT = {'technician_reviewed': 1.25, 'verified_source': 1.15, 'unverified': 1.0, 'synthetic_demo': 0.5}
# Score fusion. An exact error-code match dominates; keyword rank is scaled to 0-1 by the best keyword hit of this query;
# embedding similarity above EMB_MIN_SIM is scaled to 0-1. A record matched by several channels adds them up.
CODE_SCORE, ALIAS_SCORE, KW_WEIGHT, EMB_WEIGHT, EMB_MIN_SIM = 10.0, 9.0, 3.0, 3.0, 0.5
# Common Hinglish words technicians type, mapped to the English words the records use. Search terms only; nothing is added to records.
HINGLISH = {'pankha': 'fan', 'pankhe': 'fan', 'thanda': 'cool', 'thandi': 'cool', 'garam': 'hot', 'awaaz': 'noise',
            'awaz': 'noise', 'aawaz': 'noise', 'paani': 'water', 'pani': 'water', 'ghoom': 'spin', 'ghum': 'spin', 'ghumta': 'spin',
            'dhuan': 'smoke', 'dhuaan': 'smoke', 'badbu': 'smell', 'tapak': 'leak', 'tapakna': 'leak', 'bijli': 'power', 'jhatka': 'shock',
            'hil': 'vibration', 'hilta': 'vibration', 'barf': 'ice', 'dheema': 'slow', 'dheere': 'slow', 'dhire': 'slow',
            'nikal': 'drain', 'nikalta': 'drain', 'beep': 'beeping', 'chingari': 'spark', 'jal': 'burning', 'jala': 'burning'}
# The same for Hindi typed in Devanagari (voice input in Hindi arrives this way). Without it a Hindi message finds no records
# by keyword at all; the embedding channel, when configured, also understands Hindi.
DEVANAGARI = {'पंखा': 'fan', 'पंखे': 'fan', 'ठंडा': 'cool', 'ठंडी': 'cool', 'ठंडक': 'cooling', 'कूलिंग': 'cooling', 'गरम': 'hot',
              'गर्म': 'hot', 'आवाज़': 'noise', 'आवाज': 'noise', 'शोर': 'noise', 'पानी': 'water', 'घूम': 'spin', 'घूमता': 'spin',
              'धुआं': 'smoke', 'धुआँ': 'smoke', 'बदबू': 'smell', 'टपक': 'leak', 'लीक': 'leak', 'बिजली': 'power', 'झटका': 'shock',
              'बर्फ': 'ice', 'धीमा': 'slow', 'धीरे': 'slow', 'हिल': 'vibration', 'निकल': 'drain', 'बीप': 'beeping', 'चिंगारी': 'spark',
              'बंद': 'stops', 'चालू': 'start', 'स्वाद': 'taste', 'दरवाजा': 'door', 'दरवाज़ा': 'door', 'लाइट': 'light',
              'एसी': 'ac', 'फ्रिज': 'fridge', 'फ्रीज': 'fridge', 'मशीन': 'machine', 'माइक्रोवेव': 'microwave', 'प्यूरीफायर': 'purifier'}
DEV_WORD = re.compile(r'[\u0900-\u097F]+')


def _fuse(chan: dict[str, dict], category: str | None, brand: str | None) -> list['Hit']:
    max_kw = max((c['kw'] for c in chan.values()), default=0.0) or 1.0
    out = []
    for rid, c in chan.items():
        row = c['row']
        score = c['code'] + KW_WEIGHT * c['kw'] / max_kw + EMB_WEIGHT * max(0.0, (c['emb'] - EMB_MIN_SIM) / (1 - EMB_MIN_SIM))
        match = 'error_code' if c['code'] else 'keyword' if c['kw'] else 'embedding'
        rel = bool(category and row.appliance_category != category)
        score *= VERIFICATION_WEIGHT.get(row.verification_status, 1.0) * (0.6 if rel else 1.0)
        if brand and row.appliance_brand and row.appliance_brand.lower() == brand.lower():
            score *= 1.3
        out.append(Hit(rid, row.appliance_category, rel, score, match, row.data))
    return out


class _NoIndex(Exception):
    pass


@dataclass
class Hit:
    record_id: str
    category: str
    related: bool
    score: float
    match: str  # error_code | keyword | embedding | filter
    record: dict
    flags: list[str] = field(default_factory=list)

    def citation(self) -> dict:
        r = self.record
        return {'record_id': self.record_id, 'source_name': r['source_name'], 'source_url': r.get('source_url'), 'license': r['source_license'],
                'verification_status': r['verification_status'], 'match': self.match, 'related_category': self.related}


def ingest(db: Session, records: list[RepairRecord]) -> dict:
    """Idempotent upsert by record_id. Returns counts."""
    existing = {r.record_id: r for r in db.scalars(select(RepairRecordRow).where(RepairRecordRow.record_id.in_([x.record_id for x in records])))}
    added = updated = 0
    for r in records:
        d = r.model_dump(mode='json')
        cols = dict(appliance_category=r.appliance_category, appliance_brand=r.appliance_brand, appliance_model=r.appliance_model, market=r.market,
                    error_code=r.error_code, severity=r.severity, requires_power_off=r.requires_power_off, verification_status=r.verification_status,
                    source_name=r.source_name[:200], source_license=r.source_license[:200], source_url=r.source_url, source_record_id=r.source_record_id[:120],
                    search_text=r.search_text(), data=d, last_updated=r.last_updated)
        row = existing.get(r.record_id)
        if row:
            if row.data != d or row.search_text != cols['search_text']:
                for k, v in cols.items(): setattr(row, k, v)
                updated += 1
        else:
            db.add(RepairRecordRow(record_id=r.record_id, **cols)); added += 1
    db.flush()
    return {'added': added, 'updated': updated, 'unchanged': len(records) - added - updated}


def _tsquery(q: str) -> str | None:
    toks = []
    for t in WORD.findall(q.lower()):
        if t in HINGLISH:
            toks.append(HINGLISH[t])
        if t not in STOP:
            toks.append(t)
    for t in DEV_WORD.findall(q):
        en = DEVANAGARI.get(t) or next((v for k, v in DEVANAGARI.items() if t.startswith(k)), None)
        if en and en not in STOP:
            toks.append(en)
    return ' | '.join(dict.fromkeys(toks[:24])) or None


def known_brands(db: Session) -> list[str]:
    return [b for (b,) in db.execute(select(RepairRecordRow.appliance_brand).where(RepairRecordRow.appliance_brand.is_not(None)).distinct())]


def detect_brand(db: Session, text_: str) -> str | None:
    t = f' {text_.lower()} '
    for b in sorted(known_brands(db) + list(set(N.BRANDS.values())), key=len, reverse=True):
        if re.search(rf'\b{re.escape(b.lower())}\b', t):
            return b
    return None


async def retrieve(db: Session, query: str, category: str | None = None, brand: str | None = None, model: str | None = None,
                   error_codes: list[str] | None = None, k: int = 6, include_synthetic: bool = False, use_embeddings: bool = True) -> dict:
    detected = None
    if not category or category == 'unknown':  # appliance-aware even when the session has no appliance yet
        detected = N.detect_appliance(query)
        category = detected if detected != 'unknown' else None
    cats = [category] + RELATED.get(category, []) if category else []
    brand = brand or detect_brand(db, query)
    codes = error_codes if error_codes is not None else N.extract_codes(query)

    def base():
        q = select(RepairRecordRow)
        if cats:
            q = q.where(RepairRecordRow.appliance_category.in_(cats))
        if not include_synthetic:
            q = q.where(RepairRecordRow.verification_status != 'synthetic_demo')
        if model:
            q = q.where(or_(RepairRecordRow.appliance_model.is_(None), func.lower(RepairRecordRow.appliance_model) == model.lower()))
        if brand:  # another brand's record (and its code meanings) never answers this brand's question; brand-less records still can
            q = q.where(or_(RepairRecordRow.appliance_brand.is_(None), func.lower(RepairRecordRow.appliance_brand) == brand.lower()))
        return q

    # Each channel keeps its own signal per record; they are combined once, at the end (see _fuse), so a record found by
    # both keywords and embeddings ranks above one found by either alone, and the two scales are made comparable.
    chan: dict[str, dict] = {}

    def add(row: RepairRecordRow, channel: str, value: float):
        c = chan.setdefault(row.record_id, {'row': row, 'code': 0.0, 'kw': 0.0, 'emb': 0.0})
        c[channel] = max(c[channel], value)

    code_found, code_missing = [], []
    for c in codes:
        rows = db.scalars(base().where(RepairRecordRow.error_code == c).limit(10)).all()
        # Codes a source lists as alternatives (LG 'CH38 / F4') match too, as whole tokens only, so E1 never matches E10.
        alias_rows = db.scalars(base().where(RepairRecordRow.error_code != c, RepairRecordRow.data['error_code_original'].as_string()
                                             .op('~*')(rf'\m{re.escape(c)}\M')).limit(10)).all() if re.fullmatch(r'[A-Z0-9]{1,8}', c) else []
        (code_found if rows or alias_rows else code_missing).append(c)
        for row in rows:
            add(row, 'code', CODE_SCORE)
        for row in alias_rows:
            add(row, 'code', ALIAS_SCORE)

    code_missing = [c for c in code_missing if not any(c.endswith(f) or f.endswith(c) for f in code_found)]  # 'ERIF' alias of found 'IF'
    tsq = _tsquery(query)
    if tsq:
        rank = func.ts_rank(func.to_tsvector('english', RepairRecordRow.search_text), func.to_tsquery('english', tsq))
        rows = db.execute(base().add_columns(rank).where(func.to_tsvector('english', RepairRecordRow.search_text).op('@@')(func.to_tsquery('english', tsq)))
                          .order_by(rank.desc()).limit(40)).all()
        for row, r in rows:
            add(row, 'kw', float(r))

    mode, reason = 'keyword', None
    st = get_settings()
    if use_embeddings and st.vector_search_mode != 'keyword' and get_gemini().configured and st.gemini_embed_model:
        mdl_cfg = get_gemini().model('embed')
        indexed = db.scalar(select(func.count()).select_from(RepairEmbedding).where(RepairEmbedding.source_type == 'record', RepairEmbedding.model_identifier == mdl_cfg)) if mdl_cfg else 0
        try:
            if not indexed:  # no index built: don't spend an embedding call (and free-tier quota) on every message
                raise _NoIndex()
            (qv,), mdl = await get_gemini().embed([query], task='RETRIEVAL_QUERY')
            ids = select(RepairRecordRow.id).where(RepairRecordRow.id.in_(base().with_only_columns(RepairRecordRow.id).scalar_subquery()))
            embs = db.execute(select(RepairEmbedding, RepairRecordRow).join(RepairRecordRow, RepairRecordRow.id == RepairEmbedding.source_id)
                              .where(RepairEmbedding.source_type == 'record', RepairEmbedding.model_identifier == mdl, RepairEmbedding.dimensions == len(qv),
                                     RepairEmbedding.source_id.in_(ids))).all()
            if embs:
                mode = 'hybrid'
                for e, row in embs:
                    sim = cosine(qv, e.vector)
                    if sim > EMB_MIN_SIM:
                        add(row, 'emb', sim)
            else:
                reason = 'No record embeddings for the configured model. Run scripts/index_knowledge.py.'
        except _NoIndex:
            reason = 'No record embeddings for the configured model. Run scripts/index_knowledge.py.'
        except AppError as e:
            reason = f'Embedding call failed ({e.code}); keyword results only.'
    else:
        reason = 'Embeddings not configured or VECTOR_SEARCH_MODE=keyword.'

    ranked = sorted(_fuse(chan, category, brand), key=lambda h: -h.score)[:k]
    for h in ranked:
        if h.record['verification_status'] == 'synthetic_demo':
            h.flags.append('SYNTHETIC_DEMO')
        if h.related:
            h.flags.append('RELATED_CATEGORY')
    coverage = 'none' if not ranked else 'grounded' if any(not h.related and h.match in ('error_code', 'keyword', 'embedding') for h in ranked) else 'partial'
    if codes and code_missing and not code_found:
        coverage = 'partial' if ranked else 'none'
    log(logger, 'retrieve', category=category, detected=detected, brand=brand, codes=codes, hits=len(ranked), mode=mode, coverage=coverage)
    return {'mode': mode, 'fallback_reason': reason, 'coverage': coverage, 'brand': brand, 'category': category, 'category_detected': detected, 'error_codes_found': code_found,
            'error_codes_unknown': code_missing, 'hits': ranked}


def context_block(res: dict) -> str:
    """Evidence passed to Gemini. Each record is tagged with its id so the model can cite it; nothing else may be cited."""
    lines = []
    for h in res['hits']:
        r = h.record
        tag = f"[{h.record_id}] ({r['appliance_category']}{', ' + r['appliance_brand'] if r.get('appliance_brand') else ''}{', ' + r['market'] if r.get('market') else ''}; "
        tag += f"{r['verification_status']}{'; RELATED CATEGORY ONLY' if h.related else ''}{'; SYNTHETIC DEMO, NOT REAL' if 'SYNTHETIC_DEMO' in h.flags else ''})"
        body = []
        if r.get('error_code'): body.append(f"code {r['error_code']}")
        if r.get('reported_symptoms'): body.append('symptoms: ' + '; '.join(r['reported_symptoms'][:4]))
        if r.get('observed_conditions'): body.append('reported: ' + '; '.join(c[:200] for c in r['observed_conditions'][:2]))
        if r.get('possible_faults'): body.append('faults: ' + '; '.join(r['possible_faults'][:4]))
        if r.get('suspected_components'): body.append('components: ' + ', '.join(r['suspected_components'][:4]))
        if r.get('diagnostic_procedure'): body.append('checks: ' + '; '.join(r['diagnostic_procedure'][:4]))
        if r.get('repair_steps'): body.append('source repair steps: ' + '; '.join(s[:200] for s in r['repair_steps'][:3]))
        if r.get('repair_outcome'): body.append(f"outcome: {r['repair_outcome']}")
        lines.append(f"{tag} " + ' | '.join(body))
    hdr = f"Retrieval coverage: {res['coverage']}."
    if res['error_codes_unknown']:
        hdr += f" No record exists for error code(s) {', '.join(res['error_codes_unknown'])}{' for ' + res['brand'] if res['brand'] else ''}: do not state what they mean."
    return hdr + '\n' + ('\n'.join(lines) if lines else '(no matching records)')


def stats(db: Session) -> dict:
    rows = db.execute(select(RepairRecordRow.appliance_category, RepairRecordRow.verification_status, func.count()).group_by(RepairRecordRow.appliance_category, RepairRecordRow.verification_status)).all()
    out: dict = {'total': sum(r[2] for r in rows), 'by_category': {}, 'by_verification_status': {}}
    for c, v, n in rows:
        out['by_category'][c] = out['by_category'].get(c, 0) + n
        out['by_verification_status'][v] = out['by_verification_status'].get(v, 0) + n
    srcs = db.execute(select(RepairRecordRow.source_license, func.count()).group_by(RepairRecordRow.source_license)).all()
    out['by_license'] = {s: n for s, n in srcs}
    out['verification_meaning'] = VERIFICATION_MEANING
    return out


async def index_records(db: Session, batch: int = 50, commit_each_batch: bool = False) -> int:
    """Embed records that have no vector for the configured model, and re-embed those whose text changed since (the stored
    `content` is compared with the record's current text). With commit_each_batch, a quota error part-way keeps earlier batches."""
    g = get_gemini(); mdl = g.model('embed')
    have = {e.source_id: e for e in db.scalars(select(RepairEmbedding).where(RepairEmbedding.source_type == 'record', RepairEmbedding.model_identifier == mdl))}
    rows = [r for r in db.scalars(select(RepairRecordRow).where(RepairRecordRow.verification_status != 'synthetic_demo'))
            if r.id not in have or have[r.id].content != r.search_text[:2000]]
    n = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        vecs, mdl = await g.embed([r.search_text[:2000] for r in chunk])
        for r, v in zip(chunk, vecs):
            e = have.get(r.id)
            if e:  # stale: same row updated in place
                e.content, e.vector, e.dimensions, e.appliance_type = r.search_text[:2000], v, len(v), r.appliance_category
            else:
                db.add(RepairEmbedding(source_type='record', source_id=r.id, appliance_type=r.appliance_category, content=r.search_text[:2000],
                                       model_identifier=mdl, dimensions=len(v), vector=v))
        db.flush(); n += len(chunk)
        if commit_each_batch:
            db.commit()
    return n


def seed_curated(db: Session) -> int:
    """Make sure FixSaathi's own guidance is always present, so the app works before any external dataset is ingested."""
    from ..agents.prompts import KNOWLEDGE_FILE
    from ..datasets.importers import curated
    from ..datasets.pipeline import validate
    cands, _ = curated.load(KNOWLEDGE_FILE)
    recs, _ = validate(cands)
    return ingest(db, recs)['added']
