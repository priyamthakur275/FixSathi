# Feature audit (20 Nov 2026)

What each evidence level means:
- **Tested:** covered by automated tests. The backend tests use real PostgreSQL with a fake Gemini; the browser tests run real Chrome against the real API.
- **Verified live:** run by the team with the real Gemini key on 20 Nov 2026.
- **Not verified live:** the code exists and is tested with a fake, but hasn't been run against real Gemini.

## Core

| Feature | Status | Evidence |
|---|---|---|
| Register, login, refresh rotation, logout, roles, organisation scoping | Done | Tested: expired and invalid tokens, rate-limited login, self-registration can't pick a role |
| Unauthorised access (no token, other user, other organisation) | Done | Tested: 401 and 404, browser test confirms a 401 without a token |
| Repair sessions, appliance picker (6 categories), clean titles | Done | Tested |
| Chat with history; photos reload when a session is reopened | Done | Tested (fixed a bug: reopened sessions lost their photos) |
| Photo upload and camera capture, validated by decoding the bytes (JPEG, PNG or WebP, max 8 MB) | Done | Tested: invalid file returns 415 |
| **Photo persistence** (`STORAGE_PROVIDER=database`) | Done | Tested: survives a storage reset and a real server restart in the browser; other users get 404 |
| Missing photo file | Done | Clear `MEDIA_MISSING` 404; the UI shows "Image unavailable" |
| Service reports, history, saved diagnoses, manager dashboard | Done | Tested |
| `/health`: database check, 503 when down, HEAD supported | Done | Tested with a simulated database outage |

## AI (Google Gemini, server side only)

| Feature | Status | Evidence |
|---|---|---|
| Key valid, models visible, text and embedding calls | Done | Verified live (`check_gemini.py --call`) |
| Chat with a photo (vision), replying in Hinglish | Done | Verified live: burnt fan photo, 15:37 IST |
| Structured diagnosis, ranked, confidence marked as an estimate | Done | Tested; **not verified live** |
| Repair steps | Done | Tested; **not verified live** |
| Component box on the photo | Done | Tested; **not verified live** |
| Step pictures (Nano Banana) | Done | Tested; **not verified live**. The model is visible to the key. |
| Error classification and fix hints, rate-limit retries, model fallback | Done | Tested with real SDK error classes |
| Grounding in 377 repair records, invented citations removed, coverage label | Done | Tested |
| Appliance-aware retrieval (detected from text when the session has none) | Done | Tested: one realistic query per appliance stays in its category |
| Microwave oven and water purifier support | Done | Tested (data, detection, retrieval, microwave server rule). Not verified live. |
| Error-code aliases (`CH38 / F4`), spaced codes (`CH 38`) | Done | Tested |
| Required tools and escalation reason in diagnosis | Done | Tested with fake Gemini. Not verified live. |
| Conversation-aware chat (real turns, follow-ups, earlier photo kept) | Done | Tested with fake Gemini. **Not verified live** from this environment. |
| Markdown answers with numbered sources | Done | Tested (parser unit tests, browser screenshots) |
| Password show/hide on sign-in and registration | Done | Component tests + browser test |
| + attach menu: several photos, PDF, Word, TXT/CSV/MD, camera, drag-and-drop, paste | Done | Component tests + browser test (real Chrome) |
| Camera: preview, front/back, retake, confirm, permission and https errors, phone-camera fallback | Done | Component tests; browser test with a simulated camera. **Real phone cameras not tested from this environment.** |
| PDFs and documents read by the AI | Done | Backend tests with fake Gemini (PDF sent as PDF, text as data). **Not verified live.** |
| Photo metadata (GPS) removed on upload | Done | Backend test |
| Fine-tuned or custom-trained model | **Not built** | FixSaathi uses Gemini through its API with retrieval. We do not claim a trained model. |
| Embedding re-ranking | Code exists, not used in deployment | No index built; deployment uses `VECTOR_SEARCH_MODE=keyword` |
| **Gemini Live** streaming voice and camera | Built, not usable with the current key | Tested with a fake Live session. The key lists no Live model. |
| Browser voice mode (speech recognition to Gemini chat to speech) | Done | Verified manually in Chrome. Not automatable in headless Chrome. |

## Demo mode

| Feature | Status | Evidence |
|---|---|---|
| `/demo` with 2 scenarios: ceiling fan burn (real photo), split AC not cooling | Done | Tested in the browser with **no AI key** |
| Demo replies labelled "scripted sample, not live AI"; never labelled AI-generated | Done | Tested |
| Demo sessions use the real safety gate, logging and reports | Done | Tested: 409 before the statements, unlocked after both |
| AI-unavailable notice links to the demo | Done | Tested |

## Safety

| Check | Status |
|---|---|
| Both statements required; one alone keeps the lock | Tested |
| Server-side only; frontend flags ignored; direct API calls blocked (409) | Tested |
| Per session and per technician; can't be reused in another session or by another user | Tested |
| Expiry (`SAFETY_CONFIRMATION_TTL_MINUTES`, 60) | Tested |
| AI tools can't record statements or skip the gate | Tested |
| Blocked attempts logged | Tested |
| Locked instructions withheld from the client | Tested |
| No claim of measuring voltage | UI and reports say FixSaathi can't measure voltage |

## Not done

- **Cloud Run, AlloyDB, Cloud Storage:** planned, not built. The app runs on Render and Neon.
- **Field accuracy measurement:** none, so no accuracy numbers are claimed.
- **Official hackathon deck template:** not in this repo. The team must download it from the participant dashboard.
- **Uptime monitor:** has to be set up in UptimeRobot (see README).
