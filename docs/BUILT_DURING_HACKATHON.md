# What Was Built Before vs. During the Hackathon

This record is taken directly from `git log` on branch `antigravity-v2` (no embellishment).

## 1. What Existed Before Nov 27

- **Pre-hackathon baseline (`7bc3aed`, imported 2026-11-26):** `FixSathi-main` — the core FastAPI + React + PostgreSQL application built earlier for Google Startup Buildathon India 2026 (auth, sessions, 377-record repair knowledge base, hybrid retrieval, server-side power-isolation safety lock, diagnosis/steps/reports, Gemini Live relay, TTS, and 350+ automated tests).
- **Nov 26 UI & design foundation (4 commits):**
  - `0723148` (2026-11-26): Unified design token system, high-contrast Sunlight mode, Hindi-first greeting, and strict red/green power-state colors.
  - `98cbf4e` (2026-11-26): Mobile-first Home, guided 5-stage repair workspace, diagnosis "Why" panel, SVG part cards, and manager funnel.
  - `5473d4f` (2026-11-26): Fixed mobile clipping on hero speak CTA and 5-step progress labels.
  - `b647b90` (2026-11-26): Fixed CSS grid horizontal overflow on mobile repair workspace.

## 2. What Was Built on Nov 25–27 (Hackathon Sprint)

In addition to the Nov 26 UI foundation above, the following features, reliability hardening, live Gemini integration, and Google Cloud Run deployment were built on **2026-11-27**:

- **Live Vision, Streaming, Evaluation & Hindi polish:**
  - `1ce695b` (2026-11-27): Warm up `/health` on login and cache repeated knowledge lookups.
  - `4ae2765` (2026-11-27): Gemini Vision nameplate and error-display reader (`POST /read-nameplate`) with technician verification/correction and retrieval grounding.
  - `945f6b4` (2026-11-27): Hardened nameplate endpoint ownership, file size/type limits, and log redaction.
  - `cb11d11` (2026-11-27): Public `/evaluation` page rendering `docs/EVALUATION_RESULTS.json`.
  - `c742595` (2026-11-27): Server-screened SSE chat streaming (`StreamScreener`) with automatic non-streaming fallback.
  - `05b9d36` (2026-11-27): Informational expected-readings reference cards without live-work guidance.
  - `2d71534` (2026-11-27): Spoken Hindi technician vocabulary in chat and live prompts.
  - `52c092c` (2026-11-27): Removed dead code, unused styles, and overclaiming copy.
  - `f3af61d`, `2505777`, `1bb1191` (2026-11-27): 90s demo script, judge Q&As, and fresh captures.
  - `3fc7d8b` (2026-11-27): Unmocked live Gemini smoke script (`backend/scripts/smoke_live.py`) and sample nameplate image.
- **Live Gemini Configuration & Cloud Run + Cloud SQL Deployment:**
  - `67a9254` (2026-11-27): Configured live Gemini models, verified live smoke test, and moved scripted demos to the **Offline backup** footer link.
  - `ce9083d`, `32c78a9`, `2c1d96a` (2026-11-27): Single-container `Dockerfile` for Cloud Run, unbuffered SSE middleware, fast/diagnosis model routing, Cloud SQL PostgreSQL 16 via Unix socket, Secret Manager wiring, and `DEPLOY_CLOUDRUN.md`.
- **Stage Reliability & Auditability:**
  - `6548c53`, `b78bebb` (2026-11-27): Per-operation timeouts, 5-minute circuit breaker, SSE `working` heartbeats, "How this answer was made" provenance panel, technician nameplate confirmation gate before diagnosis, and public `/api/v1/samples/nameplate` endpoint.
  - `4501cd4` (2026-11-27): Jittered retry (400–800 ms) on 503/timeout for the first two streaming models, 5-minute skip of `gemini-4-neon` after 429, and clear user-facing busy message when all models return 503.
  - *(Current commit)* (2026-11-27): Measured model probe table (`docs/MODEL_USAGE.md`), optional live Cloud Run Voice (`gemini-3.8-live`) and TTS (`gemini-3.8-flash-tts`) checks in `smoke_live.py`, and this hackathon history document.
