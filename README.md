<div align="center">

# FixSaathi

**An AI repair copilot for appliance technicians in India: grounded diagnosis, a safety lock enforced by the server, and voice in English, Hindi and Kannada.**

[**Live app**](https://fixsaathi-vu9s.onrender.com) · [API docs](https://fixsaathi-vu9s.onrender.com/docs) · [Evaluation](docs/EVALUATION.md) · [Architecture](docs/ARCHITECTURE.md)

![React](https://img.shields.io/badge/React_19-TypeScript-3178C6?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-PostgreSQL-009688?logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-RAG_+_Live_voice-4285F4?logo=google&logoColor=white)
[![CI](https://github.com/priyamthakur275/FixSathi/actions/workflows/ci.yml/badge.svg)](https://github.com/priyamthakur275/FixSathi/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/tests-436-2ea44f)
![Deploy](https://img.shields.io/badge/deployed_on-Render-46E3B7?logo=render&logoColor=white)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
<a href="docs/demo/fixsaathi-demo.mp4"><img src="docs/demo/demo.gif" width="860" alt="FixSaathi walkthrough: the server withholds power-sensitive steps until the technician records two safety statements, then releases them and writes the report"></a>
<br><sub><a href="docs/demo/fixsaathi-demo.mp4"><b>Watch the 53-second walkthrough (MP4)</b></a></sub>
</p>

<table>
<tr>
<td width="68%"><img src="docs/screenshots/safety-lock.png" alt="Repair workspace: the safety panel keeps power-sensitive steps locked until the technician records two statements"></td>
<td width="32%"><img src="docs/screenshots/mobile-home.png" alt="FixSaathi home screen on a phone"></td>
</tr>
<tr>
<td colspan="2"><img src="docs/screenshots/chat.png" alt="Chat: a power-sensitive step is withheld until isolation is recorded"></td>
</tr>
</table>

<sub>Walkthrough and screenshots are from a local run. The chat and workspace show one of the app's built-in demo scenarios, which are labelled on screen as scripted sample content; the safety lock, the withheld step and the retrieved records are the real server code.</sub>

## The problem

Most AC, fridge and washing-machine repairs in India are done by independent technicians who work alone, with no service manual and no senior to call. They diagnose by trial and error, which wastes parts and time, and they sometimes work on appliances that are still live.

FixSaathi gives that technician a copilot on their phone: describe the fault by text, voice or photo, get a ranked diagnosis grounded in real repair records, then follow guided steps that the server will not reveal until the power is isolated. The service report writes itself.

## What it does

| | |
|---|---|
| **Grounded diagnosis** | Every answer is built from the repair records retrieved for that question (377 records: manufacturer documentation, the ApplianceDB error-code dataset and FixSaathi's own guidance). The server deletes any citation that was not retrieved, and marks a fault as unverified when no record supports it. |
| **Server-side safety lock** | Steps that need the power off are sent to the phone *without their instructions* until the technician records two statements: "power switched off at the MCB" and "checked with my own tester". AI chat and voice replies are screened sentence by sentence before anyone reads or hears them. Microwave internals are always handed over to authorised service. |
| **Voice, three languages** | Speak a fault, hear the answer. Gemini Live for real-time voice, with Gemini text-to-speech and the device voice as fallbacks. The interface works in English, Hindi and Kannada, and the search understands Hinglish ("pankha dheere chal raha hai") and Devanagari Hindi. |
| **Photos and documents** | Attach appliance photos, a camera capture, PDFs or Word files. The server checks every file's real type and strips location data from photos. |
| **Fault finder** | Type an error code or a symptom ("LG CH38", "fan hums but does not spin") and get the matching records at once, straight from the knowledge base: no AI call, no quota, works without a Gemini key. Checks that need the power isolated are sent locked, as in a session. |
| **Send to customer** | A finished report becomes a short plain-text summary of the visit (problem, work done, result, isolation recorded) to send on WhatsApp or copy. |
| **Answer feedback** | Thumbs up or down on each AI answer, with a note on what was wrong. When a job is closed the technician rates the guidance and says whether the AI's likely cause was right. The manager dashboard shows the share of answers technicians found helpful. |
| **Answer-quality check** | 30 technician questions asked to the deployed app and graded by fixed rules: right points covered, records cited, no invented error codes, no live-work step readable while the power is locked. See [Results](#results). |
| **Reports and dashboard** | A service report and PDF built only from what was recorded in the session; a manager view with sessions, first-time-fix rate, escalations and ratings. |

## Results

Measured offline by [`backend/scripts/evaluate.py`](backend/scripts/evaluate.py) on hand-labelled fault descriptions written in the way technicians type them. Held-out v2 was written before the current ranking was run on it and was not used to tune anything. Details, method, every miss and which sets were used to change code: [docs/EVALUATION.md](docs/EVALUATION.md).

| Held-out sets | Result |
|---|---|
| Correct repair record ranked first (held-out v2, 36 queries; English, Hinglish, Hindi) | **94.4%**, up from 88.9% with the previous ranking (MRR 0.914 → 0.958) |
| Correct repair record in the top 3 (held-out v2 / held-out, 36 + 30 queries) | **94.4% / 100%** |
| Appliance detected correctly from free text (held-out / v2) | **96.7% / 97.2%** |
| Unsafe instructions withheld by the safety filter | **11 / 12** when first measured; 12 / 12 after the fix it led to |
| Safe text left readable | **11 / 12** |

These numbers cover retrieval (keyword and error-code channels, reproducible without an API key) and the safety rule.

**Answers on the live app** ([`eval_answers.py`](backend/scripts/eval_answers.py), 30 questions in English, Hinglish and Hindi, every session left un-isolated):

| Check | Result |
|---|---|
| Answers passing every check | **28 / 30** (27 / 30 on the first run) |
| Live-work steps readable while the power is locked | **0 / 30** (1 / 30 on the first run: a Hindi reply, which led to Devanagari safety rules) |
| Meanings invented for unknown error codes | **0** |
| Cites a repair record where one exists | 22 / 24 |

The queries were written by the team, not collected from technicians. Method, both runs and every miss: [docs/EVALUATION.md](docs/EVALUATION.md#answer-quality-gemini-answers-live-app).

## Field feedback

50 technicians in 39 cities (6 months to 20 years in the trade, median 7) tried FixSaathi on a fault of their own and answered six questions on WhatsApp. Replies, one row each: [`data/field_feedback/`](data/field_feedback/).

| Question | Answer |
|---|---|
| Was the likely cause right? | **45 yes**, 5 partly, 0 no |
| How useful, out of 5 | **4.0** on average: 5.0 from technicians under 3 years, 4.0 from 3-9 years, 3.6 from 10+ years |
| Will you use it? | 24 yes, 11 will give it to their helpers or juniors, 10 sometimes, 3 if more data is added, 2 no |

> "Wo MCB band karke tester wala lock best hai, mujhe pehle 2 baar jhatka lag chuka hai." (The switch-off-and-test lock is the best part; I have had two shocks before.) Rohit Kumar, helper, Noida

> "Mere liye basic hai par mere 4 naye ladke hain, unke liye safety lock bahut kaam ka hai." (Basic for me, but very useful for my four new technicians.) Vikramjit Singh, AC contractor, Ludhiana

> "Fan ka capacitor badalne ke liye app kaun kholega?" (Who opens an app to change a fan capacitor?) Electrician, 18 years, Lucknow: 2 / 5

What they asked for, and what changed:

| Feedback | Replies | Change |
|---|---|---|
| The first load takes 30-45 seconds | 18 | The keep-awake ping was running only a few times a day. It now runs continuously. |
| Asked to switch off the MCB when it was not needed, or too often | 5 | Isolation is now asked for only when a step opens the appliance or touches electrical parts. A recorded isolation still expires after a while, on purpose. |
| Too many English words | 4 | Hindi replies use simple spoken Hindi, with part names as technicians say them. |
| Microwave high-voltage warning should stand out | 2 | Shown as a red alert in the chat. |
| Brand error codes, sensor values, pressure charts | 7 | Not yet: needs sourced data, not model guesses. Next on the list. |
| Live testing (clamp meter, PCB voltage) | 4 | Not added, by design (see Honest limits). |
| Offline use, part photos | 4 | Not yet. |

Experienced technicians found it too basic; juniors and helpers rated it highest. That points to the first real users: trainees and the teams of contractors and shop owners.

## How it works

```mermaid
flowchart TD
    T["Technician: text, voice or photo"] --> W["React web app"]
    W -->|HTTPS + JWT| A["FastAPI"]
    A --> R["Retrieval: error codes, full-text, embeddings"]
    R <--> DB[("PostgreSQL: 377 repair records, sessions, safety log")]
    R -->|top records only| G["Google Gemini"]
    G --> S{"Server safety screen"}
    S -->|isolation not recorded| L["Power steps withheld"]
    S -->|both statements recorded| O["Full answer with citations"]
    L --> W
    O --> W
```

1. **Retrieve.** The appliance comes from the session or is detected from the technician's words. Brand and error codes are extracted ("CH 38", "CH38" and the alias "F4" all reach LG's record). Records are ranked within that appliance: exact error-code matches first, then a field-weighted keyword score (a word in the record's reported symptom counts more than one in its procedure, and rare words count more than common ones) and Gemini embeddings, fused so a record found both ways ranks highest.
2. **Generate.** Gemini gets only the top records as tagged evidence, never the whole knowledge base (about 1,400 input tokens per reply).
3. **Screen.** `app/core/power_rules.py` is the single definition of "power-sensitive", shared by repair steps, chat, Live voice and the dataset importer, including Hindi verbs (*khol*, *nikal*, *badal*). `SafetyService.guard` is the only code path that can permit a power-sensitive action, and the AI has no tool that can record a safety statement. Every blocked attempt is logged.
4. **Fail safely.** Every Gemini failure is classified (bad key, quota, timeout, blocked...) and shown with a fix; the technician's message is saved either way. Rate limits fall back to the next model. Live audio that cannot be screened is not played.

## Engineering

- **Backend:** FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, `google-genai`. JWT access and refresh tokens, organisation-scoped access for managers, rate-limited sign-in, a per-account AI quota so one public sign-up cannot use up the Gemini key, uploads checked by content and re-encoded without location data.
- **Frontend:** React 19, TypeScript, Vite, Tailwind 4, Framer Motion, Recharts. Mobile-first, works on a phone browser. Archivo at two widths (expanded for headings and figures); red and green are kept for power state only, and the safety panel draws the breaker the technician has switched off. A command palette (Ctrl K / Cmd K) reaches every page and past repair, and the team dashboard refreshes itself every minute. Checked with axe-core: no WCAG 2 AA violations on the main screens in either theme (the wordmark logo excepted).
- **Tests:** 436 automated tests: 367 backend tests run the real Alembic migrations on PostgreSQL with Gemini replaced by a deterministic fake, and 69 frontend tests (Vitest, Testing Library). Plus the offline evaluation and the answer-quality check above.
- **Data pipeline:** `scripts/process_datasets.py` normalises the sources into one schema with licence and verification status per record; `scripts/dataset_quality_report.py` reports coverage. See [docs/DATASET_ARCHITECTURE.md](docs/DATASET_ARCHITECTURE.md).
- **Deployment:** one Docker service on Render serves the website and the API from the same address, plus PostgreSQL ([`render.yaml`](render.yaml)); no URL is written into the config, so it deploys to any account. Secrets live only in Render's environment, and CI runs every test and the evaluation on each push.

```
frontend/   React app
backend/    FastAPI app: api/ routes · services/ (retrieval, AI, safety, reports) · integrations/gemini · tests/ · scripts/
data/       377 processed repair records, raw sources, schema, evaluation sets (data/eval)
docs/       architecture, API, safety and security, retrieval, voice, datasets, evaluation
```

## Deploy your own copy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/priyamthakur275/FixSathi)

Sign in to Render, paste a Gemini API key when asked (or leave it empty to try the labelled demo scenarios), and apply. Render creates the database and one web service; the first build takes about ten minutes, and the app is at the service's `onrender.com` address.

## Run it locally

You need PostgreSQL 16, Python 3.12 and Node 22.19+ (or just Docker). A Gemini key is optional: without one, AI features say so clearly and the labelled demo scenarios still work.

```bash
# Docker: one command
python3 backend/scripts/setup_env.py --compose   # writes backend/.env and .env
docker compose up --build                         # app: http://localhost:5173  API: http://localhost:8000/docs
```

```bash
# Manual
createdb fixsaathi
cd backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python scripts/setup_env.py --database-url "postgresql+psycopg://$USER@localhost:5432/fixsaathi"   # then add GEMINI_API_KEY to backend/.env
alembic upgrade head && python scripts/ingest_knowledge.py
uvicorn app.main:app --reload --port 8000

cd ../frontend && cp .env.example .env && npm ci && npm run dev
```

```bash
# Tests and evaluation
cd backend && createdb fixsaathi_test
DATABASE_URL=postgresql+psycopg://$USER@localhost:5432/fixsaathi_test SECRET_KEY=test-secret-key-0123456789-abcdefghijk pytest -q
cd ../frontend && npm test && npm run build && npm run lint
# evaluation: see docs/EVALUATION.md
```

## Honest limits

- **Early field data only.** 50 technicians tried it once on a fault of their choice and were reached through personal contacts. It has not yet been used day to day on paid jobs.
- **The safety statements are the technician's word.** FixSaathi cannot measure voltage or verify isolation, and the app and reports say so.
- **The knowledge base is small** (377 records, two-thirds of them washing-machine error codes). Answers outside it are marked as not grounded.
- **Free hosting.** The API runs on Render's free plan, which sleeps after 15 idle minutes. A GitHub Actions job pings it every 4 minutes to keep it awake; if that job is late, the first request can still take 30-50 seconds.
- **No live-testing mode, by design.** Some checks (running current with a clamp meter, PCB voltages) need the supply on. FixSaathi does not guide work on live circuits; it tells the technician what the reading should be checked against and leaves live work to their training and judgement.

## Team

Built by **Prerana P Jois** and **Priyam Thakur** (Team Tensor Trailblazers, BMS College of Engineering, Bengaluru) for the Google Startup Buildathon India 2026, where the project reached the end of Round 2.

## Data and licence

Application source code is released under the [MIT License](LICENSE). ApplianceDB-derived records are ODbL-1.0 (attribution and share-alike); manufacturer documentation is summarised with links to the source. See [docs/DATASET_SOURCES.md](docs/DATASET_SOURCES.md) and [docs/SOURCE_ATTRIBUTION.md](docs/SOURCE_ATTRIBUTION.md).
