# Architecture

```mermaid
flowchart LR
  subgraph Browser
    UI[React app] -- REST JSON + multipart --> API
    UI -- WebSocket /api/v1/live/:id --> LIVE
  end
  subgraph FastAPI
    API[REST routers] --> SVC[Services]
    LIVE[Live relay] --> SVC
    SVC --> SAFE[SafetyService.guard]
    SVC --> AG[Agents: diagnosis, guidance, part locator, step image]
    SVC --> RET[Retrieval: embeddings or keyword]
    SVC --> ST[Local storage adapter]
  end
  SVC --> PG[(PostgreSQL / AlloyDB)]
  AG --> GEM[Gemini API]
  LIVE --> GL[Gemini Live API]
  RET --> GEM
```

Layers: `api/v1` (HTTP only) → `services` (business rules, access policy, safety) → `db/models` and `integrations` (Gemini, storage). Prompts live in `app/agents/prompts.py`, and output schemas in `app/agents/schemas.py`. All model output is validated with Pydantic before use.

## ER diagram

```mermaid
erDiagram
  organisations ||--o{ users : has
  users ||--o{ repair_sessions : owns
  organisations ||--o{ repair_sessions : scopes
  users ||--o{ refresh_tokens : has
  repair_sessions ||--o{ conversations : has
  repair_sessions ||--o{ media : has
  repair_sessions ||--o{ diagnosis_results : has
  repair_sessions ||--o{ identified_components : has
  media ||--o{ identified_components : on
  repair_sessions ||--o{ repair_steps : has
  repair_sessions ||--o{ safety_confirmations : has
  repair_sessions ||--o{ safety_events : has
  repair_sessions ||--o{ escalation_requests : has
  repair_sessions ||--o| service_reports : has
  repair_sessions ||--o{ feedback : has
  repair_sessions ||--o{ ai_usage : logs
  repair_knowledge ||--o{ repair_embeddings : indexed_as
```

## Session states

`created → active ⇄ diagnosing / awaiting_confirmation / guidance_in_progress / escalated → completed | cancelled`. Transitions are validated in `services/sessions.py`. `completed` and `cancelled` are terminal.

## Access policy (`services/access.py`)

- Technician: only their own sessions.
- Manager: read access to sessions in their organisation, and can update escalations. They cannot confirm safety or act on a technician's session.
- Admin: everything.
- A session someone may not see returns 404 rather than 403, so its existence is not revealed.
