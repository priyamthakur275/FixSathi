"""Run Red-Team Challenger against all 36 queries in data/eval/retrieval_holdout_v2.jsonl using real Gemini calls.

Measures honestly:
  - how often Challenger agrees vs disagrees vs fails/times out
  - added Challenger latency (avg, p50, p95 ms)
  - whether Challenger disagreements fall on primary diagnosis misses vs matches

Usage (from backend/):
  python scripts/eval_challenger.py
"""
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(Path(__file__).resolve().parents[1])

from _paths import ROOT
from app.agents import prompts
from app.agents.schemas import ChallengerOutput, DiagnosisOutput
from app.config import get_settings
from app.db.session import SessionLocal
from app.integrations.gemini.client import GeminiClient
from app.services.knowledge_base import context_block, retrieve

EVAL_FILE = ROOT / 'eval' / 'retrieval_holdout_v2.jsonl'
OUT_DETAIL = ROOT / 'eval' / 'challenger_holdout_v2_results.json'
OUT_PUBLIC = Path(__file__).resolve().parents[2] / 'docs' / 'EVALUATION_RESULTS.json'


async def run_one(db, g: GeminiClient, case: dict) -> dict:
    res = await retrieve(db, case['query'], category=case['appliance'], k=6, use_embeddings=False)
    allowed = {h.record_id for h in res['hits']}
    note = prompts.APPLIANCE_NOTES.get(case['appliance'], prompts.APPLIANCE_NOTES['unknown'])
    diag_contents = [
        f"Appliance type: {case['appliance']}. Notes: {note}",
        prompts.wrap('knowledge', context_block(res)),
        prompts.wrap('history', '(none)'),
        prompts.wrap('technician_input', case['query']),
        'No images supplied: do not use observed_in_image evidence.',
    ]
    t0 = time.perf_counter()
    for _retry in range(4):
        try:
            diag_out, diag_meta = await g.generate_json('diagnosis', DiagnosisOutput, diag_contents, prompts.DIAGNOSIS_SYSTEM)
            break
        except Exception as e:
            if getattr(e, 'code', '') == 'QUOTA_EXCEEDED' and _retry < 3:
                await asyncio.sleep(16)
                continue
            raise
    diag_ms = int((time.perf_counter() - t0) * 1000)

    cited = []
    for f in diag_out.possible_faults:
        for r in f.record_ids:
            if r in allowed and r not in cited:
                cited.append(r)
    relevant = set(case['relevant'])
    top_fault_cited = set(diag_out.possible_faults[0].record_ids) & allowed if diag_out.possible_faults else set()
    diag_hit = bool(set(cited) & relevant)
    top_fault_hit = bool(top_fault_cited & relevant)
    conf_before = round(float(diag_out.possible_faults[0].confidence), 3) if diag_out.possible_faults else None

    proposed = {
        'appliance_type': case['appliance'],
        'problem_summary': diag_out.problem_summary,
        'possible_faults': [
            {'fault': f.fault, 'confidence': f.confidence, 'status': f.status, 'record_ids': [r for r in f.record_ids if r in allowed]}
            for f in diag_out.possible_faults[:4]
        ],
        'recommended_checks': diag_out.recommended_checks[:5],
        'safety_requirements': diag_out.safety_requirements[:5],
    }
    ch_contents = [
        f"Appliance: {case['appliance']}. Nameplate: none",
        prompts.wrap('technician_input', case['query']),
        prompts.wrap('knowledge', context_block(res)),
        prompts.wrap('proposed_diagnosis', json.dumps(proposed, ensure_ascii=False)),
    ]
    ct0 = time.perf_counter()
    try:
        for _retry in range(4):
            try:
                ch_out, ch_meta = await g.generate_json('challenger', ChallengerOutput, ch_contents, prompts.CHALLENGER_SYSTEM, temperature=0.1)
                break
            except Exception as e:
                if getattr(e, 'code', '') == 'QUOTA_EXHAUSTED' or getattr(e, 'code', '') == 'QUOTA_EXCEEDED':
                    if _retry < 3:
                        await asyncio.sleep(16)
                        ct0 = time.perf_counter()
                        continue
                raise
        ch_ms = int((time.perf_counter() - ct0) * 1000)
        objections = [
            {
                'claim': o.claim,
                'why': o.why,
                'evidence_id': o.evidence_id if (o.evidence_id in allowed or o.evidence_id == 'technician_input') else None,
            }
            for o in ch_out.objections
        ]
        agrees = bool(ch_out.agrees)
        if not agrees and not objections and not ch_out.missed_checks and not ch_out.safety_concerns:
            agrees = True
        return {
            'id': case['id'],
            'language': case['language'],
            'appliance': case['appliance'],
            'query': case['query'],
            'relevant': case['relevant'],
            'retrieval_hit_top1': bool(res['hits'] and res['hits'][0].record_id in relevant),
            'diag_model': diag_meta.model,
            'diag_ms': diag_ms,
            'diag_cited': cited,
            'diag_hit': diag_hit,
            'top_fault_hit': top_fault_hit,
            'confidence_before': conf_before,
            'challenger_status': 'ok',
            'challenger_model': ch_meta.model,
            'challenger_ms': ch_ms,
            'agrees': agrees,
            'revised_confidence': round(float(ch_out.revised_confidence), 3),
            'objections': objections,
            'missed_checks': list(ch_out.missed_checks),
            'safety_concerns': list(ch_out.safety_concerns),
        }
    except Exception as e:
        ch_ms = int((time.perf_counter() - ct0) * 1000)
        return {
            'id': case['id'],
            'language': case['language'],
            'appliance': case['appliance'],
            'query': case['query'],
            'relevant': case['relevant'],
            'retrieval_hit_top1': bool(res['hits'] and res['hits'][0].record_id in relevant),
            'diag_model': diag_meta.model,
            'diag_ms': diag_ms,
            'diag_cited': cited,
            'diag_hit': diag_hit,
            'top_fault_hit': top_fault_hit,
            'confidence_before': conf_before,
            'challenger_status': 'unavailable',
            'challenger_model': None,
            'challenger_ms': ch_ms,
            'agrees': None,
            'error': getattr(e, 'code', type(e).__name__),
        }


async def main() -> None:
    s = get_settings()
    if not s.ai_configured:
        raise SystemExit('GEMINI_API_KEY must be set in backend/.env to run eval_challenger.py')
    # Pin to the exact deployed model path (gemini-3.5-flash-lite) so numbers match production
    s.gemini_agent_model = 'gemini-3.5-flash-lite'
    s.gemini_fast_model = 'gemini-3.5-flash-lite'
    s.gemini_agent_fallback_models = ''
    s.gemini_thinking_level = 'low'
    s.gemini_challenger_timeout_seconds = 10.0  # allow measurement of true tail latency during offline eval

    cases = [json.loads(l) for l in EVAL_FILE.read_text(encoding='utf-8').splitlines() if l.strip()]
    g = GeminiClient()
    results = []
    with SessionLocal() as db:
        for i, c in enumerate(cases, 1):
            r = await run_one(db, g, c)
            results.append(r)
            tag = 'AGREE' if r['agrees'] is True else 'DISAGREE' if r['agrees'] is False else 'UNAVAIL'
            print(f"[{i:02d}/{len(cases)}] {c['id']} {tag:8s} ch_ms={r['challenger_ms']:4d} diag_hit={r['diag_hit']} top_hit={r['top_fault_hit']}", flush=True)
            if i < len(cases):
                await asyncio.sleep(8.5)

    ok_rows = [r for r in results if r['challenger_status'] == 'ok']
    agreed = [r for r in ok_rows if r['agrees'] is True]
    disagreed = [r for r in ok_rows if r['agrees'] is False]
    unavail = [r for r in results if r['challenger_status'] != 'ok']
    latencies = [r['challenger_ms'] for r in ok_rows]
    disagreed_on_miss = [r for r in disagreed if not r['top_fault_hit']]
    disagreed_on_hit = [r for r in disagreed if r['top_fault_hit']]
    agreed_on_miss = [r for r in agreed if not r['top_fault_hit']]

    summary = {
        'date': str(date.today()),
        'dataset': 'held_out_v2',
        'cases': len(results),
        'model': 'gemini-3.5-flash-lite',
        'ok_count': len(ok_rows),
        'unavailable_count': len(unavail),
        'agrees_count': len(agreed),
        'disagrees_count': len(disagreed),
        'agree_rate': round(len(agreed) / len(ok_rows), 3) if ok_rows else 0.0,
        'disagree_rate': round(len(disagreed) / len(ok_rows), 3) if ok_rows else 0.0,
        'safety_concerns_flagged': sum(1 for r in ok_rows if r.get('safety_concerns')),
        'avg_latency_ms': int(statistics.mean(latencies)) if latencies else 0,
        'median_latency_ms': int(statistics.median(latencies)) if latencies else 0,
        'max_latency_ms': max(latencies) if latencies else 0,
        'disagreements_on_top_fault_miss': len(disagreed_on_miss),
        'disagreements_on_top_fault_hit': len(disagreed_on_hit),
        'agreements_on_top_fault_miss': len(agreed_on_miss),
        'note': (
            'Primary diagnosis and adversarial challenger both ran unmocked via gemini-3.5-flash-lite over all 36 held_out_v2 queries. '
            'Disagreements are broken down by whether the primary top fault cited a ground-truth relevant record.'
        ),
        'disagreements': [
            {
                'id': r['id'],
                'query': r['query'],
                'top_fault_hit': r['top_fault_hit'],
                'diag_hit': r['diag_hit'],
                'confidence_before': r.get('confidence_before'),
                'revised_confidence': r.get('revised_confidence'),
                'claim': (r['objections'][0]['claim'] if r.get('objections') else (r['safety_concerns'][0] if r.get('safety_concerns') else (r['missed_checks'][0] if r.get('missed_checks') else ''))),
                'why': (r['objections'][0]['why'] if r.get('objections') else ''),
            }
            for r in disagreed[:12]
        ],
    }

    OUT_DETAIL.write_text(json.dumps({'summary': summary, 'results': results}, indent=2, ensure_ascii=False), encoding='utf-8')
    pub = json.loads(OUT_PUBLIC.read_text(encoding='utf-8'))
    pub['challenger_holdout_v2'] = summary
    OUT_PUBLIC.write_text(json.dumps(pub, indent=1, ensure_ascii=False), encoding='utf-8')
    print('\n=== SUMMARY ===')
    print(json.dumps({k: v for k, v in summary.items() if k != 'disagreements'}, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
