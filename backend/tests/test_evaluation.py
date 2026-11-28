"""Public /api/v1/evaluation endpoint serves docs/EVALUATION_RESULTS.json verbatim."""
import json
from pathlib import Path

RESULTS_FILE = Path(__file__).resolve().parents[2] / 'docs' / 'EVALUATION_RESULTS.json'


def test_public_evaluation_endpoint_matches_docs_file_verbatim(client):
    r = client.get('/api/v1/evaluation')  # no Authorization header required
    assert r.status_code == 200, r.text
    assert 'max-age=300' in (r.headers.get('cache-control') or '')
    expected = json.loads(RESULTS_FILE.read_text(encoding='utf-8'))
    got = r.json()
    assert got == expected
    assert got['held_out_v2']['retrieval']['appliance_selected']['overall']['hit@1'] == 0.944
    assert got['held_out']['safety_filter']['unsafe_withheld'] == '12/12'
    assert got['held_out']['safety_filter']['safe_shown'] == '11/12'
