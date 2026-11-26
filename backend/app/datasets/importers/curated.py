"""FixSaathi's own curated guidance (app/knowledge/faults.json), migrated into the unified schema without discarding any entry."""
import json
from datetime import date
from pathlib import Path
from .. import normalize as N


def load(path: Path) -> tuple[list[dict], list[dict]]:
    data = json.loads(path.read_text())
    out = []
    for e in data['entries']:
        needs, pol = N.safety_policy(e['appliance_type'], e['troubleshooting_steps'])
        out.append({
            'record_id': f"fixsaathi:{e['key']}", 'appliance_category': e['appliance_type'], 'reported_symptoms': e['symptoms'],
            'possible_faults': e['possible_causes'], 'diagnostic_procedure': e['troubleshooting_steps'], 'repair_steps': [],
            'safety_requirements': e['safety_requirements'], 'fixsaathi_safety_policy': pol, 'requires_power_off': needs,
            'diagnostic_questions': [], 'source_name': 'FixSaathi curated guidance', 'source_url': None,
            'source_license': 'Project-owned (FixSaathi team)', 'source_record_id': e['key'],
            'verification_status': 'unverified', 'last_updated': date.today(),
            'provenance': {'authored_by': 'FixSaathi team', 'file': 'backend/app/knowledge/faults.json', 'fault_category': e['fault_category'],
                           'escalation_conditions': e['escalation_conditions'], 'note': 'Generic safety-first guidance. Not technician-reviewed.'},
        })
    return out, []
