# FixSaathi backend (FastAPI)

See the root README for setup. Summary:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env    # set SECRET_KEY and DATABASE_URL (Gemini optional)
alembic upgrade head
uvicorn app.main:app --reload --port 8000   # /docs, /health, /ready
pytest -q                                   # needs DATABASE_URL pointing at an empty test DB
```

Layout: `app/api/v1` routers · `app/services` business logic, access policy and **safety** · `app/agents` prompts and output schemas · `app/integrations/gemini` the single Gemini client and Live relay connector · `app/integrations/storage` local file storage · `app/db` models and session · `alembic/` migrations · `tests/` (52 tests, Gemini mocked) · `scripts/` user and role admin, knowledge indexing.

Docs: ../docs/API.md, ../docs/LIVE_PROTOCOL.md, ../docs/ALLOYDB.md, ../docs/DEPLOY_CLOUD_RUN.md (also included in the backend zip under docs/).
