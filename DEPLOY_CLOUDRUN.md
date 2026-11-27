# Deploy FixSaathi to Google Cloud Run (Single Service + Neon PostgreSQL)

FixSaathi builds into one container image (`Dockerfile`): Vite compiles the React 19 frontend into `/app/web`, and FastAPI serves both the UI and API on `$PORT` (`8080`) with zero-CORS same-origin requests, unbuffered SSE streaming, WebSocket Live relay, and automatic Alembic migrations + 377-record knowledge seeding on startup (`backend/scripts/render_start.sh`).

Secrets live **only** in Google Secret Manager — never in git, Docker images, or logs.

---

## 1. Choose Region & Neon Database

Match the Cloud Run region closely to your Neon Postgres region:
- Neon in Ohio (`us-east-2`) -> `REGION=us-east4`
- Neon in Singapore (`ap-southeast-1`) -> `REGION=asia-southeast1`

Copy Neon's **direct** (non-`-pooler`) PostgreSQL connection string ending with `?sslmode=require` so Alembic migrations and advisory locks run reliably.

```bash
export PROJECT_ID="YOUR_GCP_PROJECT_ID"
export REGION="us-east4"   # or asia-southeast1 if Neon is in Singapore
gcloud auth login
gcloud config set project "$PROJECT_ID"
```

---

## 2. Enable Required Google Cloud APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

---

## 3. Store Secrets in Secret Manager & Grant Access

Run interactively so secrets never appear in git or shell scripts:

```bash
# 1) Gemini API key (paste when prompted, press Ctrl+D)
gcloud secrets create GEMINI_API_KEY --replication-policy="automatic" 2>/dev/null || true
printf '%s' "PASTE_GEMINI_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --data-file=-

# 2) Strong 64-byte JWT signing key
gcloud secrets create SECRET_KEY --replication-policy="automatic" 2>/dev/null || true
python3 -c "import secrets, sys; sys.stdout.write(secrets.token_urlsafe(48))" | gcloud secrets versions add SECRET_KEY --data-file=-

# 3) Neon direct PostgreSQL URL (?sslmode=require)
gcloud secrets create DATABASE_URL --replication-policy="automatic" 2>/dev/null || true
printf '%s' "PASTE_NEON_DIRECT_URL" | gcloud secrets versions add DATABASE_URL --data-file=-

# Grant Cloud Run's default compute service account read access to secrets
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for S in GEMINI_API_KEY SECRET_KEY DATABASE_URL; do
  gcloud secrets add-iam-policy-binding "$S" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## 4. Run Initial Migrations & Knowledge Seed Against Neon (One-Time Local)

```bash
cd backend && source .venv/bin/activate
DATABASE_URL="PASTE_NEON_DIRECT_URL" SECRET_KEY="migration-only-secret-0123456789-abcdef" alembic upgrade head
DATABASE_URL="PASTE_NEON_DIRECT_URL" SECRET_KEY="migration-only-secret-0123456789-abcdef" python scripts/ingest_knowledge.py
```

---

## 5. Deploy Single Service to Cloud Run

Uses `--min-instances 1` during the live demo to avoid cold starts, `^@^` delimiter to preserve commas in `GEMINI_AGENT_FALLBACK_MODELS`, and `STORAGE_PROVIDER=database` so uploaded technician photos persist in Postgres across container restarts.

```bash
cd ..
gcloud run deploy fixsaathi \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --min-instances 1 \
  --memory 1Gi \
  --timeout 300 \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest,SECRET_KEY=SECRET_KEY:latest,DATABASE_URL=DATABASE_URL:latest" \
  --set-env-vars "^@^APP_ENV=production@STORAGE_PROVIDER=database@VECTOR_SEARCH_MODE=auto@GEMINI_AGENT_MODEL=gemini-4-neon@GEMINI_FAST_MODEL=gemini-3.5-flash-lite@GEMINI_AGENT_FALLBACK_MODELS=gemini-4-hydrogen,gemini-3.5-flash-lite@GEMINI_THINKING_LEVEL=low@GEMINI_EMBED_MODEL=gemini-embedding-2@GEMINI_LIVE_MODEL=gemini-3.8-live@GEMINI_TTS_MODEL=gemini-3.8-flash-tts@NANO_BANANA_MODEL=gemini-3.1-flash-image"
```

Capture the public URL and align `CORS_ORIGINS` (safe same-origin setting even if an external tab or Swagger hits the API):

```bash
SERVICE_URL=$(gcloud run services describe fixsaathi --region "$REGION" --format="value(status.url)")
gcloud run services update fixsaathi --region "$REGION" --update-env-vars "CORS_ORIGINS=$SERVICE_URL"
echo "Public URL: $SERVICE_URL"
```

---

## 6. Verify Live Public Deployment

```bash
curl -fsS "$SERVICE_URL/health"
python backend/scripts/smoke_live.py --base-url "$SERVICE_URL"
```

---

## 7. After the Demo: Scale to Zero

```bash
gcloud run services update fixsaathi --region "$REGION" --min-instances 0
```
