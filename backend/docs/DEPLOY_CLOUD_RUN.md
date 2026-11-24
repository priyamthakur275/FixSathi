# Deploying to Cloud Run (asia-south1): guide only, not executed

Prerequisites: a project with billing (or credits) attached; the run, artifactregistry, cloudbuild, secretmanager and sqladmin/alloydb APIs enabled.

```bash
PROJECT=your-project-id; REGION=asia-south1
# Secrets
printf '%s' "$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')" | gcloud secrets create fixsaathi-secret-key --data-file=-
printf '%s' "YOUR_GEMINI_KEY" | gcloud secrets create gemini-api-key --data-file=-
printf '%s' "postgresql+psycopg://USER:PASS@HOST:5432/fixsaathi" | gcloud secrets create fixsaathi-db-url --data-file=-

# Backend
cd backend
gcloud run deploy fixsaathi-api --source . --region $REGION \
  --set-secrets SECRET_KEY=fixsaathi-secret-key:latest,GEMINI_API_KEY=gemini-api-key:latest,DATABASE_URL=fixsaathi-db-url:latest \
  --set-env-vars APP_ENV=production,CORS_ORIGINS=https://YOUR_FRONTEND_URL,GEMINI_AGENT_MODEL=...,GEMINI_LIVE_MODEL=...,GEMINI_EMBED_MODEL=...,NANO_BANANA_MODEL=... \
  --timeout 3600 --session-affinity --max-instances 3 --allow-unauthenticated
# Migrations: run once as a Cloud Run job, or locally against the DB:  alembic upgrade head
```

Notes:
- WebSockets work on Cloud Run. A request (including a live socket) is capped by `--timeout` (max 60 min). Session affinity is best-effort, so the client should reconnect on close.
- `LOCAL_STORAGE_PATH` on Cloud Run is ephemeral. A Cloud Storage adapter is **not implemented yet**, so uploaded photos do not survive instance restarts. Add `integrations/storage/gcs.py` before real use.
- The rate limiter is per instance (in memory).
- Frontend: build with `VITE_API_BASE_URL=https://fixsaathi-api-...run.app` and deploy `frontend/Dockerfile` as a second service, or to Firebase Hosting.
