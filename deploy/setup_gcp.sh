#!/usr/bin/env bash
#
# One-time (and safely re-runnable) setup for BoardMind's GCP project:
# enables APIs, creates service accounts + IAM bindings, an Artifact
# Registry repo, deploys backend then frontend to Cloud Run, provisions
# Pub/Sub topics/push-subscriptions (via the backend's own
# ensure_infrastructure() admin call), and creates the Cloud Scheduler jobs
# that drive Executive Watch Mode.
#
# Usage:
#   export GOOGLE_CLOUD_PROJECT=your-project-id
#   export REGION=us-central1            # optional, defaults below
#   ./deploy/setup_gcp.sh
#
# Requires: gcloud CLI authenticated (`gcloud auth login`) with
# Owner/Editor on the target project, and docker.

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT first}"
REGION="${REGION:-us-central1}"
REPO="${ARTIFACT_REPO:-boardmind}"
BACKEND_SA="boardmind-backend@${PROJECT_ID}.iam.gserviceaccount.com"
PUBSUB_SA="boardmind-pubsub-invoker@${PROJECT_ID}.iam.gserviceaccount.com"
SCHEDULER_SA="boardmind-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Project:    ${PROJECT_ID}"
echo "==> Region:     ${REGION}"
gcloud config set project "${PROJECT_ID}" >/dev/null

echo "==> Enabling required APIs (idempotent)"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  cloudscheduler.googleapis.com \
  aiplatform.googleapis.com \
  logging.googleapis.com \
  iam.googleapis.com

echo "==> Artifact Registry repo"
gcloud artifacts repositories describe "${REPO}" --location="${REGION}" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "${REPO}" --repository-format=docker --location="${REGION}" \
    --description="BoardMind container images"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "==> Firestore (native mode) — no-op if already provisioned"
gcloud firestore databases describe --database="(default)" >/dev/null 2>&1 || \
  gcloud firestore databases create --location="${REGION}" --type=firestore-native

echo "==> Service accounts"
for sa_email_var in "BACKEND_SA:boardmind-backend:Runs the BoardMind FastAPI + ADK agent service" \
                     "PUBSUB_SA:boardmind-pubsub-invoker:Identity Pub/Sub uses to push-invoke Cloud Run" \
                     "SCHEDULER_SA:boardmind-scheduler:Identity Cloud Scheduler uses to invoke Cloud Run"; do
  name="${sa_email_var#*:}"; name="${name%%:*}"
  desc="${sa_email_var##*:}"
  gcloud iam service-accounts describe "${name}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1 || \
    gcloud iam service-accounts create "${name}" --display-name="${desc}"
done

echo "==> IAM bindings (least privilege — read/write only what each agent needs)"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${BACKEND_SA}" \
  --role="roles/datastore.user" --condition=None >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${BACKEND_SA}" \
  --role="roles/pubsub.publisher" --condition=None >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${BACKEND_SA}" \
  --role="roles/pubsub.editor" --condition=None >/dev/null   # needed for ensure_infrastructure() to create topics/subs once
gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${BACKEND_SA}" \
  --role="roles/aiplatform.user" --condition=None >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${BACKEND_SA}" \
  --role="roles/logging.logWriter" --condition=None >/dev/null

echo "==> Deploying backend (first pass, so we know its URL for push subscriptions + frontend build)"
docker build -f backend/Dockerfile -t "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:bootstrap" .
docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:bootstrap"

gcloud run deploy boardmind-backend \
  --image="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:bootstrap" \
  --region="${REGION}" --platform=managed \
  --service-account="${BACKEND_SA}" \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=1,PUBSUB_ENABLED=1"

BACKEND_URL=$(gcloud run services describe boardmind-backend --region="${REGION}" --format='value(status.url)')
echo "==> Backend deployed at: ${BACKEND_URL}"

echo "==> Re-deploying backend with SERVICE_BASE_URL set (needed for Pub/Sub push + Scheduler targets)"
gcloud run deploy boardmind-backend \
  --image="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:bootstrap" \
  --region="${REGION}" --platform=managed \
  --service-account="${BACKEND_SA}" \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=1,PUBSUB_ENABLED=1,SERVICE_BASE_URL=${BACKEND_URL},PUBSUB_PUSH_AUDIENCE=${BACKEND_URL}"

echo "==> Allowing Pub/Sub + Scheduler service accounts to invoke the backend"
gcloud run services add-iam-policy-binding boardmind-backend --region="${REGION}" \
  --member="serviceAccount:${PUBSUB_SA}" --role="roles/run.invoker"
gcloud run services add-iam-policy-binding boardmind-backend --region="${REGION}" \
  --member="serviceAccount:${SCHEDULER_SA}" --role="roles/run.invoker"

# Pub/Sub's push-authentication service agent needs token-creator on the SA
# it signs push OIDC tokens as.
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
gcloud iam service-accounts add-iam-policy-binding "${PUBSUB_SA}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator"

echo "==> Provisioning Pub/Sub topics + push subscriptions (backend's own ensure_infrastructure())"
IDENTITY_TOKEN=$(gcloud auth print-identity-token --audiences="${BACKEND_URL}" 2>/dev/null || gcloud auth print-identity-token)
curl -sf -X POST "${BACKEND_URL}/api/admin/ensure-infrastructure" -H "Authorization: Bearer ${IDENTITY_TOKEN}" || \
  echo "  (skipped — see routers/admin.py; run manually if this endpoint isn't deployed yet)"

echo "==> Cloud Scheduler jobs driving Executive Watch Mode"
declare -A JOBS=(
  [boardmind-health-check]="*/15 * * * *:health-check"
  [boardmind-daily-brief]="0 8 * * *:daily-brief"
  [boardmind-weekly-review]="0 9 * * 1:weekly-review"
  [boardmind-monthly-board-report]="0 9 1 * *:monthly-board-report"
)
for job_name in "${!JOBS[@]}"; do
  cron="${JOBS[$job_name]%%:*}"
  job_param="${JOBS[$job_name]##*:}"
  gcloud scheduler jobs describe "${job_name}" --location="${REGION}" >/dev/null 2>&1 && \
    gcloud scheduler jobs delete "${job_name}" --location="${REGION}" --quiet
  gcloud scheduler jobs create http "${job_name}" \
    --location="${REGION}" --schedule="${cron}" \
    --uri="${BACKEND_URL}/api/watch/scheduled-tick?job=${job_param}" \
    --http-method=POST \
    --oidc-service-account-email="${SCHEDULER_SA}" \
    --oidc-token-audience="${BACKEND_URL}"
done

echo "==> Deploying frontend, pointed at the backend URL"
docker build -f frontend/Dockerfile --build-arg NEXT_PUBLIC_API_URL="${BACKEND_URL}" \
  -t "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:bootstrap" .
docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:bootstrap"
gcloud run deploy boardmind-frontend \
  --image="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:bootstrap" \
  --region="${REGION}" --platform=managed --allow-unauthenticated

FRONTEND_URL=$(gcloud run services describe boardmind-frontend --region="${REGION}" --format='value(status.url)')

echo ""
echo "================================================================"
echo " Done."
echo " Backend  (private, OIDC-invoked only): ${BACKEND_URL}"
echo " Frontend (public):                      ${FRONTEND_URL}"
echo ""
echo " Optional next step: enable Model Armor screening on top of the"
echo " built-in heuristic scanner in app/platform/security.py:"
echo "   gcloud model-armor templates create boardmind-default \\"
echo "     --location=${REGION} --project=${PROJECT_ID} \\"
echo "     --pi-and-jailbreak-filter-settings-enforcement=enabled \\"
echo "     --pi-and-jailbreak-filter-settings-confidence-level=medium-and-above"
echo " then set MODEL_ARMOR_ENABLED=1 on the backend service."
echo "================================================================"
