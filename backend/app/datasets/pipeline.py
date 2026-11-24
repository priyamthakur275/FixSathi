"""Validation + de-duplication. Pure functions so they are easy to test."""
import hashlib, json
from collections import Counter
from pydantic import ValidationError
from .schema import RepairRecord


def content_key(r: RepairRecord) -> str:
    """Two records are duplicates only if brand, market, category, model, code AND the stated fault match.
    Same code on a different model, brand, market or appliance stays a separate record."""
    basis = [r.appliance_category, (r.appliance_brand or '').lower(), (r.market or '').lower(), (r.appliance_model or '').lower(), r.error_code or '',
             ' '.join(sorted(f.lower() for f in r.possible_faults)), ' '.join(sorted(s.lower() for s in r.observed_conditions))]
    return hashlib.sha256('|'.join(basis).encode()).hexdigest()


def validate(candidates: list[dict]) -> tuple[list[RepairRecord], list[dict]]:
    ok, rejected = [], []
    seen_ids: set[str] = set(); seen_content: dict[str, str] = {}
    for c in candidates:
        try:
            r = RepairRecord.model_validate(c)
        except ValidationError as e:
            rejected.append({'record_id': c.get('record_id'), 'source_record_id': c.get('source_record_id'), 'reason': 'invalid',
                             'errors': [f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()][:5]}); continue
        if r.record_id in seen_ids:
            rejected.append({'record_id': r.record_id, 'source_record_id': r.source_record_id, 'reason': 'duplicate_record_id'}); continue
        k = content_key(r)
        if k in seen_content:
            rejected.append({'record_id': r.record_id, 'source_record_id': r.source_record_id, 'reason': 'duplicate_content', 'duplicate_of': seen_content[k]}); continue
        seen_ids.add(r.record_id); seen_content[k] = r.record_id; ok.append(r)
    return ok, rejected


def report(records: list[RepairRecord], rejected: list[dict], skipped: dict[str, list[dict]]) -> dict:
    return {
        'records_valid': len(records),
        'by_source': dict(Counter(r.source_name.split(' via ')[0].split(' / ')[0] for r in records)),
        'by_category': dict(Counter(r.appliance_category for r in records)),
        'by_verification_status': dict(Counter(r.verification_status for r in records)),
        'records_rejected': len(rejected), 'rejected_reasons': dict(Counter(x['reason'] for x in rejected)),
        'skipped_by_source': {k: {'count': len(v), 'reasons': dict(Counter(x['reason'].split(':')[0] + (':' + x['reason'].split(':')[1] if ':' in x['reason'] else '') for x in v))} for k, v in skipped.items()},
    }


def to_jsonl(records: list[RepairRecord]) -> str:
    return '\n'.join(json.dumps(r.model_dump(mode='json'), ensure_ascii=False) for r in records) + '\n'
