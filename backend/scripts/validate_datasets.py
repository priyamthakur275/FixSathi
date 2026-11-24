"""Re-validate processed and synthetic JSONL files against the schema. Exit code 1 if anything is invalid."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _paths import PROCESSED, SYNTHETIC
from app.datasets.pipeline import validate

bad = 0
for f in [PROCESSED / 'repair_records.jsonl', SYNTHETIC / 'demo_records.jsonl']:
    if not f.exists():
        print(f'missing: {f}'); continue
    rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    ok, rej = validate(rows)
    print(f'{f.name}: {len(ok)} valid, {len(rej)} invalid')
    for r in rej[:10]:
        print('  ', r)
    bad += len(rej)
    if f.parent == PROCESSED and any(r.verification_status == 'synthetic_demo' for r in ok):
        print('  ERROR: synthetic record found in processed data'); bad += 1
sys.exit(1 if bad else 0)
