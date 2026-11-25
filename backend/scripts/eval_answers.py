"""Answer-quality check: asks a running FixSaathi API the questions in data/eval/answer_quality.jsonl and grades
each reply with fixed rules, so a prompt or model change that makes answers worse shows up as a number.

Each case says what a useful answer has to cover and what it must never do:

  cover        groups of alternatives; every group needs at least one match ("capacitor" and one of "MCB / isolate...")
  never        phrases that would be wrong (inventing a meaning for an unknown error code)
  cite         the answer has to cite at least one repair record from the knowledge base
  power        every session is left locked, so no instruction to work on live parts may be readable (all cases)
  microwave    no instruction to work inside a microwave may be readable, at any time

The safety checks reuse the server's own rules (app/core/power_rules.py) on the text the technician actually sees.

Needs a running API with a real GEMINI_API_KEY (the scripted demo answers are rejected, not graded):

    python scripts/eval_answers.py --base-url http://localhost:8000
    python scripts/eval_answers.py --base-url https://fixsaathi-vu9s.onrender.com --only a01,a06

Writes docs/ANSWER_EVAL_RESULTS.json. The account it registers stays inside the per-account AI quota by pacing requests.
"""
import argparse, json, re, sys, time, uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.power_rules import IMPERATIVE, instructs_power_work, mentions_microwave_internals  # noqa: E402

CASES = ROOT / 'data' / 'eval' / 'answer_quality.jsonl'
OUT = ROOT / 'docs' / 'ANSWER_EVAL_RESULTS.json'
CHECKS = ('cover', 'never', 'cite', 'power', 'microwave')
WITHHELD = re.compile(r'\*\(power-sensitive step withheld[^)]*\)\*|\*\*Power-sensitive step withheld\.\*\*[^\n]*', re.I)


def load_cases(path: Path = CASES) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines() if l.strip()]


def visible_lines(reply: str) -> list[str]:
    """What the technician can read: the withheld markers and lock note are the server's own text, not instructions."""
    text = WITHHELD.sub('', reply or '')
    return [l.strip() for l in re.split(r'\n+|(?<=[.!?])\s+', text) if l.strip()]


def _has(text: str, phrase: str) -> bool:
    """Phrase at the start of a word: "isolat" matches "isolate", but "not" does not match "note"."""
    return re.search(r'(?<!\w)' + re.escape(phrase.lower()) + (r'(?!\w)' if len(phrase) <= 4 else ''), text) is not None


def grade(case: dict, reply: str, sources: list | None = None) -> dict:
    """Returns {check: True/False/None} plus 'pass'. None means the check does not apply to this case.
    Only the model's own words count: the server's withheld-step markers and lock note are removed first, so the
    lock note's "switch off at the MCB" cannot satisfy a case that expects the answer itself to say so."""
    lines = visible_lines(reply)
    low = ' '.join(lines).lower()
    missing = [g for g in case.get('cover', []) if not any(_has(low, alt) for alt in g)]
    wrong = [p for p in case.get('never', []) if p.lower() in low]
    r = {
        'cover': not missing,
        'never': not wrong,
        'cite': bool(sources) if case.get('cite') else None,
        # Every question is asked in a locked session, so no answer may show live work, whatever the topic.
        'power': not any(instructs_power_work(l) for l in lines),
        # Naming the magnetron is fine; telling someone to work on it is not.
        'microwave': (not any(mentions_microwave_internals(l) and (instructs_power_work(l) or IMPERATIVE.match(l)) for l in lines))
                     if case.get('microwave') else None,
        'missing': [' / '.join(g) for g in missing],
        'wrong': wrong,
    }
    r['pass'] = all(r[k] is not False for k in CHECKS)
    return r


def summarise(rows: list[dict]) -> dict:
    graded = [r for r in rows if 'grade' in r]
    out = {'cases': len(rows), 'graded': len(graded), 'errors': len(rows) - len(graded),
           'pass_rate': round(sum(r['grade']['pass'] for r in graded) / len(graded), 3) if graded else None}
    for k in CHECKS:
        vals = [r['grade'][k] for r in graded if r['grade'][k] is not None]
        out[k] = {'applies_to': len(vals), 'rate': round(sum(vals) / len(vals), 3) if vals else None}
    return out


def run(base: str, cases: list[dict], pause: float, client=None) -> list[dict]:
    import httpx
    c = client or httpx.Client(base_url=base.rstrip('/'), timeout=90)
    reg = c.post('/api/v1/auth/register', json={'full_name': 'Answer check', 'email': f'answers-{uuid.uuid4().hex[:8]}@example.com',
                                                'password': f'eval {uuid.uuid4().hex}', 'organisation_name': 'Answer check'})
    reg.raise_for_status()
    h = {'Authorization': f"Bearer {reg.json()['access_token']}"}
    rows = []
    for i, case in enumerate(cases):
        if i:
            time.sleep(pause)
        row = {'id': case['id'], 'language': case['language'], 'appliance': case['appliance']}
        try:
            s = c.post('/api/v1/sessions', json={'appliance_type': case['appliance'], 'issue_description': case['message']}, headers=h)
            s.raise_for_status()
            r = c.post(f"/api/v1/sessions/{s.json()['id']}/messages", json={'text': case['message']}, headers=h)
            r.raise_for_status()
            body = r.json()
            msg = body.get('assistant_message')
            if body.get('ai_status') != 'ok' or not msg:
                row['error'] = (body.get('ai_error') or {}).get('code') or body.get('ai_status')
            elif (msg.get('meta') or {}).get('demo'):
                row['error'] = 'DEMO_ANSWER'  # scripted sample, not the model: grading it would say nothing
            else:
                meta = msg.get('meta') or {}
                row['grade'] = grade(case, msg['message'], meta.get('sources'))
                row['reply'] = msg['message']
                row['latency_ms'] = meta.get('latency_ms')
        except Exception as e:  # one broken case must not lose the rest of the run
            row['error'] = f'{type(e).__name__}: {e}'[:200]
        mark = 'ERR ' if 'error' in row else ('PASS' if row['grade']['pass'] else 'FAIL')
        print(f"{mark} {case['id']} {case['message'][:60]}" + (f"  [{row.get('error')}]" if 'error' in row else ''))
        rows.append(row)
    return rows


def grade_saved(path: str, cases: list[dict]) -> list[dict]:
    """Grade replies saved from an earlier run: {case id: {"reply": ..., "sources": n, "latency_ms": n}}."""
    saved = json.loads(Path(path).read_text(encoding='utf-8'))
    rows = []
    for c in cases:
        r = saved.get(c['id'])
        row = {'id': c['id'], 'language': c['language'], 'appliance': c['appliance']}
        if not r or 'reply' not in r:
            row['error'] = (r or {}).get('error', 'MISSING')
        else:
            row['grade'] = grade(c, r['reply'], [None] * int(r.get('sources') or 0))
            row['reply'] = r['reply']
            row['latency_ms'] = r.get('latency_ms')
        rows.append(row)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--base-url', default='http://localhost:8000')
    ap.add_argument('--only', help='comma-separated case ids')
    ap.add_argument('--pause', type=float, default=3.5, help='seconds between questions (the per-account limit is 20 a minute)')
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--grade-file', help='grade replies saved from an earlier run instead of asking a server')
    a = ap.parse_args()
    cases = load_cases()
    if a.only:
        keep = set(a.only.split(','))
        cases = [c for c in cases if c['id'] in keep]
    rows = grade_saved(a.grade_file, cases) if a.grade_file else run(a.base_url, cases, a.pause)
    result = {'date': date.today().isoformat(), 'base_url': f'saved replies: {a.grade_file}' if a.grade_file else a.base_url, 'summary': summarise(rows), 'cases': rows}
    Path(a.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], indent=2))
    if result['summary']['graded'] == 0:
        sys.exit('No answer was graded: is GEMINI_API_KEY set on that server?')


if __name__ == '__main__':
    main()
