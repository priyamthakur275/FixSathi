"""raw -> processed. Normalises every available source into the unified schema, validates, de-duplicates, and writes:
    data/processed/repair_records.jsonl   valid records
    data/processed/rejected.jsonl        rejected candidates with reasons
    data/processed/processing_report.json counts (real, computed from this run)
Synthetic demo records (data/synthetic/) are validated separately and never mixed into processed output.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _paths import PROCESSED, RAW, SCHEMAS, SYNTHETIC
from app.agents.prompts import KNOWLEDGE_FILE
from app.datasets.importers import appliancedb, curated, manufacturer_docs, openrepair
from app.datasets.pipeline import report, to_jsonl, validate
from app.datasets.schema import RepairRecord


def main():
    candidates, skipped = [], {}
    c, s = curated.load(KNOWLEDGE_FILE); candidates += c; skipped['fixsaathi_curated'] = s
    adb = RAW / 'appliancedb'
    if (adb / 'error_codes.csv').exists():
        commit = json.loads((adb / 'FETCH_INFO.json').read_text()).get('commit') if (adb / 'FETCH_INFO.json').exists() else None
        c, s = appliancedb.load(adb, commit); candidates += c; skipped['appliancedb'] = s
    else:
        print('ApplianceDB not found in data/raw/appliancedb (run download_datasets.py)')
    mfr = RAW / 'manufacturer_docs'
    if (mfr / 'records.json').exists():
        c, s = manufacturer_docs.load(mfr); candidates += c; skipped['manufacturer_docs'] = s
    for f in sorted((RAW / 'openrepair').glob('*.csv')) if (RAW / 'openrepair').exists() else []:
        c, s = openrepair.load(f); candidates += c; skipped[f'openrepair:{f.name}'] = s
    records, rejected = validate(candidates)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / 'repair_records.jsonl').write_text(to_jsonl(records))
    (PROCESSED / 'rejected.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rejected))
    rep = report(records, rejected, skipped)
    syn = SYNTHETIC / 'demo_records.jsonl'
    if syn.exists():
        srecs, srej = validate([json.loads(l) for l in syn.read_text().splitlines() if l.strip()])
        rep['synthetic_demo'] = {'valid': len(srecs), 'rejected': len(srej), 'note': 'Kept separate. Not ingested unless --include-synthetic.'}
    (PROCESSED / 'processing_report.json').write_text(json.dumps(rep, indent=1))
    SCHEMAS.mkdir(parents=True, exist_ok=True)
    (SCHEMAS / 'repair_record.schema.json').write_text(json.dumps(RepairRecord.model_json_schema(), indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == '__main__':
    main()
