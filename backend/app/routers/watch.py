"""
Executive Watch Mode — the flagship autonomous feature.

Three ways a workflow starts with zero manual "Generate" click:

  1. Cloud Scheduler hits POST /api/watch/scheduled-tick on a cron
     (deploy/setup_gcp.sh provisions this — e.g. every 15 min for health
     checks, daily for the CEO morning brief, weekly/monthly for strategic
     and board reviews, each as its own Scheduler job hitting this same
     endpoint with a different `job` query param so the timeline records
     which cadence fired it).
  2. A document lands -> POST /api/watch/report-uploaded (wired to whatever
     upload UI/action calls it — replaces the old "press Generate" flow).
  3. An operator manually arms/disarms the loop from the Executive Watch
     page; this never blocks autonomous triggers 1-2, it only gates the
     in-process 5-minute reminder tick used when Cloud Scheduler isn't
     configured yet (e.g. first local run before `deploy/setup_gcp.sh`).

Every trigger here starts a new workflow_id and publishes the first event;
from that point on, propagation through Finance -> Risk -> Strategy ->
CEO Brief is entirely agent-to-agent via Pub/Sub (see events/topics.py).
"""
import uuid
from fastapi import APIRouter, Header, HTTPException

from ..platform.gcp_config import gcp_settings
from ..platform.pubsub_bus import publish
from ..platform import firestore_memory as memory
from ..events.topics import Topic, EventEnvelope

router = APIRouter(prefix="/api/watch", tags=["watch"])


def _check_scheduler_secret(x_scheduler_token: str | None) -> None:
    if not gcp_settings.SCHEDULER_SHARED_SECRET:
        return  # not configured — rely on Cloud Run's OIDC invoker check alone
    if x_scheduler_token != gcp_settings.SCHEDULER_SHARED_SECRET:
        raise HTTPException(status_code=403, detail="Invalid scheduler token")


@router.get("/status")
def status():
    state = memory.get_platform_state("executive_watch", default={"enabled": gcp_settings.EXEC_WATCH_ENABLED})
    return {
        "enabled": state.get("enabled", gcp_settings.EXEC_WATCH_ENABLED),
        "interval_seconds": gcp_settings.EXEC_WATCH_INTERVAL_SECONDS,
        "last_tick_at": state.get("last_tick_at"),
        "last_tick_job": state.get("last_tick_job"),
        "pubsub_live": gcp_settings.configured() and gcp_settings.PUBSUB_ENABLED,
    }


@router.post("/toggle")
def toggle(enabled: bool):
    memory.set_platform_state("executive_watch", {"enabled": enabled})
    return {"enabled": enabled}


@router.post("/scheduled-tick")
async def scheduled_tick(job: str = "health-check", x_scheduler_token: str | None = Header(default=None)):
    """Cloud Scheduler target. `job` distinguishes cadences (health-check,
    daily-brief, weekly-review, monthly-board-report) that all fan into the
    same SCHEDULED_TICK topic but are recorded distinctly on the timeline."""
    _check_scheduler_secret(x_scheduler_token)
    state = memory.get_platform_state("executive_watch", default={"enabled": gcp_settings.EXEC_WATCH_ENABLED})
    if not state.get("enabled", gcp_settings.EXEC_WATCH_ENABLED):
        return {"status": "skipped", "reason": "executive watch mode disabled"}

    workflow_id = uuid.uuid4().hex
    event = EventEnvelope(topic=Topic.SCHEDULED_TICK, produced_by="cloud-scheduler",
                           workflow_id=workflow_id, payload={"job": job})
    memory.start_workflow(workflow_id, event.topic.value, event.event_id)
    memory.set_platform_state("executive_watch", {"last_tick_at": event.ts, "last_tick_job": job})
    await publish(event)
    return {"status": "dispatched", "workflow_id": workflow_id, "job": job}


@router.post("/report-uploaded")
async def report_uploaded(filename: str = "uploaded-report"):
    """Fired when a new business document lands. Kicks Finance + Compliance
    agents off in parallel, per TOPIC_SUBSCRIBERS in events/topics.py."""
    workflow_id = uuid.uuid4().hex
    event = EventEnvelope(topic=Topic.REPORT_UPLOADED, produced_by="upload-pipeline",
                           workflow_id=workflow_id, payload={"filename": filename})
    memory.start_workflow(workflow_id, event.topic.value, event.event_id)
    await publish(event)
    return {"status": "dispatched", "workflow_id": workflow_id}


@router.post("/board-meeting-approaching")
async def board_meeting_approaching(days_out: int = 7):
    workflow_id = uuid.uuid4().hex
    event = EventEnvelope(topic=Topic.BOARD_MEETING_APPROACHING, produced_by="calendar-integration",
                           workflow_id=workflow_id, payload={"days_out": days_out})
    memory.start_workflow(workflow_id, event.topic.value, event.event_id)
    await publish(event)
    return {"status": "dispatched", "workflow_id": workflow_id}
