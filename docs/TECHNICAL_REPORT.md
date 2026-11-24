# FixSaathi: technical report

Team Tensor Trailblazers (Prerana P Jois, Priyam Thakur). Google Startup Buildathon India 2026. Status as of 20 November 2026.

## 1. Architecture (what runs today)

| Layer | Technology | Purpose |
|---|---|---|
| Web app | React 19, TypeScript, Vite, Tailwind CSS 4, Framer Motion | Technician workspace: chat, photo or camera, voice, repair workspace, reports, manager dashboard. Pages load on demand. |
| API | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic | Login, repair sessions, chat, diagnosis and step agents, the server-side safety gate, retrieval, reports, dashboard, the Live voice WebSocket relay. |
| Auth | JWT access tokens (30 min), rotating hashed refresh tokens, Argon2 passwords, technician/manager/admin roles | Each user sees only their own or their organisation's sessions. |
| AI | Google Gemini via the official `google-genai` SDK, called only from the server | `gemini-3.6-flash` for chat, vision and structured JSON, with fallbacks `gemini-3.5-flash`, `gemini-3.1-flash-lite` and `gemini-2.5-flash`. `gemini-embedding-001` for embeddings. `gemini-3.1-flash-image` (Nano Banana) for step pictures. Live API relay. |
| Knowledge | `repair_records` table: 377 records across 8 appliance categories (253 washing machine, 41 refrigerator, 28 split AC, 19 ceiling fan, 18 water purifier, 16 microwave, 1 MCB, 1 solar), with a PostgreSQL full-text (GIN) index and brand, model and error-code fields | Retrieval within the detected appliance, with sources. The server removes any record ID the model invents. Each answer gets a coverage label: grounded, partial or none. **No model is trained or fine-tuned**: Gemini is used through its API with this retrieved evidence. |
| Database | PostgreSQL on Neon (free tier) | Users, sessions, messages, safety events, steps, reports, repair records, and **photos** (`stored_files`, with `STORAGE_PROVIDER=database`). |
| Demo mode | `app/demo/` with 2 scripted scenarios | Lets the product be shown without AI. The content is labelled; the safety gate, logging and reports are real. |
| Hosting | Render, as one Docker service in the Singapore region | One service serves both the website and the API over HTTPS. The Gemini key stays on the server. |

**Planned, not built:** Google Cloud Run, AlloyDB vector search, Cloud Storage.

## 2. Feature audit

See `FEATURE_AUDIT.md` for the current, complete list. The table below is a summary.

Evidence levels:
- **A:** automated tests (real PostgreSQL, fake Gemini).
- **B:** checked with real Gemini on the team's laptop on 20 Nov 2026.
- **C:** code only, not checked against real Gemini.

| Feature | Status | Evidence |
|---|---|---|
| Register, login, refresh, roles, org scoping | Implemented and tested | A |
| Repair session create, list and close | Implemented and tested | A |
| Appliance selection (6 categories) | Implemented and tested | A (browser) |
| Chat with message history | Implemented and tested | A, B |
| Photo upload and camera capture | Implemented and tested | A; real Gemini photo answer, B |
| Gemini vision reply in Hinglish | Verified with real Gemini | B (burnt fan photo, 15:37 IST) |
| Fault diagnosis (structured, ranked, confidence marked as estimate) | Implemented, not checked with real Gemini | A, C |
| Component identification with a box on the photo | Implemented, not checked with real Gemini | A, C |
| Step-by-step guidance | Implemented, not checked with real Gemini | A, C |
| **Safety gate**: power-sensitive steps need both `power_off_confirmed` and `tester_checked`, enforced on the server for REST, AI tools and voice; 60-min expiry; blocked attempts logged; the model cannot record the statements | Implemented and tested | A |
| Service report | Implemented and tested | A |
| Manager dashboard | Implemented and tested | A |
| RAG retrieval (full-text) with citation checks | Implemented and tested | A |
| Embedding re-ranking | Partially implemented: code exists, no index built in deployment, so the deployment uses full-text only | C |
| Nano Banana step pictures | Implemented, not checked with real Gemini (model is visible to the key) | A, C |
| Gemini Live voice and camera streaming | Partially implemented: relay built and tested with a fake, **but the key has no Live model** | A |
| Browser voice fallback (Chrome speech to Gemini text to Chrome speech) | Implemented; verified manually | B (transcription and reply seen) |
| Model fallback on free-tier rate limits | Implemented and tested | A |
| Specific AI error messages with a fix hint | Implemented and tested | A |
| Labelled demo mode (`/demo`) | Implemented and tested with no AI key | A (browser) |
| Photo persistence in PostgreSQL | Implemented and tested, including a real server restart | A |
| `/health` checks the database, returns 503 when it's down, accepts HEAD | Implemented and tested | A |
| Field accuracy measurement | Not done. No accuracy numbers are claimed. | n/a |

## 3. Improvements made

**Latest round:**
- **Photo persistence:** photos are now stored in PostgreSQL, so they survive restarts. Missing files return a clear 404.
- **Demo mode:** a labelled demo mode, offered from the AI-unavailable notice.
- **Health check:** `/health` now checks the database, returns 503 when it fails and accepts HEAD.
- **Bug fix:** photos now reload when a saved session is reopened.
- **Voice copy:** it no longer claims Gemini Live before Live is actually connected.
- **Repo cleanup:** removed an outdated handoff file.

**Earlier rounds:**

1. **Root cause of "needs paid tier":** every free-tier rate limit was being reported as "billing required" and never retried. Now only a real `limit: 0` counts as billing. Ordinary rate limits wait the delay Google asks for, then fall back to the next configured model. Two tests were added.
2. **Speed:** replies use `thinking_level=low`, and the app turns this off if a model rejects it. Pages load lazily and are prefetched while idle. Chat shows its progress stage with an elapsed timer. Voice runs diagnosis once after two turns, not on every sentence. Deployed retrieval uses full-text search directly, so no embedding call is wasted.
3. **Voice:** Chrome speech is used when the Live model isn't available. This happens only for model or provider errors; a closed session or a login error still shows its own message.
4. **User journey:** added an appliance picker to the start screen. Session titles are now clean first sentences.
5. **Deployment:** one service serving both site and API from the same address (same-origin WebSocket). The app accepts `postgres://` database URLs. Added `.gitignore` and `.dockerignore`, so the `.env` file and keys can't be committed.

## 3b. Knowledge base update (20 Nov 2026, evening)

- **85 records added** from 21 public manufacturer pages and user manuals (LG, Daikin India, Samsung, Crompton, Orient, Kent, Eureka Forbes Aquaguard). Each keeps its source title, URL, source type, evidence level and access date. Text is paraphrased, not copied. The original 292 records are unchanged (checked record by record).
- **Two new appliances:** microwave oven and water purifier, end to end (start-screen tiles, sessions, prompts, safety policy).
- **Appliance-aware retrieval:** when a session has no appliance yet, it is detected from the text, so a fridge question no longer pulls washing-machine records. Fixed a bug where "fridge not cooling" was guessed as a split AC.
- **Error-code aliases:** a source's alternatives (LG `CH38 / F4`) match as whole tokens, so `E1` never matches `E10`. Spaced codes (`CH 38`) are read too.
- **Diagnosis output** now includes required tools and an escalation reason (migration `0004`, additive).
- **Microwave rule in server code:** any generated step that opens the cabinet or touches the magnetron, high-voltage capacitor, diode or transformer becomes a hand-over to authorised service.
- **Quality report** (`docs/DATASET_QUALITY_REPORT.md`): 0 duplicates, 0 invalid categories, 0 conflicting code meanings, 365 of 377 records with a source URL. The 12 without one are FixSaathi team guidance, attributed to the team.

## 3c. Quality pass (20 Nov 2026, night)

**Bugs found and fixed**
- *Chat repeated the technician's message to Gemini* (once in the flattened history, once as input). Chat now sends real user/model turns, and the message being answered is sent once.
- *Follow-ups lost context*: retrieval used only the first message and the latest one. It now also uses the last two technician turns, and the most recent photo stays available for questions like "is that a burn mark?".
- *Search missed word forms*: the full-text index used no stemming, so "burn" did not match "burning" and "humming" did not match "hum". It now uses English stemming (migration `0005`).
- *Safety re-check missed word forms*: the server's power-sensitive word check matched "remove" but not "removing", and "replace" but not "replaced". It now matches word forms. Over-matching only locks more steps.
- *Wasted embedding call on every message* when `VECTOR_SEARCH_MODE=auto` and no index had been built. The call is now skipped.
- *Slow replies on the live site (found in the production log).* The first real chat took 24 s: `gemini-3.6-flash` and `gemini-3.5-flash` returned quota errors on the free-tier key and were each retried after a wait before `gemini-3.1-flash-lite` answered (about 10 s). Exhausted models are now tried once with no retry wait, then skipped for the cooldown Google asks for (at least 60 s), so later messages go straight to a model that works.
- *Stray space* left where an invented citation was removed, in chat and in speech.
- *Voice read Markdown symbols and record ids aloud.* Voice messages now ask Gemini for short spoken replies, and the browser strips symbols before speaking.
- *Printing a report gave white text on white paper.* Added print styles.
- *Unclear startup crash* when `SECRET_KEY` or `DATABASE_URL` was missing. The server now says what to fix, and `scripts/setup_env.py` creates the file.
- *Help page overstated voice* ("live voice and camera"). Corrected, and added answers on how the AI works and which appliances are covered.

**Dataset**
- Rewrote one misleading team-written step ("Try bypassing the regulator…") as an observation-only check.
- Corrected the `requires_power_off` flag on 8 records, using the same word-form fix.
- Reviewed the 280 ApplianceDB records: no encoding errors, no empty faults, every record sourced. The three UK/US pairs with the same code are kept, because markets differ. The prompts now say that a code match from a US or UK model must be confirmed against the Indian label.

**AI behaviour**
- A new chat prompt answers the question first, then gives ranked causes, discriminating checks and the next step. Length matches the message, it handles follow-ups and reported check results, says when the knowledge base has no record, and keeps every safety rule.
- Replies use light Markdown, which the app renders safely (no HTML), with numbered citations linked to their sources.

**Interface**
- New design system (tokens, cards, buttons, inputs, chips) and redesigned sidebar, sign-in, home (live knowledge count and AI status), chat, workspace, history (search, mobile cards), reports, dashboard, help, demo, voice and the camera dialog.

## 3d. Attachments, camera, sign-in and backend hardening (20 Nov 2026, late night)

**New, working features**
- *Password visibility:* an eye button in the password field on sign-in and registration shows or hides the password while you type. It keeps your cursor and resets to hidden when you submit or switch modes. Registration shows a live length hint.
- *"+" attach menu* in the chat composer (home and assistant): **Photos and images** (several at once), **PDF or document** (PDF, Word .docx, TXT, CSV, Markdown; several at once), and **Take a photo**. Also drag-and-drop and pasting an image. Up to 6 files per message, each removable before sending. Clear messages for unsupported or oversized files. Upload progress shows in the chat ("Uploading 2 of 3: manual.pdf").
- *Camera:* live preview using the back camera by default, a front/back switch when the device has both, capture, preview with **Retake** / **Use this photo**, and nothing is uploaded until the message is sent. It explains each failure: permission denied, no camera, camera busy, or a page that is not https. Fallbacks: **Use phone camera app** (the phone's own camera) and **Upload from gallery**. The camera is released whenever the dialog closes.
- *Documents in the AI:* PDFs are sent to Gemini as real PDFs, so scanned pages are read too. Word and text files are sent as their extracted text, wrapped as data that cannot act as instructions. Document text also feeds the knowledge-base search. The workspace lists documents separately from photos; PDFs and text open in a new tab, Word files download.
- *Failed uploads lose nothing:* the message is taken back out of the chat, and your text and files are put back in the box with the reason.

**Backend bugs fixed**
- Photos kept their **EXIF and GPS metadata** (location, camera make). They are now rotated upright and re-encoded without metadata.
- There was no pixel limit, so very large images were only partly guarded against. Images over 40 megapixels are now refused.
- There was no limit on files per session. It is now 60.
- Two simultaneous registrations with the same email would return a **500**. They now return `EMAIL_TAKEN`.
- Login timing revealed whether an email had an account. A dummy hash now evens out the timing.
- Reusing an old refresh token did not revoke the account's other sessions. It now does, with a 30-second grace period so two tabs refreshing together still work.
- Unexpected errors returned a **plain-text 500** the app could not read. All errors are now JSON. Database conflicts return 409, and an unreachable database returns 503.
- The component locator would accept a PDF. It now refuses documents.
- `pypdf` was missing from `requirements.txt`.

**Frontend bugs fixed**
- A **502/503 while the free server wakes up signed the user out**, because the refresh call cleared the saved sign-in on any error. Only a real "token invalid" now signs out. Startup retries for up to about 45 s and shows "Waking up the server".
- Raw proxy errors showed as "Request failed (503)". They are now readable messages.
- Tablets now get the slim sidebar by default so the chat has room.

**Known limitation (by design, not changed):** registering with an existing organisation's name joins that organisation. Technicians only ever see their own sessions, so no data is exposed, but there are no invitations yet.

## 4. Test results (run 20 Nov 2026)

| Suite | Result |
|---|---|
| Backend pytest (real PostgreSQL, fake Gemini) | **166 passed, 0 failed**. The 25 file tests use real files built in the test: photos with GPS and rotation, PDFs (text, scanned, encrypted, 61 pages, damaged), Word, CSV, Markdown, disguised binaries, path-traversal names, size, count and access limits, chat with PDF and documents, and the refresh-token and login-timing fixes. Covers chat turns and follow-ups, stemming, citation clean-up, the embedding skip, dataset quality, appliance detection, retrieval per appliance, code aliases, the microwave rule and the diagnosis fields. |
| Frontend unit and component tests (Vitest, jsdom, Testing Library) | **29 passed**: password toggle (sign-in and registration), attach menu (open, options, Escape), several files, unsupported, oversized and too many files, paste, file rules, draft restored after a failed upload, camera (back camera, switch, release, denied, no camera, busy, not https, preview and confirm, non-image refused), opening files, API client (waking server keeps sign-in, invalid token signs out, proxy errors), Markdown, speech text |
| TypeScript type check and production build | Pass |
| Lint (oxlint) | 0 errors, 3 warnings (re-render performance hints) |
| Browser end-to-end, real Chrome against the production-style single service (re-run after the knowledge update) | **29 of 29 checks pass**: login and errors, register, refresh survives reload, chat, sidebar, camera capture, component box, diagnosis, image evidence, lock, server 409 refusal, one statement keeps the lock, both unlock, step completion, step picture, report contents, safety disclaimer, history, saved diagnoses, roles, manager dashboard, voice on a closed session, mobile without horizontal scroll |
| Browser test for a provider failure | Pass: the specific "API key invalid" error and its fix hint are shown |
| Browser demo-mode test, **no AI key**, `STORAGE_PROVIDER=database`, server restarted mid-test | **16 of 16 pass**: health, AI-unavailable notice, demo link, labels, photo, banner, lock (409), photo after restart, unlock, demo report label, 401 without a token, no page errors |
| Console or page errors during the full screenshot journey | 0 |
| Browser test of the new features (real Chrome, simulated camera device) | **31 of 31 pass**: password toggle, + menu with 2 photos and 3 documents, unsupported file, camera capture, retake, use, sent, photos and documents in the workspace, PDF opens, Word downloads, document added in the workspace, names kept after reload, failed upload restores the draft, mobile (390 px) and tablet (820 px) menu fit, no sideways scroll, camera opens, permission denial |
| Fresh setup from the source ZIP (new venv, `npm ci`, `setup_env.py`, migrations, ingest, one-process run, browser smoke test) | **8 of 8 pass** |

**Not covered by automated tests:**
- Real Gemini answers. The tests use a fake. One live chat was confirmed in the production log (20 Nov, 17:12 IST, answered by `gemini-3.1-flash-lite`); the new prompt has not yet been tried live.
- Browser voice mode. Headless Chrome has no speech recognition.

## 5. Known limitations

- **Gemini Live:** not available on the current key. Voice uses browser speech plus Gemini.
- **Free Render plan:** sleeps after 15 minutes idle, and the first request afterwards takes about 50 seconds. Keep it awake with a free uptime monitor, or use the Starter plan.
- **Photo storage:** photos are stored in Neon, whose free tier has limited storage (about 0.5 to 1 GB). That's fine for the evaluation; move to Cloud Storage for scale.
- **Knowledge base:** 377 records. Washing machines still make up 253, because the ApplianceDB sample is mostly washers and we kept every useful record. Microwave and purifier records come from a few brands only (Samsung; Kent, Aquaguard). MCB and solar have 1 record each. No record is technician-reviewed yet.
- **Retrieval accuracy is not measured.** Tests check that answers stay in the right appliance and return the expected record for one realistic query per appliance. There is no labelled evaluation set, so no accuracy figure is claimed.
- **Data licence:** ApplianceDB is ODbL-1.0 (attribution and share-alike). Keep the attribution.
- **Free-tier key:** small per-minute limits. The fallback models help, but heavy use during judging can still slow replies.

## 6. Deployment

- **Code:** https://github.com/PreranaPJois-123/FixSaathi (branch `main`). Pushes deploy automatically.
- **Service:** Render "fixsaathi" (Docker, Singapore, free plan) at https://fixsaathi.onrender.com
- **Database:** Neon, database `fixsaathi` on the default branch of the existing project.
- **Startup:** each start runs `alembic upgrade head`, loads the knowledge records if they're missing, then starts uvicorn.
- **To finish:** in the Render dashboard, go to fixsaathi > Environment and set `GEMINI_API_KEY` (a newly created key), then choose Save, rebuild and deploy.
- **To run locally:** see `README.md` in the repo. You need Python 3.12, Node 22 and PostgreSQL 16.
