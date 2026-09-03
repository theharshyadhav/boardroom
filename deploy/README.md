# Deploying BoardMind to Google Cloud

## Prerequisites
- A GCP project with billing enabled
- `gcloud` CLI authenticated: `gcloud auth login`
- Docker
- Vertex AI Gemini access enabled for the project (`gcloud services enable aiplatform.googleapis.com`, done by the script below)

## One-command setup + deploy

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export REGION=us-central1   # optional
./deploy/setup_gcp.sh
```

This is idempotent — re-running it after code changes redeploys both services with a fresh image; it won't recreate service accounts, topics, or IAM bindings that already exist.

What it does, in order:
1. Enables Cloud Run, Cloud Build, Artifact Registry, Firestore, Pub/Sub, Cloud Scheduler, Vertex AI, Cloud Logging APIs
2. Creates the Artifact Registry repo and three service accounts (`boardmind-backend`, `boardmind-pubsub-invoker`, `boardmind-scheduler`) with least-privilege IAM roles
3. Provisions Firestore in native mode
4. Deploys the backend to Cloud Run **twice** — once to learn its URL, once more with that URL baked in as `SERVICE_BASE_URL` (needed so Pub/Sub push subscriptions and Cloud Scheduler jobs know where to call back)
5. Grants the Pub/Sub and Scheduler service accounts `roles/run.invoker` on the backend, and grants Pub/Sub's push-auth service agent `roles/iam.serviceAccountTokenCreator` on the invoker SA (required for OIDC-signed push requests — see `app/routers/pubsub_push.py`)
6. Calls `/api/admin/ensure-infrastructure` (protected by Cloud Run's own IAM check, since the backend is `--no-allow-unauthenticated`) to create every Pub/Sub topic + push subscription in `app/events/topics.py`
7. Creates four Cloud Scheduler jobs hitting `/api/watch/scheduled-tick` on different cadences (health-check every 15 min, daily CEO brief, weekly strategic review, monthly board report)
8. Builds and deploys the frontend, pointed at the backend's URL

## Ongoing deploys (CI/CD)

`cloudbuild.yaml` at the repo root does steps 4 and 8 above via Cloud Build — wire it to a trigger on your repo:

```bash
gcloud builds triggers create github \
  --repo-name=<your-repo> --repo-owner=<you> --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml \
  --substitutions=_BACKEND_URL=$(gcloud run services describe boardmind-backend --region=$REGION --format='value(status.url)')
```

Run `./deploy/setup_gcp.sh` once first — Cloud Build's config assumes the service accounts, topics, and Scheduler jobs already exist.

## Local development against real GCP

```bash
cp backend/.env.example backend/.env   # fill in GOOGLE_CLOUD_PROJECT, etc.
gcloud auth application-default login
docker compose up --build
```

Note: Pub/Sub **push** subscriptions need a publicly reachable HTTPS endpoint, which `localhost` isn't. Locally, either:
- Leave `PUBSUB_ENABLED=0` and let events dispatch in-process (see `platform/pubsub_bus.py`'s fallback mode) — full app functionality, just not literally routed through Cloud Pub/Sub, or
- Tunnel your local backend (e.g. `cloudflared tunnel` or `ngrok http 8000`) and set `SERVICE_BASE_URL` to the tunnel URL before calling `/api/admin/ensure-infrastructure`, to test real push delivery end-to-end.

## Security notes
- The backend Cloud Run service is deployed **without** public access (`--no-allow-unauthenticated`). Only the frontend is public; it calls the backend server-side, or you can add Identity-Aware Proxy in front of the backend if you need direct external API access.
- Pub/Sub push requests are OIDC-verified in `app/routers/pubsub_push.py` — an endpoint that doesn't recognize the token's audience/issuer returns 401.
- Cloud Scheduler-triggered endpoints additionally check an optional shared secret (`SCHEDULER_SHARED_SECRET`) as defense in depth on top of Cloud Run's own IAM check.
- See `app/platform/security.py` for the prompt-injection/PII/RBAC/audit-log layer, and the Model Armor note at the end of `setup_gcp.sh`'s output for the production-grade upgrade path.
