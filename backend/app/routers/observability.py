"""
Enterprise Observability API — running/completed/failed agents, execution
timeline, Pub/Sub event trail, alerts, and the security audit log. Backs the
frontend's /observability and /timeline pages.

Token usage and latency are pulled from the existing llm_provider telemetry
(the same counters the current Telemetry page already reads) so the two
views stay consistent rather than tracking cost twice.
"""
from fastapi import APIRouter, HTTPException

from ..platform import firestore_memory as memory
from ..platform import security
from .. import llm_provider
from ..schemas import AlertAckRequest

router = APIRouter(prefix="/api/observability", tags=["observability"])


@router.get("/summary")
def summary():
    agents = memory.list_agents()
    running = sum(1 for a in agents if a.get("status") == "running")
    healthy = sum(1 for a in agents if a.get("health") == "healthy")
    total_executions = sum(a.get("execution_count", 0) for a in agents)
    workflows = memory.list_recent_workflows(limit=200)
    failed_workflows = sum(1 for w in workflows if w.get("status") == "error")
    return {
        "agents_total": len(agents),
        "agents_running": running,
        "agents_healthy": healthy,
        "total_executions": total_executions,
        "workflows_tracked": len(workflows),
        "failed_workflows": failed_workflows,
        "llm_telemetry": {
            "calls": llm_provider.TELEMETRY["calls"],
            "cache_hits": llm_provider.TELEMETRY["cache_hits"],
            "in_tokens": llm_provider.TELEMETRY["in_tokens"],
            "out_tokens": llm_provider.TELEMETRY["out_tokens"],
            "estimated_cost_usd": round(llm_provider.estimated_cost_usd(), 4),
        },
    }


@router.get("/workflows")
def workflows(limit: int = 20):
    return memory.list_recent_workflows(limit=limit)


@router.get("/workflows/{workflow_id}")
def workflow_timeline(workflow_id: str):
    timeline = memory.get_timeline(workflow_id)
    if not timeline.get("steps") and not timeline.get("root_topic"):
        raise HTTPException(status_code=404, detail="Unknown workflow")
    return timeline


@router.get("/alerts")
def alerts(unacknowledged_only: bool = False, limit: int = 50):
    return memory.list_alerts(unacknowledged_only=unacknowledged_only, limit=limit)


@router.post("/alerts/ack")
def ack_alert(req: AlertAckRequest):
    memory.acknowledge_alert(req.alertId)
    return {"status": "ok"}


@router.get("/audit-log")
def audit_log(limit: int = 100):
    return security.list_audit_log(limit=limit)
