#!/usr/bin/env bash
# Deploy FixSaathi to Cloud Run (asia-south1, Mumbai) with Firestore + Secret Manager.
# Usage: ./deploy.sh <PROJECT_ID> [ACCESS_CODE]
set -euo pipefail
PROJECT="${1:?Usage: ./deploy.sh <PROJECT_ID> [ACCESS_CODE]}"
CODE="${2:-}"
REGION=asia-south1
SERVICE=fixsaathi

gcloud config set project "$PROJECT"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com secretmanager.googleapis.com

# Firestore database (Native mode) in Mumbai, if not created yet.
gcloud firestore databases describe --database="(default)" >/dev/null 2>&1 || \
  gcloud firestore databases create --location="$REGION" --type=firestore-native

# Store the Gemini key in Secret Manager (reads GEMINI_API_KEY from your shell).
: "${GEMINI_API_KEY:?Run: export GEMINI_API_KEY=your_key   first}"
if gcloud secrets describe gemini-api-key >/dev/null 2>&1; then
  printf %s "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
else
  printf %s "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
fi

# Let the Cloud Run service account read the secret and use Firestore.
SA="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding gemini-api-key --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$SA" --role=roles/datastore.user >/dev/null

ENV="STORE=firestore,GOOGLE_CLOUD_PROJECT=$PROJECT"
[ -n "$CODE" ] && ENV="$ENV,ACCESS_CODE=$CODE"

# Long timeout + session affinity keep live WebSocket repair sessions stable.
gcloud run deploy "$SERVICE" --source . --region "$REGION" --allow-unauthenticated \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest --set-env-vars="$ENV" \
  --timeout=3600 --session-affinity --min-instances=1 --max-instances=10 --memory=1Gi --cpu=1

echo "Done. Technician app: $(gcloud run services describe $SERVICE --region $REGION --format='value(status.url)')"
echo "Manager dashboard:    add /dashboard to the URL"
