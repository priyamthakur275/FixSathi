"""Offline evaluation of the two parts of FixSaathi that decide what a technician sees:

1. Retrieval: for each fault description in data/eval/retrieval_*.jsonl, is a correct repair record among the
   records Gemini is given? Measured twice: with the appliance the technician picked, and with no appliance (detected
   from the text). Reports Hit@1, Hit@3, MRR and appliance-detection accuracy, overall and per language and appliance.
2. Safety filter: for each sentence in data/eval/safety_*.jsonl, does the server-side rule withhold instructions
   that need the power isolated, and leave diagnosis, questions and safety reminders readable?

Needs a PostgreSQL database with the records loaded (alembic upgrade head && python scripts/ingest_knowledge.py).
Embeddings are off by default so the result is reproducible without an API key: --embeddings adds the Gemini channel.
No answer is generated, so no model output is graded here.

    python scripts/evaluate.py                 # prints a summary, writes docs/EVALUATION_RESULTS.json
    python scripts/evaluate.py --embeddings    # also uses Gemini embeddings (needs GEMINI_API_KEY and an index)
"""
import argparse, asyncio, json, os, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _paths import ROOT
from app.core.power_rules import instructs_power_work
from app.datasets.normalize import detect_appliance
from app.db.session import SessionLocal
from app.services.knowledge_base import retrieve

EVAL = ROOT / 'eval'
OUT = Path(__file__).resolve().parents[2] / 'docs' / 'EVALUATION_RESULTS.json'


def _rank(hit_ids: list[str], relevant: set[str]) -> int | None:
    return next((i + 1 for i, r in enumerate(hit_ids) if r in relevant), None)


def _summary(rows: list[dict]) -> dict:
    n = len(rows)
    ranks = [r['rank'] for r in rows]
    return {'cases': n, 'hit@1': round(sum(1 for k in ranks if k == 1) / n, 3), 'hit@3': round(sum(1 for k in ranks if k and k <= 3) / n, 3),
            'hit@6': round(sum(1 for k in ranks if k) / n, 3), 'mrr': round(sum(1 / k for k in ranks if k) / n, 3)}


def _grouped(rows: list[dict], key: str) -> dict:
    g = defaultdict(list)
    for r in rows:
        g[r[key]].append(r)
    return {k: _summary(v) for k, v in sorted(g.items())}


def _load(name: str) -> list[dict]:
    return [json.loads(l) for l in (EVAL / name).read_text().splitlines() if l.strip()]


async def eval_retrieval(cases: list[dict], embeddings: bool) -> dict:
    out = {}
    with SessionLocal() as db:
        for mode in ('appliance_selected', 'appliance_detected'):
            rows = []
            for c in cases:
                res = await retrieve(db, c['query'], category=c['appliance'] if mode == 'appliance_selected' else None, k=6, use_embeddings=embeddings)
                ids = [h.record_id for h in res['hits']]
                rows.append({'id': c['id'], 'language': c['language'], 'appliance': c['appliance'], 'query': c['query'],
                             'rank': _rank(ids, set(c['relevant'])), 'top3': ids[:3]})
            out[mode] = {'overall': _summary(rows), 'by_language': _grouped(rows, 'language'), 'by_appliance': _grouped(rows, 'appliance'),
                         'misses_top3': [{'id': r['id'], 'query': r['query'], 'rank': r['rank'], 'top3': r['top3']} for r in rows if not r['rank'] or r['rank'] > 3]}
    detected = sum(1 for c in cases if detect_appliance(c['query']) == c['appliance'])
    out['appliance_detection_accuracy'] = round(detected / len(cases), 3)
    out['appliance_detection_misses'] = [{'id': c['id'], 'query': c['query'], 'expected': c['appliance'], 'got': detect_appliance(c['query'])}
                                         for c in cases if detect_appliance(c['query']) != c['appliance']]
    return out


def eval_safety(cases: list[dict]) -> dict:
    tp = fn = fp = tn = 0
    errors = []
    for c in cases:
        flagged = instructs_power_work(c['text'])
        unsafe = c['label'] == 'instruction_needs_isolation'
        tp += unsafe and flagged; fn += unsafe and not flagged; fp += (not unsafe) and flagged; tn += (not unsafe) and not flagged
        if flagged != unsafe:
            errors.append({'id': c['id'], 'text': c['text'], 'expected': c['label'], 'withheld': flagged})
    return {'cases': len(cases), 'unsafe_withheld': f'{tp}/{tp + fn}', 'recall_unsafe': round(tp / (tp + fn), 3),
            'safe_shown': f'{tn}/{tn + fp}', 'false_positive_rate': round(fp / (tn + fp), 3), 'errors': errors}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--embeddings', action='store_true'); p.add_argument('--no-write', action='store_true'); a = p.parse_args()
    result = {'date': date.today().isoformat(), 'retrieval_channels': 'error code + PostgreSQL full-text' + (' + Gemini embeddings' if a.embeddings else ''),
              'note': ('development = the sets the Hindi search terms, the take-out rule and the field-weighted ranking were fixed against; '
                       'held_out = written after the first fixes and not used to change any code; '
                       'held_out_v2 = retrieval only, written before the field-weighted ranking was measured on it and not used to tune it.')}
    for split, (rq, sq) in {'development': ('retrieval_benchmark.jsonl', 'safety_benchmark.jsonl'),
                            'held_out': ('retrieval_holdout.jsonl', 'safety_holdout.jsonl'),
                            'held_out_v2': ('retrieval_holdout_v2.jsonl', None)}.items():
        r = asyncio.run(eval_retrieval(_load(rq), a.embeddings)); s = eval_safety(_load(sq)) if sq else None
        result[split] = {'retrieval': r, 'safety_filter': s} if s else {'retrieval': r}
        print(f'--- {split}')
        for mode in ('appliance_selected', 'appliance_detected'):
            o = r[mode]['overall']
            print(f"{mode:20s} cases={o['cases']} hit@1={o['hit@1']:.1%} hit@3={o['hit@3']:.1%} mrr={o['mrr']:.3f}")
        print(f"appliance detection   {r['appliance_detection_accuracy']:.1%}")
        if s:
            print(f"safety filter         unsafe withheld {s['unsafe_withheld']}, safe shown {s['safe_shown']}")
    if not a.no_write:
        OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False) + '\n')
        print('wrote', OUT)


if __name__ == '__main__':
    main()
