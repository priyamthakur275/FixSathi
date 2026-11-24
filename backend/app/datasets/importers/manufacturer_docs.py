"""Records summarised by the FixSaathi team from public manufacturer troubleshooting pages and user manuals
(data/raw/manufacturer_docs/). Each record keeps its source title, URL, source type and evidence level.
Only what the source states is kept; empty fields stay empty."""
import json
from datetime import date
from pathlib import Path
from .. import normalize as N

# Sources on the manufacturer's own site count as manufacturer-documented. Manuals hosted elsewhere (retailer CDN, manual
# archives) are the manufacturer's text, but we could not confirm the copy, so they stay 'unverified'.
VERIFIED_EVIDENCE = {'manufacturer_documented', 'manufacturer_general_guidance'}
LICENSE = 'Facts paraphrased from publicly available manufacturer documentation, with attribution. No source text redistributed.'


def load(folder: Path) -> tuple[list[dict], list[dict]]:
    meta = json.loads((folder / 'sources.json').read_text())
    sources, accessed = meta['sources'], meta['accessed']
    out, skipped = [], []
    for e in json.loads((folder / 'records.json').read_text())['entries']:
        src = sources.get(e['src'])
        if not src:
            skipped.append({'source_record_id': e.get('id'), 'reason': f"unknown_source:{e.get('src')}"}); continue
        also = [sources[s] for s in e.get('also_src', []) if s in sources]
        checks = e.get('checks', [])
        needs, pol = N.safety_policy(e['cat'], checks + [e.get('action') or ''])
        code = N.error_code(e.get('code'))
        aliases = [N.error_code(a) for a in e.get('aliases', [])]
        out.append({
            'record_id': f"mfr:{e['id']}", 'appliance_category': e['cat'], 'appliance_brand': N.brand(e.get('brand')),
            'appliance_model': e.get('model'), 'market': e.get('market'), 'error_code': code,
            'error_code_original': ' / '.join([code, *aliases]) if code else None,
            'reported_symptoms': e.get('symptoms', []), 'possible_faults': e.get('faults', []), 'diagnostic_procedure': checks,
            'recommended_repair': e.get('action'), 'safety_requirements': e.get('safety', []), 'fixsaathi_safety_policy': pol,
            'requires_power_off': needs, 'severity': e.get('severity'),
            'source_name': f"{src['publisher']}: {src['title']}", 'source_url': src['url'], 'source_license': LICENSE,
            'source_record_id': e['id'], 'verification_status': 'verified_source' if src['evidence_level'] in VERIFIED_EVIDENCE else 'unverified',
            'last_updated': date.fromisoformat(accessed),
            'provenance': {'summarised_by': 'FixSaathi team', 'file': 'data/raw/manufacturer_docs/records.json', 'source_title': src['title'],
                           'publisher': src['publisher'], 'source_type': src['source_type'], 'evidence_level': src['evidence_level'],
                           'accessed': accessed, 'additional_sources': [a['url'] for a in also], 'escalation_conditions': e.get('escalate', []),
                           'code_aliases': aliases,
                           'note': 'Paraphrased from the source. Possible causes are as the source lists them, not confirmed diagnoses.'},
        })
    return out, skipped
