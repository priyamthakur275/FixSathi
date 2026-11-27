"""Repair knowledge base over `repair_records`.

retrieve(): structured filters (category, brand, model, error code) → PostgreSQL full-text keyword ranking →
optional Gemini-embedding re-ranking. Synthetic demo records are excluded unless include_synthetic=True.
Every hit carries its record_id, source, licence and verification status so answers can cite it.
"""
import copy, logging, math, re, threading, time
from collections import OrderedDict
from dataclasses import dataclass, field
from sqlalchemy import func, or_, select, text, true
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
CODE_RECORD_NO_CODE = 0.9
# Everyday English words for the same thing, mapped to the words the records use. Search terms only; nothing is added to records.
SYNONYMS = {'plate': 'turntable', 'tray': 'turntable', 'rotate': 'turntable', 'rotates': 'turntable', 'rotating': 'turntable',
            'switches': 'turns', 'switched': 'turns', 'timer': 'time', 'odour': 'smell', 'odor': 'smell', 'stink': 'smell',
            'stinks': 'smell', 'cold': 'cooling', 'chilling': 'cooling', 'tripping': 'trips', 'buzzing': 'humming', 'alarm': 'beeping'}
# Common Hinglish words technicians type, mapped to the English words the records use. Search terms only; nothing is added to records.
HINGLISH = {'pankha': 'fan', 'pankhe': 'fan', 'thanda': 'cool', 'thandi': 'cool', 'garam': 'hot', 'awaaz': 'noise',
            'awaz': 'noise', 'aawaz': 'noise', 'paani': 'water', 'pani': 'water', 'ghoom': 'spin', 'ghum': 'spin', 'ghumta': 'spin',
            'dhuan': 'smoke', 'dhuaan': 'smoke', 'badbu': 'smell', 'tapak': 'leak', 'tapakna': 'leak', 'bijli': 'power', 'jhatka': 'shock',
            'hil': 'vibration wobbling shaking', 'hilta': 'vibration wobbling shaking', 'barf': 'ice', 'dheema': 'slow', 'dheere': 'slow', 'dhire': 'slow',
            'nikal': 'drain', 'nikalta': 'drain', 'beep': 'beeping', 'chingari': 'spark', 'jal': 'burning', 'jala': 'burning'}
# The same for Hindi typed in Devanagari (voice input in Hindi arrives this way). Without it a Hindi message finds no records
# by keyword at all; the embedding channel, when configured, also understands Hindi.
DEVANAGARI = {'पंखा': 'fan', 'पंखे': 'fan', 'ठंडा': 'cool', 'ठंडी': 'cool', 'ठंडक': 'cooling', 'कूलिंग': 'cooling', 'गरम': 'hot',
              'गर्म': 'hot', 'आवाज़': 'noise', 'आवाज': 'noise', 'शोर': 'noise', 'पानी': 'water', 'घूम': 'spin', 'घूमता': 'spin',
              'धुआं': 'smoke', 'धुआँ': 'smoke', 'बदबू': 'smell', 'टपक': 'leak', 'लीक': 'leak', 'बिजली': 'power', 'झटका': 'shock',
              'बर्फ': 'ice', 'धीमा': 'slow', 'धीरे': 'slow', 'हिल': 'vibration wobbling shaking', 'निकल': 'drain', 'बीप': 'beeping', 'चिंगारी': 'spark',
              'बंद': 'stops', 'चालू': 'start', 'स्वाद': 'taste', 'दरवाजा': 'door', 'दरवाज़ा': 'door', 'लाइट': 'light',
              'एसी': 'ac', 'फ्रिज': 'fridge', 'फ्रीज': 'fridge', 'मशीन': 'machine', 'माइक्रोवेव': 'microwave', 'प्यूरीफायर': 'purifier'}
DEV_WORD = re.compile(r'[\u0900-\u097F]+')

_CACHE_MAX = 256
_CACHE_TTL_S = 300.0
_CACHE_LOCK = threading.RLock()
_BRANDS_CACHE: tuple[float, list[str]] | None = None
_RETRIEVE_CACHE: OrderedDict[tuple, tuple[float, dict]] = OrderedDict()
_CACHE_STATS = {'hits': 0, 'misses': 0}


def clear_cache() -> None:
    """Drop cached brand lists and retrieval hits (called on ingest, re-index, and in tests)."""
    global _BRANDS_CACHE
    with _CACHE_LOCK:
        _BRANDS_CACHE = None
        _RETRIEVE_CACHE.clear()
        _CACHE_STATS['hits'] = 0
        _CACHE_STATS['misses'] = 0


def cache_stats() -> dict[str, int]:
    """Return a snapshot of knowledge-lookup cache hits and misses."""
    with _CACHE_LOCK:
        return dict(_CACHE_STATS)


def _lexemes(expr):
    return func.coalesce(func.array_to_string(func.tsvector_to_array(expr), ' '), '')


def _keyword_scores(db: Session, pool, tsq: str, limit: int = 60) -> list[tuple['RepairRecordRow', float]]:
    """Keyword channel, scored like a small BM25F: each query word counts by how rare it is among this appliance's records
    (inverse document frequency) and by where it appears in the record: in the reported symptoms or error code it counts
    fully, in the possible faults or components 0.6, elsewhere (procedures, repair text) 0.25. So "Kent RO keeps beeping"
    ranks the record whose symptom is beeping above the many records that merely say "RO purifier", and a symptom query
    with no code ranks the record about that symptom above long error-code records that mention the word in passing.
    PostgreSQL does the stemming and the candidate search (GIN index); the arithmetic is done here on at most `limit` rows."""
    q_lex = [x for x in (db.scalar(select(func.array_to_string(func.tsvector_to_array(func.to_tsvector('english', tsq.replace('|', ' '))), ' '))) or '').split() if x]
    if not q_lex:
        return []
    ids = pool.with_only_columns(RepairRecordRow.id).subquery()
    n_docs = db.scalar(select(func.count()).select_from(ids)) or 1
    lex = func.unnest(func.tsvector_to_array(func.to_tsvector('english', RepairRecordRow.search_text))).table_valued('lexeme').render_derived().lateral()
    df = dict(db.execute(select(lex.c.lexeme, func.count()).select_from(RepairRecordRow).join(lex, true())
                         .where(RepairRecordRow.id.in_(select(ids.c.id)), lex.c.lexeme.in_(q_lex)).group_by(lex.c.lexeme)).all())
    idf = {t: math.log(1 + (n_docs - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5)) for t in q_lex}
    d = RepairRecordRow.data
    head = func.to_tsvector('english', func.coalesce(d['reported_symptoms'], text("'[]'::jsonb"))).op('||')(
        func.to_tsvector('english', func.coalesce(RepairRecordRow.error_code, '')))
    mid = func.to_tsvector('english', func.coalesce(d['possible_faults'], text("'[]'::jsonb"))).op('||')(
        func.to_tsvector('english', func.coalesce(d['suspected_components'], text("'[]'::jsonb"))))
    rows = db.execute(pool.add_columns(_lexemes(head), _lexemes(mid), _lexemes(func.to_tsvector('english', RepairRecordRow.search_text)))
                      .where(func.to_tsvector('english', RepairRecordRow.search_text).op('@@')(func.to_tsquery('english', tsq)))).all()
    out = []
    for row, h, m, body in rows:
        h, m, body = set(h.split()), set(m.split()), set(body.split())
        score = sum(idf[t] * (1.0 if t in h else 0.6 if t in m else 0.25 if t in body else 0.0) for t in q_lex)
        if score > 0:
            out.append((row, score))
    out.sort(key=lambda x: -x[1])
    return out[:limit]


def _fuse(chan: dict[str, dict], category: str | None, brand: str | None, codes_asked: bool = True) -> list['Hit']:
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
        if not codes_asked and row.error_code:  # no code on the display: a record about the symptom beats one about a code
            score *= CODE_RECORD_NO_CODE
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
    clear_cache()
    return {'added': added, 'updated': updated, 'unchanged': len(records) - added - updated}


def _tsquery(q: str) -> str | None:
    toks = []
    for t in WORD.findall(q.lower()):
        if t in HINGLISH:
            toks.extend(HINGLISH[t].split())
        if t in SYNONYMS:
            toks.extend(SYNONYMS[t].split())
        if t not in STOP:
            toks.append(t)
    for t in DEV_WORD.findall(q):
        en = DEVANAGARI.get(t) or next((v for k, v in DEVANAGARI.items() if t.startswith(k)), None)
        toks.extend(w for w in (en or '').split() if w not in STOP)
    return ' | '.join(dict.fromkeys(toks[:32])) or None


def known_brands(db: Session) -> list[str]:
    global _BRANDS_CACHE
    now = time.monotonic()
    with _CACHE_LOCK:
        if _BRANDS_CACHE and now - _BRANDS_CACHE[0] < _CACHE_TTL_S:
            return list(_BRANDS_CACHE[1])
    vals = [b for (b,) in db.execute(select(RepairRecordRow.appliance_brand).where(RepairRecordRow.appliance_brand.is_not(None)).distinct())]
    with _CACHE_LOCK:
        _BRANDS_CACHE = (now, list(vals))
    return vals


def detect_brand(db: Session, text_: str) -> str | None:
    t = f' {text_.lower()} '
    for b in sorted(known_brands(db) + list(set(N.BRANDS.values())), key=len, reverse=True):
        if re.search(rf'\b{re.escape(b.lower())}\b', t):
            return b
    return None


async def retrieve(db: Session, query: str, category: str | None = None, brand: str | None = None, model: str | None = None,
                   error_codes: list[str] | None = None, k: int = 6, include_synthetic: bool = False, use_embeddings: bool = True) -> dict:
    st = get_settings()
    cache_key = (
        ' '.join((query or '').strip().lower().split()),
        category or '',
        (brand or '').strip().lower(),
        (model or '').strip().lower(),
        tuple(error_codes) if error_codes is not None else None,
        k,
        include_synthetic,
        use_embeddings,
        st.vector_search_mode,
        bool(get_gemini().configured and st.gemini_embed_model),
    )
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _RETRIEVE_CACHE.get(cache_key)
        if cached and now - cached[0] < _CACHE_TTL_S:
            _RETRIEVE_CACHE.move_to_end(cache_key)
            _CACHE_STATS['hits'] += 1
            return copy.deepcopy(cached[1])
        if cached:
            del _RETRIEVE_CACHE[cache_key]
        _CACHE_STATS['misses'] += 1

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
        for row, score in _keyword_scores(db, base(), tsq):
            add(row, 'kw', score)

    mode, reason = 'keyword', None
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

    ranked = sorted(_fuse(chan, category, brand, codes_asked=bool(codes)), key=lambda h: (-h.score, h.record_id))[:k]
    for h in ranked:
        if h.record['verification_status'] == 'synthetic_demo':
            h.flags.append('SYNTHETIC_DEMO')
        if h.related:
            h.flags.append('RELATED_CATEGORY')
    coverage = 'none' if not ranked else 'grounded' if any(not h.related and h.match in ('error_code', 'keyword', 'embedding') for h in ranked) else 'partial'
    if codes and code_missing and not code_found:
        coverage = 'partial' if ranked else 'none'
    log(logger, 'retrieve', category=category, detected=detected, brand=brand, codes=codes, hits=len(ranked), mode=mode, coverage=coverage)
    out = {'mode': mode, 'fallback_reason': reason, 'coverage': coverage, 'brand': brand, 'category': category, 'category_detected': detected, 'error_codes_found': code_found,
           'error_codes_unknown': code_missing, 'hits': ranked}
    with _CACHE_LOCK:
        _RETRIEVE_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(out))
        _RETRIEVE_CACHE.move_to_end(cache_key)
        while len(_RETRIEVE_CACHE) > _CACHE_MAX:
            _RETRIEVE_CACHE.popitem(last=False)
    return out


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
    if n > 0:
        clear_cache()
    return n


def seed_curated(db: Session) -> int:
    """Make sure FixSaathi's own guidance is always present, so the app works before any external dataset is ingested."""
    from ..agents.prompts import KNOWLEDGE_FILE
    from ..datasets.importers import curated
    from ..datasets.pipeline import validate
    cands, _ = curated.load(KNOWLEDGE_FILE)
    recs, _ = validate(cands)
    return ingest(db, recs)['added']
