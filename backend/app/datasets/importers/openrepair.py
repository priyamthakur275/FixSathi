"""Open Repair Alliance export (ORDS v0.3, CC BY-SA 4.0). Community repair-event records: free-text problem + outcome.
The CSV must be downloaded manually (the site uses a request form). Only rows that clearly match a FixSaathi appliance are kept."""
import csv, re
from datetime import date
from pathlib import Path
from .. import normalize as N

SOURCE = 'Open Repair Alliance (ORDS)'
LICENSE = 'CC BY-SA 4.0. https://openrepair.org/open-data/downloads/'
STATUS = {'fixed': 'fixed', '1': 'fixed', 'repairable': 'repairable', '2': 'repairable', 'end of life': 'end_of_life', '3': 'end_of_life', 'unknown': 'unknown', '0': 'unknown'}
LARGE = [('washing_machine', r'washing machine|washer(?! ?dryer)'), ('refrigerator', r'fridge|refrigerator|freezer')]


def classify(product_category: str | None, problem: str | None, partner_cat: str | None) -> str | None:
    pc = (product_category or '').strip().lower()
    if pc == 'aircon/dehumidifier':
        return 'aircon_dehumidifier'
    if pc == 'fan':
        return 'fan_other'
    if pc == 'large home electrical':  # mixed bucket: keep only rows that name the appliance
        text = f'{partner_cat or ""} {problem or ""}'.lower()
        for cat, rx in LARGE:
            if re.search(rx, text):
                return cat
    return None


def load(csv_path: Path) -> tuple[list[dict], list[dict]]:
    out, skipped = [], []
    with csv_path.open(newline='', encoding='utf-8', errors='replace') as f:
        for r in csv.DictReader(f):
            rid = N.clean(r.get('id')); prov = N.clean(r.get('data_provider')) or 'unknown'
            cat = classify(r.get('product_category'), r.get('problem'), r.get('partner_product_category'))
            if not cat:
                skipped.append({'source_record_id': rid, 'reason': f"out_of_scope:{N.clean(r.get('product_category'))}"}); continue
            problem = N.clean(r.get('problem'))
            if not problem or len(problem) < 4:
                skipped.append({'source_record_id': rid, 'reason': 'no_problem_text'}); continue
            year = N.clean(r.get('year_of_manufacture'))
            out.append({
                'record_id': f'openrepair:{prov}:{rid}'.replace(' ', '_')[:120], 'appliance_category': cat, 'appliance_brand': N.brand(r.get('brand')),
                'model_year': int(float(year)) if year and re.fullmatch(r'\d{4}(\.0)?', year) and 1950 <= int(float(year)) <= 2100 else None,
                'reported_symptoms': N.symptoms(problem) or [problem[:200]], 'observed_conditions': [problem[:500]],
                'repair_outcome': STATUS.get((N.clean(r.get('repair_status')) or 'unknown').lower(), 'unknown'),
                'fixsaathi_safety_policy': N.safety_policy(cat, [])[1],
                'source_name': f'{SOURCE} / {prov}', 'source_url': 'https://openrepair.org/open-data/downloads/', 'source_license': LICENSE,
                'source_record_id': f'{prov}:{rid}', 'verification_status': 'unverified', 'last_updated': date.today(),
                'provenance': {'dataset': 'ORDS', 'country': N.clean(r.get('country')), 'event_date': N.clean(r.get('event_date')),
                               'product_category': N.clean(r.get('product_category')), 'partner_product_category': N.clean(r.get('partner_product_category')),
                               'repair_barrier_if_end_of_life': N.clean(r.get('repair_barrier_if_end_of_life'))},
            })
    return out, skipped
