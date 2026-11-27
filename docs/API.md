# API and frontend mapping

Base: `/api/v1`. Errors always look like `{"error": {"code", "message", "details"}}`. Lists return `{items, total, limit, offset}`. Interactive docs are at `/docs` (OpenAPI).

| Frontend (file → action) | Endpoint | Persists |
|---|---|---|
| LoginPage → sign in / register | `POST /auth/login`, `POST /auth/register` | users, refresh_tokens |
| AuthContext → restore on reload | `POST /auth/refresh`, `GET /auth/me` | rotates refresh token |
| ProfilePage → sign out | `POST /auth/logout` | revokes refresh token |
| SettingsPage → language | `PATCH /users/me` | users.preferred_language |
| AppContext.send (first message) | `POST /sessions` | repair_sessions |
| Composer / CameraModal → photo | `POST /sessions/{id}/images` (multipart) | media + file in storage |
| AppContext.send | `POST /sessions/{id}/messages/stream` (SSE with sentence-level safety screening) or fallback `POST /sessions/{id}/messages` | conversations (user + AI reply) |
| Chat → thumbs up / down on an AI answer | `PUT /sessions/{id}/messages/{message_id}/feedback` with `{helpful, comment?}` (`helpful: null` clears it; owner only) | conversations.metadata.feedback |
| ChatPage `/chat/:id` (open existing) | `GET /sessions/{id}`, `GET /sessions/{id}/messages` | |
| Sidebar chat history and search | `GET /sessions?mine=true&q=` (searches titles, issue and message text; hidden chats excluded) | |
| Sidebar → Rename | `PATCH /sessions/{id}` with `{title}` (allowed on closed sessions too) | repair_sessions.title |
| Sidebar → Delete | `DELETE /sessions/{id}` (soft: sets `hidden_at`, cancels an open session; reports and safety log kept) | repair_sessions.hidden_at |
| Chat / workspace / report → Download PDF | `GET /sessions/{id}/report.pdf` (built from recorded data; locked power-step instructions withheld) | |
| History, My Repairs | `GET /history?open_only=` | |
| RepairSessionPage → Nameplate & error display | `POST /sessions/{id}/read-nameplate`, `PATCH /sessions/{id}/nameplate` | repair_sessions.appliance_details.nameplate |
| → Expected readings reference | `GET /expected-readings?appliance_type=` | |
| → Run diagnosis | `POST /sessions/{id}/diagnose`, `GET .../diagnosis` | diagnosis_results, ai_usage |
| → Identify component | `POST /sessions/{id}/identify-component` | identified_components |
| → Generate steps | `POST /sessions/{id}/steps/generate`, `GET .../steps` | repair_steps |
| → Tick a step | `POST /sessions/{id}/steps/{step}/complete` (409 if safety missing), `/reopen` | repair_steps, safety_events |
| → Step picture | `POST /sessions/{id}/steps/{step}/visual` | media (kind=generated) |
| SafetyPanel | `GET /sessions/{id}/safety`, `POST .../safety/confirm`, `GET .../safety/events` | safety_confirmations, safety_events |
| → Ask a senior | `POST /sessions/{id}/escalate` | escalation_requests |
| → Similar repairs | `GET /sessions/{id}/similar-repairs` | |
| → Finish | `POST /sessions/{id}/feedback`, `POST /sessions/{id}/reports` | feedback, service_reports |
| ReportsPage | `GET /reports`, `GET /reports/{id}` | |
| SavedDiagnoses | `GET /diagnoses` | |
| SeniorSupport | `GET /escalations`, `PATCH /escalations/{id}` (manager) | |
| ManagerDashboard | `GET /dashboard/overview`, `/dashboard/repairs`, `/dashboard/technicians`, `/dashboard/metrics` | |
| VoicePage | `WS /live/{session_id}` (see LIVE_PROTOCOL.md) | conversations (transcripts), repair_steps, safety_events |
| EvaluationPage (`/evaluation`, public) | `GET /evaluation` | serves `docs/EVALUATION_RESULTS.json` |
| Images in UI | `GET /media/{id}` (bearer auth, fetched as a blob) | |
| Ops | `GET /health`, `GET /ready` | |

## Safety block response (HTTP 409)

```json
{"error": {"code": "SAFETY_CONFIRMATION_REQUIRED", "message": "...",
  "details": {"allowed": false, "reason": "SAFETY_CONFIRMATION_REQUIRED", "missing": ["tester_checked"], "disclaimer": "..."}}}
```

`reason` may also be `SAFETY_CONFIRMATION_EXPIRED` or `NOT_SESSION_TECHNICIAN`.

## AI error codes

`AI_NOT_CONFIGURED`, `MODEL_NOT_CONFIGURED` (503), `MODEL_UNAVAILABLE`, `AI_QUOTA_EXCEEDED` (503), `AI_TIMEOUT`, `AI_INVALID_OUTPUT`, `AI_ERROR` (502). Chat stores the technician's message even when the AI fails, and returns `ai_status` + `ai_error`.
