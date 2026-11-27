# Measured Gemini Model Usage

All numbers below are from real API calls executed on **2026-11-27** using the same Gemini API key configured in Secret Manager for the deployed Cloud Run service (`https://fixsaathi-915991223959.us-east4.run.app`, project `geminisprints26blr-3820`, region `us-east4`). No mocks or estimated figures.

## 1. Direct Model Probes (3 runs each)

Each model was called 3 consecutive times with a minimal prompt (`max_output_tokens=16`, `thinking_level=low` on `v1`; `v1beta` for `gemini-decision-1`):

| Model | API Version | Run 1 | Run 2 | Run 3 | Result / Error |
|---|---|---|---|---|---|
| `gemini-3.5-flash-lite` | `v1` | `OK` (738 ms) | `OK` (780 ms) | `OK` (505 ms) | **3/3 OK** — reliable primary for chat, vision, diagnosis fallback |
| `gemini-4-hydrogen` | `v1` | `Timeout` (>15,002 ms) | `503 UNAVAILABLE` (1,251 ms) | `Timeout` (>15,002 ms) | **0/3 under 8 s** — `503 UNAVAILABLE` ("currently experiencing high demand") and >15 s timeouts. Routing left unchanged (configured first for diagnosis with automatic fallback to `gemini-3.5-flash-lite`, which answers in ~1–2 s). |
| `gemini-4-neon` | `v1` | `429 RESOURCE_EXHAUSTED` (268 ms) | `429 RESOURCE_EXHAUSTED` (123 ms) | `429 RESOURCE_EXHAUSTED` (115 ms) | **0/3** — quota exhausted on this API key. Skipped for 5 minutes in memory after any 429 so it does not delay replies or overwrite real error messages. **Not claimed as active.** |
| `gemini-4-carbon` | `v1` | `429 RESOURCE_EXHAUSTED` (197 ms) | `429 RESOURCE_EXHAUSTED` (185 ms) | `429 RESOURCE_EXHAUSTED` (94 ms) | **0/3** — quota exhausted on this API key. **Not configured and not claimed.** |
| `gemini-decision-1` | `v1beta` | `404 NOT_FOUND` (164 ms) | `404 NOT_FOUND` (111 ms) | `404 NOT_FOUND` (96 ms) | **0/3** — `models/gemini-decision-1 is not found for API version v1beta, or is not supported for generateContent` (REST check also `404` in 133 ms). Optional decision gate skipped. |

## 2. Live Cloud Run End-to-End Verification

Measured against `https://fixsaathi-915991223959.us-east4.run.app`:

| Capability | Endpoint | Model That Actually Answered | Measured Result |
|---|---|---|---|
| Streamed chat (English, Devanagari Hindi, Hinglish) | `POST /api/v1/sessions/{id}/messages/stream` | `gemini-3.5-flash-lite` | Verified in 3/3 consecutive `smoke_live.py` runs (4–6 SSE deltas, safety lock enforced server-side) |
| Nameplate & error display Vision | `POST /api/v1/sessions/{id}/read-nameplate` | `gemini-3.5-flash-lite` (fallback when `gemini-4-hydrogen` unavailable) | Extracted `LG LS-Q18YNZA` + `CH38`, matched 5 KB records |
| Structured diagnosis | `POST /api/v1/sessions/{id}/diagnose` | `gemini-3.5-flash-lite` (fallback from `gemini-4-hydrogen`) | HTTP 201 in 1,745 ms (`latency_ms=1172`) |
| Real-time voice & video (WebSocket) | `WS /api/v1/live/{id}` | `gemini-3.8-live` | Connected (`session_ready`), returned assistant `transcription` and `audio_chunk` (`audio/pcm;rate=24000`) in 3,814 ms |
| Text-to-Speech | `GET /api/v1/sessions/{id}/messages/{msg_id}/speech` | `gemini-3.8-flash-tts` | HTTP 200, `audio/wav`, 1,433,352 bytes in 9,737 ms (prebuilt `Charon` voice) |
| Knowledge embeddings | `POST /api/v1/sessions/...` (hybrid retrieval) | `gemini-embedding-2` | Configured (`VECTOR_SEARCH_MODE=auto`); falls back seamlessly to PostgreSQL full-text search if unindexed |

## 3. Routing & Fallback Policy

- **Fast chat (`op='chat'`):** `gemini-3.5-flash-lite` first (8 s timeout, 1 jittered retry on 503/timeout for the first two models), falling back to `gemini-4-hydrogen`.
- **Diagnosis & Vision (`op='diagnosis'`, `op='nameplate'`):** `gemini-4-hydrogen` is configured first (`GEMINI_AGENT_MODEL`) with automatic failover to `gemini-3.5-flash-lite` when hydrogen is overloaded or times out. Because `gemini-4-hydrogen` answered 0/3 probes under 8 s during testing, we did **not** tighten its timeout or claim it as primary-verified; the UI provenance panel ("How this answer was made") and `smoke_live.py` both display the exact `model_identifier` that answered each call.
- **No-quota protection:** `gemini-4-neon` is skipped for 5 minutes after a 429 so its error never masks a 503 from working models.
- **Not claimed:** `gemini-4-neon`, `gemini-4-carbon`, `gemini-decision-1`, and `gemini-3.1-flash-image` (configured for on-demand step illustrations, not probed in this run).
