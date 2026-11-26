"""ApplianceDB free developer sample (ODbL-1.0). One unified record per (brand, market, appliance_type, code).
Records from different brands, markets or appliance types are never merged, even when codes match."""
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from .. import normalize as N

SOURCE = 'ApplianceDB (free developer sample)'
LICENSE = 'ODbL-1.0 (attribution + share-alike); docs CC BY 4.0. https://github.com/ApplianceDB/ApplianceDB-public'
SCOPE = {'washer', 'refrigerator'}  # initial FixSaathi coverage; ApplianceDB has no AC data
DIFF = {'easy': 'diy', 'moderate': 'intermediate', 'advanced': 'professional', 'professional_only': 'professional'}


def _read(p: Path) -> list[dict]:
    with p.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load(raw_dir: Path, commit: str | None = None, include_all: bool = False) -> tuple[list[dict], list[dict]]:
    """Returns (candidate dicts for RepairRecord, skipped rows with reasons)."""
    codes = _read(raw_dir / 'error_codes.csv')
    procs = defaultdict(list)
    for p in _read(raw_dir / 'repair_procedures.csv'):
        procs[p['code_id']].append(p)
    parts = defaultdict(list)
    for p in _read(raw_dir / 'replacement_parts.csv'):
        parts[p['procedure_id']].append(p)
    out, skipped = [], []
    for r in codes:
        if not include_all and r['appliance_type'] not in SCOPE:
            skipped.append({'source_record_id': r['code_id'], 'reason': f"out_of_scope:{r['appliance_type']}"}); continue
        cat = N.category(r['appliance_type'])
        ps = sorted(procs.get(r['code_id'], []), key=lambda x: int(x['rank'] or 99))
        stp = [N.clean(p['steps']) for p in ps if N.clean(p['steps'])]
        diffs = [DIFF.get(p['diy_difficulty']) for p in ps if p.get('diy_difficulty')]
        mins = [int(float(p['est_labor_minutes'])) for p in ps if N.clean(p.get('est_labor_minutes'))]
        req_parts = [{'name': N.clean(x['name']), 'part_number': N.clean(x['oem_part_number'])} for p in ps for x in parts.get(p['procedure_id'], []) if N.clean(x['name'])]
        needs, pol = N.safety_policy(cat, stp)
        code = N.error_code(r['code'])
        out.append({
            'record_id': f"appliancedb:{r['code_id']}", 'appliance_category': cat, 'appliance_brand': N.brand(r['brand']), 'market': N.clean(r['market']),
            'error_code': code, 'error_code_original': N.clean(r['code']),
            'reported_symptoms': [f'Error code {code} shown on the display'], 'possible_faults': [N.clean(r['meaning'])],
            'suspected_components': [c for c in [N.component(r['component'])] if c],
            'recommended_repair': N.clean(ps[0]['title']) if ps else None, 'repair_steps': stp, 'required_parts': req_parts,
            'fixsaathi_safety_policy': pol, 'requires_power_off': needs, 'severity': N.clean(r['severity']),
            # most cautious difficulty across ranked procedures
            'repair_difficulty': max(diffs, key=['diy', 'intermediate', 'professional'].index) if diffs else None,
            'estimated_repair_duration_minutes': min(mins) if mins else None, 'repair_outcome': None,
            'source_name': SOURCE + (f" via {N.clean(r['source_name'])}" if N.clean(r['source_name']) else ''), 'source_url': N.clean(r['source_url']),
            'source_license': LICENSE, 'source_record_id': r['code_id'],
            'verification_status': 'verified_source' if r['source_type'] == 'manufacturer_listing' else 'unverified',
            'last_updated': date.today(),
            'provenance': {'dataset': 'ApplianceDB-public', 'commit': commit, 'source_type': r['source_type'], 'cause_category': r['cause_category'],
                           'procedure_ids': [p['procedure_id'] for p in ps], 'procedure_source_urls': sorted({p['source_url'] for p in ps if p.get('source_url')})},
        })
    return out, skipped
