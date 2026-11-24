# FixSaathi: AI Repair Copilot

FixSaathi is a repair copilot for appliance field technicians. The technician picks the appliance, describes the fault by text or voice, and adds a photo. FixSaathi gives a ranked diagnosis grounded in repair records, then guided steps. The **server** locks every step that needs the power off until the technician records both safety statements. When the job is done, the service report is written automatically.

- **Live app:** https://fixsaathi-copilot-v9cb.onrender.com
- **API:** https://fixsaathi-copilot-api-v9cb.onrender.com (docs: `/docs`, health: `/health`)
- **Stack:** React 19 + TypeScript (Vite, Tailwind 4) · FastAPI + SQLAlchemy 2 + Alembic · PostgreSQL · Google Gemini through the official `google-genai` SDK, called from the server only

```
frontend/    React app (Render static site in production), 29 tests
backend/     FastAPI app, Gemini integration, safety gate, demo scenarios, dataset pipeline, 205 tests
data/        377 repair records: ApplianceDB (ODbL), manufacturer documentation (summarised, with links), FixSaathi guidance
docs/        FEATURE_AUDIT, TECHNICAL_REPORT, DEMO_SCRIPT, SUBMISSION_CHECKLIST, architecture, API, safety, datasets
render.yaml  Render Blueprint: static site + API + PostgreSQL
Dockerfile   Alternative single image: builds the site, then serves the site and API from FastAPI
```

Start with **docs/FEATURE_AUDIT.md** for what is verified and what is not.

## How the AI works

FixSaathi does **not** use a trained or fine-tuned model. It calls Google Gemini through its API and grounds every answer in a curated repair knowledge base of **377 records** (retrieval-augmented generation):

1. The appliance comes from the session, or is detected from the technician's words (`fridge not cooling` is a refrigerator, not an AC).
2. Brand, model and error codes are extracted (`CH 38`, `CH38` and the alias `F4` all match LG's record).
3. Records are ranked **within that appliance only**: exact error-code matches first, then PostgreSQL full-text search and Gemini embeddings (`gemini-embedding-001`), whose scores are added together, so a record found both ways ranks highest. Same-brand and manufacturer-documented sources are preferred. Common Hinglish words (pankha, thanda, awaaz...) are mapped to the English terms the records use.
4. Gemini gets only the top matching records (never the whole knowledge base) as tagged evidence. The server deletes any citation that wasn't retrieved, and marks a fault as unverified when no record supports it.
5. The safety gate is server code: power steps stay locked until both statements are recorded, and microwave steps that would open the cabinet are replaced with a hand-over to authorised service.

| Appliance | Records |
|---|---|
| Washing machine | 253 |
| Refrigerator | 41 |
| Split AC | 28 |
| Ceiling fan | 19 |
| Water purifier | 18 |
| Microwave oven | 16 |
| MCB / electrical, rooftop solar | 1 each |

See `docs/DATASET_QUALITY_REPORT.md`, `docs/SOURCE_ATTRIBUTION.md` and `docs/RAG_PIPELINE.md`. To rebuild the data: `python scripts/process_datasets.py`, then `python scripts/dataset_quality_report.py`.

## Deploy on Render (Blueprint)

`render.yaml` defines three free resources in Singapore (Render added the `-v9cb` suffix to each name when the Blueprint was created):

| Resource | Type | What it does |
|---|---|---|
| `fixsaathi-copilot-v9cb` | Static site (`frontend/`, `npm ci && npm run build`, publishes `dist`) | The React app. All paths rewrite to `index.html` for client-side routing. `VITE_API_BASE_URL` points at the API. |
| `fixsaathi-copilot-api-v9cb` | Python web service | `pip install -r backend/requirements.txt`, then `backend/scripts/render_start.sh`: migrations (upgrade only), idempotent load of the 377 records, background embedding index, then uvicorn on `0.0.0.0:$PORT`. Health check: `/ready`. |
| `fixsaathi-copilot-db-v9cb` | PostgreSQL 16 | `DATABASE_URL` is wired from the database (internal URL). No public access. Photos are stored here too (`STORAGE_PROVIDER=database`), because the free plan has no persistent disk. |

Secrets are never in the repo: Render generates `SECRET_KEY`, and `GEMINI_API_KEY` is entered on the API service's **Environment** page (`sync: false`). Every push to `main` redeploys both services. To get a **manager** account (dashboard), register in the app, then set `BOOTSTRAP_MANAGER_EMAIL` to that email on the API service's Environment page; the next start promotes it (nothing happens if the email is not registered).

**Free-plan limits:** the API sleeps after 15 minutes idle (first request then takes up to a minute), a workspace gets 750 instance-hours a month across all free services, and a free database expires 30 days after creation unless upgraded. `.github/workflows/keep-awake.yml` wakes the API on demand before a demo.

`/health` returns 200 only when the database answers and 503 otherwise; it also reports whether AI is configured. `/ready` is the lighter check Render uses.

### Verified in production

Tested against the live services with real Gemini calls and safe, synthetic inputs:

| Feature | Result |
|---|---|
| Registration, login, token refresh, data kept after re-login | Works |
| Chat and diagnosis grounded in records, with citations | Works (English, Hinglish, Hindi input) |
| Photo upload, component located on a photo, chat reading text in a photo | Works |
| Repair steps, with power steps locked and hidden until both safety statements are recorded | Works (chat also withholds power-sensitive steps) |
| Service report | Works |
| Voice | Browser voice mode: the server side (short spoken replies) is tested. Speech recognition and read-aloud run in the browser and were not tested automatically. |
| Gemini Live voice | Not available: the current API key has no Live access (returns `MODEL_NOT_CONFIGURED`) |
| AI step illustrations | Not available: every image model needs billing on the key's project (`BILLING_REQUIRED`) |

## Run locally

You need **PostgreSQL 16**, **Python 3.12** and **Node 22.19 or newer** (`frontend/.nvmrc`; older Node 22 releases fail the frontend tests), or just Docker. A Gemini key is optional: without it, AI features answer `AI_NOT_CONFIGURED` and the labelled demo scenarios still work.

### Option A: Docker (one command)

```bash
python3 backend/scripts/setup_env.py --compose   # writes backend/.env (new SECRET_KEY) and .env (ports, database password)
# open backend/.env and paste your key after GEMINI_API_KEY= (optional)
docker compose up --build                       # site: http://localhost:5173   API: http://localhost:8000/docs
```

The compose project is named `fixsaathi-submission`, so it never reuses the containers or volumes of another FixSaathi copy. If ports 5432, 8000 or 5173 are taken, change `DB_HOST_PORT`, `BACKEND_HOST_PORT` and `FRONTEND_HOST_PORT` in `.env`. After the first start, `python scripts/index_knowledge.py` (in `backend/`, needs a Gemini key) builds the embedding index for hybrid retrieval; it skips unchanged records and waits out free-tier rate limits.

### Option B: manual (macOS / Linux)

```bash
# 1. Database (macOS: brew install postgresql@16 && brew services start postgresql@16)
createdb fixsaathi

# 2. Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup_env.py --database-url "postgresql+psycopg://$USER@localhost:5432/fixsaathi"
#    then paste your Gemini key into backend/.env (optional)
python scripts/check_gemini.py --call             # optional: checks the key and models; never prints the key
alembic upgrade head && python scripts/ingest_knowledge.py
uvicorn app.main:app --reload --port 8000         # API docs: http://localhost:8000/docs

# 3. Frontend (new terminal)
cd frontend && cp .env.example .env && npm ci && npm run dev    # http://localhost:5173
```

### Option B on Windows (PowerShell)

```powershell
# Install PostgreSQL 16 from postgresql.org, then create the database "fixsaathi" (pgAdmin, or: createdb -U postgres fixsaathi)
cd backend
py -3.12 -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\setup_env.py --database-url "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/fixsaathi"
alembic upgrade head; python scripts\ingest_knowledge.py
uvicorn app.main:app --reload --port 8000
# new terminal
cd frontend; copy .env.example .env; npm ci; npm run dev
```

### Option C: one process, like production

```bash
cd frontend && npm ci && VITE_API_BASE_URL="" npm run build && cd ../backend
FRONTEND_DIST=../frontend/dist uvicorn app.main:app --port 8000   # site and API both on http://localhost:8000
```

To make yourself a manager (for the dashboard): `python scripts/create_user.py --email you@example.com --role manager --org "Your Company"`


### What you can attach

Use the **+** button in the chat: photos (JPG, PNG, WebP, up to 8 MB), PDFs, Word (.docx) and text files (.txt, .csv, .md, up to 15 MB), or **Take a photo** with the device camera. You can attach up to 6 files per message, or drag and drop them, or paste an image. The server checks every file's real contents, removes location metadata from photos, and refuses anything else. The camera needs https (or localhost).

### Troubleshooting

| Symptom | Fix |
|---|---|
| `FixSaathi cannot start: check SECRET_KEY ...` | Run `python scripts/setup_env.py` in `backend/`. |
| `connection refused` / `password authentication failed` | PostgreSQL isn't running, or `DATABASE_URL` in `backend/.env` has the wrong user or password. |
| Chat says *AI is not available* | No `GEMINI_API_KEY` in `backend/.env`. Paste it, restart the backend. |
| *Free-tier quota reached* | Wait about a minute; the fallback models are tried automatically. |
| Step picture says `BILLING_REQUIRED` | The key's tier has no image-generation model. Enable billing on its Google project. |
| Live voice says `LIVE_NOT_AVAILABLE` | The key cannot open Gemini Live sessions (`python scripts/check_gemini.py --call --live`). The voice page falls back to browser voice mode. |
| Frontend tests fail in `undici` (`reading 'bind'`) | Node is older than 22.19: `nvm install 22 && nvm use` in `frontend/`. |
| Voice button does nothing | Use Chrome or Edge and allow the microphone. Voice uses browser speech plus Gemini. |
| Camera says permission denied | Click the camera icon in the address bar, allow the camera, then **Try camera again**. On http (not https) browsers block the camera: use **Upload from gallery**. |
| "Waking up the server" on the live site | The free Render plan sleeps when idle; the first load takes up to a minute. You stay signed in. |

## AI behaviour, and what happens without AI

- **Errors:** every Gemini failure is classified (`INVALID_API_KEY`, `PERMISSION_DENIED`, `MODEL_NOT_FOUND`, `BILLING_REQUIRED`, `QUOTA_EXCEEDED`, `AI_TIMEOUT`, `NETWORK_ERROR`, `AI_BLOCKED`, ...). The chat shows the reason and a fix. The technician's message is saved either way.
- **Retries:** free-tier rate limits are retried after the delay Google asks for, then the next fallback model is tried. Every switch is logged. Bad keys and unknown models are never retried.
- **Cost and speed:** only the top matching records are sent (about 1,400 input tokens per chat reply); chat replies are capped at 2,048 output tokens; an earlier photo is re-sent only for the next two follow-ups or when the message refers to it; the query is embedded only when an index exists; calls time out after 45 s with one retry. Token use per call is recorded in the `ai_usage` table.
- **Without a key:** AI endpoints return `AI_NOT_CONFIGURED`. The UI says so and offers the **labelled demo scenarios** (`/demo`). Demo sessions use scripted sample content written by the team, and every screen labels them "Demo scenario: scripted sample, not live AI". The safety lock, logging and reports are the same server code as live sessions.

## Voice

The voice page first tries the **Gemini Live** relay (only when `GEMINI_LIVE_MODEL` is set; it is not set in production because the current key has no Live access) (WebSocket, 16 kHz audio up, 24 kHz down). If the server's key has no Live model, it switches to **browser voice mode**: Chrome or Edge speech recognition turns speech into text, the normal Gemini chat answers through the server, and the browser reads the answer aloud. This is **not** Gemini Live streaming. Microphone denial and unsupported browsers show a clear message.

## Safety model (enforced in backend code)

- The two safety checkboxes are **statements entered by the technician**: "power switched off at the MCB" and "checked with my own tester". FixSaathi cannot measure voltage or verify isolation, and the UI and reports say so.
- `SafetyService.guard` is the only path that permits a power-sensitive action. REST step completion, step pictures and the Live `give_step` tool all go through it. Both statements are required, per session and per technician, and they expire after `SAFETY_CONFIRMATION_TTL_MINUTES` (default 60).
- Locked steps are sent to the client **without their instructions**. The server decides which steps are power-sensitive: it takes the model's flag OR keyword detection (one shared rule set, `app/core/power_rules.py`, including Hinglish verbs).
- **Chat replies** (typed and browser voice) are screened by `safety.screen_text` before they are stored or shown: while the statements are not recorded, power-sensitive instructions are replaced by a note; numbered steps get the broad step rule. Safety reminders and prohibitions stay.
- **Gemini Live**: while the gate is locked, each spoken turn is held, its transcript screened, and only then played; withheld turns are never played or saved, and audio that cannot be screened is not played (fail closed).
- **Microwaves**: internal work (cabinet, magnetron, HV capacitor) is always replaced by a hand-over to authorised service, in steps, chat and Live, even after confirmation.
- The AI has no tool that can record a statement. Every blocked attempt is logged in `safety_events`.

## Tests

```bash
cd backend && createdb fixsaathi_test
DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/fixsaathi_test SECRET_KEY=test-secret-key-0123456789-abcdefghijk pytest -q   # 205 tests
cd ../frontend && npm test && npm run build && npm run lint                                                                       # 29 tests
```

The backend tests run the real Alembic migrations on PostgreSQL and **wipe that test database**, so the test setup refuses to run unless the database is local and its name ends in `_test`. Gemini is replaced by a deterministic fake, and the test setup blanks any real key in `backend/.env`, so no paid calls are made.

Data licence: ApplianceDB-derived records are ODbL-1.0 (attribution and share-alike). See docs/DATASET_SOURCES.md.
