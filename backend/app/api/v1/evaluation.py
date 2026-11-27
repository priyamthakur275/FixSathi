"""Public read-only endpoint serving docs/EVALUATION_RESULTS.json."""
import json
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ...core.exceptions import NotFound

router = APIRouter(tags=['evaluation'])


def _results_path() -> Path | None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[4] / 'docs' / 'EVALUATION_RESULTS.json',
        here.parents[3] / 'docs' / 'EVALUATION_RESULTS.json',
        Path('/app/docs/EVALUATION_RESULTS.json'),
    ]
    return next((p for p in candidates if p.is_file()), None)


@router.get('/evaluation')
def evaluation_results():
    """Return the benchmark results verbatim from docs/EVALUATION_RESULTS.json (no auth required)."""
    path = _results_path()
    if not path:
        raise NotFound('Evaluation results file not found.')
    data = json.loads(path.read_text(encoding='utf-8'))
    return JSONResponse(data, headers={'Cache-Control': 'public, max-age=300'})
