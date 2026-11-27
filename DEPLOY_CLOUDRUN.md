# Deploy FixSaathi to Google Cloud Run (Single Service + Cloud SQL for PostgreSQL 16)

FixSaathi builds into one container image (`Dockerfile`): Vite compiles the React 19 frontend into `/app/web` (`VITE_API_BASE_URL=""` for same-origin API, SSE, and WebSocket calls), and FastAPI serves both the UI and API as non-root `USER app` on `$PORT` (`8080`), running idempotent Alembic migrations (`alembic upgrade head`) and seeding the 377 repair records (`ingest_knowledge.py --if-present`) on startup (`backend/scripts/render_start.sh`).

Secrets live **only** in Google Secret Manager — never in git, container images, or logs.

---

## 1. Set Project, Region & Enable APIs

```bash
export PROJECT_ID="geminisprints26blr-3820"
export REGION="us-east4"

gcloud auth login
gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com
```

---

## 2. Provision Cloud SQL (PostgreSQL 16)

```bash
# Demo instance in the same region as Cloud Run
gcloud sql instances create fixsaathi-db \
  --database-version=POSTGRES_16 \
  --edition=ENTERPRISE \
  --tier=db-f1-micro \
  --region="$REGION" \
  --storage-size=10GB \
  --quiet

gcloud sql databases create fixsaathi --instance=fixsaathi-db
```

Generate a random DB password without printing it, create the `fixsaathi` user, and store the Unix-socket `DATABASE_URL` directly in Secret Manager (`app/config.py` rewrites `postgresql://` -> `postgresql+psycopg://` while preserving `?host=/cloudsql/...`):

```bash
gcloud secrets create GEMINI_API_KEY --replication-policy="automatic" 2>/dev/null || true
gcloud secrets create SECRET_KEY --replication-policy="automatic" 2>/dev/null || true
gcloud secrets create DATABASE_URL --replication-policy="automatic" 2>/dev/null || true

# GEMINI_API_KEY (paste key cleanly without echoing, then press Ctrl+D)
gcloud secrets versions add GEMINI_API_KEY --data-file=-

# SECRET_KEY (generated via Python and piped directly)
python3 -c "import secrets, sys; sys.stdout.write(secrets.token_urlsafe(48))" \
  | gcloud secrets versions add SECRET_KEY --data-file=-

# Cloud SQL user + Secret Manager DATABASE_URL (Unix socket, URL-encoded password, zero terminal echo)
python3 -c '
import secrets, subprocess, urllib.parse
pw = secrets.token_urlsafe(24)
subprocess.run(["gcloud", "sql", "users", "create", "fixsaathi", "--instance=fixsaathi-db", f"--password={pw}", "--quiet"], check=True)
url = f"postgresql://fixsaathi:{urllib.parse.quote(pw, safe=\"\")}@/fixsaathi?host=/cloudsql/'"$PROJECT_ID"':'"$REGION"':fixsaathi-db"
subprocess.run(["gcloud", "secrets", "versions", "add", "DATABASE_URL", "--data-file=-"], input=url.encode(), check=True)
'
```

Grant Secret Manager and Cloud SQL client permissions to the Cloud Run runtime service account (`${PROJECT_NUMBER}-compute@developer.gserviceaccount.com`):

```bash
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for S in GEMINI_API_KEY SECRET_KEY DATABASE_URL; do
  gcloud secrets add-iam-policy-binding "$S" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
done

# Note: on GCP lab accounts where project-level setIamPolicy is restricted, ensure the
# compute service account already holds roles/editor or roles/cloudsql.client.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/cloudsql.client"
```

---

## 3. Deploy Single Service to Cloud Run

Uses `--add-cloudsql-instances` for Unix-socket access to `fixsaathi-db`, `STORAGE_PROVIDER=database` so uploaded technician photos persist across revisions, `--min-instances 1 --no-cpu-throttling --cpu-boost` for fast demo streaming, and `^@^` delimiter to preserve commas in `GEMINI_AGENT_FALLBACK_MODELS`. Migrations (`alembic upgrade head`) and the 377-record knowledge seed run automatically inside `render_start.sh` on startup.

```bash
gcloud run deploy fixsaathi \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --add-cloudsql-instances "${PROJECT_ID}:${REGION}:fixsaathi-db" \
  --min-instances 1 \
  --memory 1Gi \
  --timeout 300 \
  --no-cpu-throttling \
  --cpu-boost \
  --quiet \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest,SECRET_KEY=SECRET_KEY:latest,DATABASE_URL=DATABASE_URL:latest" \
  --set-env-vars "^@^APP_ENV=production@STORAGE_PROVIDER=database@VECTOR_SEARCH_MODE=auto@GEMINI_AGENT_MODEL=gemini-4-hydrogen@GEMINI_FAST_MODEL=gemini-3.5-flash-lite@GEMINI_AGENT_FALLBACK_MODELS=gemini-4-neon,gemini-3.5-flash-lite@GEMINI_THINKING_LEVEL=low@GEMINI_EMBED_MODEL=gemini-embedding-2@GEMINI_LIVE_MODEL=gemini-3.8-live@GEMINI_TTS_MODEL=gemini-3.8-flash-tts@NANO_BANANA_MODEL=gemini-3.1-flash-image"

SERVICE_URL=$(gcloud run services describe fixsaathi --region "$REGION" --format="value(status.url)")
gcloud run services update fixsaathi --region "$REGION" --update-env-vars "CORS_ORIGINS=$SERVICE_URL" --quiet
echo "Public URL: $SERVICE_URL"
```

*(Alternative: if using an external hosted PostgreSQL database instead of Cloud SQL, store its `DATABASE_URL` with `?sslmode=require` in Secret Manager and omit `--add-cloudsql-instances`.)*

---

## 4. Verify Live Public Deployment

```bash
curl -fsS "$SERVICE_URL/health"
python backend/scripts/smoke_live.py --base-url "$SERVICE_URL"
```

---

## 5. Safe Rollout (`--no-traffic`) & Rollback Target

- **Known good rollback revision:** `fixsaathi-00002-56b` (`https://fixsaathi-915991223959.us-east4.run.app`)
- **Emergency rollback command (100% instant traffic shift):**

```bash
gcloud run services update-traffic fixsaathi \
  --region us-east4 \
  --to-revisions fixsaathi-00002-56b=100
```

Deploy any change as an untagged/candidate revision with `--no-traffic`, verify `smoke_live.py` on its tagged URL first, and shift traffic only if every check passes:

```bash
gcloud run deploy fixsaathi \
  --source . \
  --region us-east4 \
  --no-traffic \
  --tag candidate \
  --quiet

CANDIDATE_URL="https://candidate---fixsaathi-915991223959.us-east4.run.app"
python backend/scripts/smoke_live.py --base-url "$CANDIDATE_URL"

# Shift 100% traffic only after smoke_live.py passes:
gcloud run services update-traffic fixsaathi --region us-east4 --to-latest
```

---

## 6. After the Demo: Scale to Zero

```bash
gcloud run services update fixsaathi --region "$REGION" --min-instances 0
```
