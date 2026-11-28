# What Was Built Before vs. During the Hackathon

This record is taken directly from `git log` on branch `antigravity-v2` (no embellishment).

## 1. What Existed Before Nov 27

- **Pre-hackathon baseline (`6bbee2f`, imported 2026-11-26):** `FixSathi-main` — the core FastAPI + React + PostgreSQL application built earlier for Google Startup Buildathon India 2026 (auth, sessions, 377-record repair knowledge base, hybrid retrieval, server-side power-isolation safety lock, diagnosis/steps/reports, Gemini Live relay, TTS, and 350+ automated tests).
- **Nov 26 UI & design foundation (4 commits):**
  - `7ecbf04` (2026-11-26): Unified design token system, high-contrast Sunlight mode, Hindi-first greeting, and strict red/green power-state colors.
  - `9ce5b82` (2026-11-26): Mobile-first Home, guided 5-stage repair workspace, diagnosis "Why" panel, SVG part cards, and manager funnel.
  - `65b3900` (2026-11-26): Fixed mobile clipping on hero speak CTA and 5-step progress labels.
  - `49739b8` (2026-11-26): Fixed CSS grid horizontal overflow on mobile repair workspace.

## 2. What Was Built on Nov 25–27 (Hackathon Sprint)

In addition to the Nov 26 UI foundation above, the following features, reliability hardening, live Gemini integration, and Google Cloud Run deployment were built on **2026-11-27**:

- **Live Vision, Streaming, Evaluation & Hindi polish:**
  - `56d8218` (2026-11-27): Warm up `/health` on login and cache repeated knowledge lookups.
  - `69bf163` (2026-11-27): Gemini Vision nameplate and error-display reader (`POST /read-nameplate`) with technician verification/correction and retrieval grounding.
  - `172e124` (2026-11-27): Hardened nameplate endpoint ownership, file size/type limits, and log redaction.
  - `4f86d5e` (2026-11-27): Public `/evaluation` page rendering `docs/EVALUATION_RESULTS.json`.
  - `0dbadc3` (2026-11-27): Server-screened SSE chat streaming (`StreamScreener`) with automatic non-streaming fallback.
  - `a36f75f` (2026-11-27): Informational expected-readings reference cards without live-work guidance.
  - `2e91987` (2026-11-27): Spoken Hindi technician vocabulary in chat and live prompts.
  - `639c6d3` (2026-11-27): Removed dead code, unused styles, and overclaiming copy.
  - `1a56f91`, `93c9eb6`, `157df99` (2026-11-27): 90s demo script, judge Q&As, and fresh captures.
  - `a8b0443` (2026-11-27): Unmocked live Gemini smoke script (`backend/scripts/smoke_live.py`) and sample nameplate image.
- **Live Gemini Configuration & Cloud Run + Cloud SQL Deployment:**
  - `9dca899` (2026-11-27): Configured live Gemini models, verified live smoke test, and moved scripted demos to the **Offline backup** footer link.
  - `f63e18a`, `8980e92`, `e2e608d` (2026-11-27): Single-container `Dockerfile` for Cloud Run, unbuffered SSE middleware, fast/diagnosis model routing, Cloud SQL PostgreSQL 16 via Unix socket, Secret Manager wiring, and `DEPLOY_CLOUDRUN.md`.
- **Stage Reliability & Auditability:**
  - `b602a4f`, `9bc7fda` (2026-11-27): Per-operation timeouts, 5-minute circuit breaker, SSE `working` heartbeats, "How this answer was made" provenance panel, technician nameplate confirmation gate before diagnosis, and public `/api/v1/samples/nameplate` endpoint.
  - `843f49d` (2026-11-27): Jittered retry (400–800 ms) on 503/timeout for the first two streaming models, 5-minute skip of `gemini-4-neon` after 429, and clear user-facing busy message when all models return 503.
  - *(Current commit)* (2026-11-27): Measured model probe table (`docs/MODEL_USAGE.md`), optional live Cloud Run Voice (`gemini-3.8-live`) and TTS (`gemini-3.8-flash-tts`) checks in `smoke_live.py`, and this hackathon history document.
