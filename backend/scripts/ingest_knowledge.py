"""Load processed records into PostgreSQL (repair_records). Idempotent upsert by record_id.

    python scripts/ingest_knowledge.py                      # processed records only
    python scripts/ingest_knowledge.py --include-synthetic  # also demo records (flagged, excluded from retrieval by default)
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _paths import PROCESSED, SYNTHETIC
from app.datasets.pipeline import validate
from app.db.session import SessionLocal
from app.services.knowledge_base import ingest, stats

p = argparse.ArgumentParser(); p.add_argument('--include-synthetic', action='store_true'); p.add_argument('--if-present', action='store_true', help='exit 0 quietly if no processed file'); a = p.parse_args()
if a.if_present and not (PROCESSED / 'repair_records.jsonl').exists():
    print(f'No processed records at {PROCESSED}; skipping ingestion.'); sys.exit(0)
files = [PROCESSED / 'repair_records.jsonl'] + ([SYNTHETIC / 'demo_records.jsonl'] if a.include_synthetic else [])
db = SessionLocal()
for f in files:
    recs, rej = validate([json.loads(l) for l in f.read_text().splitlines() if l.strip()])
    if rej:
        sys.exit(f'{f.name}: {len(rej)} invalid records; run validate_datasets.py')
    print(f.name, ingest(db, recs))
db.commit()
print(json.dumps({k: v for k, v in stats(db).items() if k != 'verification_meaning'}, indent=1))
