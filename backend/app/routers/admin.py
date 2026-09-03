"""
Admin endpoints — not exposed publicly. The backend Cloud Run service is
deployed with `--no-allow-unauthenticated` (see deploy/setup_gcp.sh), so
these are already gated by Cloud Run's own IAM invoker check; only
principals granted roles/run.invoker (or Owner/Editor) can reach them at
all. No additional application-level auth is layered on top because Cloud
Run's check happens before a request reaches this process.
"""
from fastapi import APIRouter

from ..platform.pubsub_bus import ensure_infrastructure

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/ensure-infrastructure")
def admin_ensure_infrastructure():
    """Idempotently creates every Pub/Sub topic and push subscription this
    service needs (see events/topics.py for the full list). Safe to call
    repeatedly — deploy/setup_gcp.sh calls this once per deploy, right after
    the backend's Cloud Run URL is known."""
    return ensure_infrastructure()
