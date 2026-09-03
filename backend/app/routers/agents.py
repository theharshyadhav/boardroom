"""
Agent Registry API — backs the frontend's /agents page (name, description,
version, capabilities, permissions, status, health, last execution,
execution count, average runtime, memory size).
"""
import uuid
from fastapi import APIRouter, HTTPException

from ..platform import firestore_memory as memory
from ..platform import security
from ..platform.pubsub_bus import publish
from ..events.topics import Topic, EventEnvelope
from ..schemas import AgentRunRequest

router = APIRouter(prefix="/api/agents", tags=["agents"])

_TOPIC_FOR_MANUAL_RUN = {
    "finance_agent": Topic.SCHEDULED_TICK,
    "risk_agent": Topic.FINANCIAL_ALERT,
    "market_intelligence_agent": Topic.SCHEDULED_TICK,
    "compliance_agent": Topic.REPORT_UPLOADED,
    "strategy_agent": Topic.FINANCIAL_ALERT,
    "ceo_brief_agent": Topic.STRATEGY_UPDATED,
}


@router.get("")
def list_agents():
    agents = memory.list_agents()
    for a in agents:
        a["memory_size"] = len(memory.recall(a["name"], limit=1000))
    return agents


@router.get("/{agent_name}")
def get_agent(agent_name: str):
    agents = {a["name"]: a for a in memory.list_agents()}
    if agent_name not in agents:
        raise HTTPException(status_code=404, detail="Unknown agent")
    detail = agents[agent_name]
    detail["recent_memory"] = memory.recall(agent_name, limit=15)
    return detail


@router.post("/{agent_name}/run")
def run_agent(agent_name: str, req: AgentRunRequest):
    if agent_name not in _TOPIC_FOR_MANUAL_RUN:
        raise HTTPException(status_code=404, detail="Unknown agent")
    if not security.authorize_agent_trigger(req.role, agent_name):
        raise HTTPException(status_code=403, detail=f"Role '{req.role}' is not permitted to trigger {agent_name}")

    event = EventEnvelope(
        topic=_TOPIC_FOR_MANUAL_RUN[agent_name],
        produced_by="manual-trigger",
        workflow_id=uuid.uuid4().hex,
        payload={"triggered_by_role": req.role, "manual": True},
    )
    memory.start_workflow(event.workflow_id, event.topic.value, event.event_id)
    import asyncio
    asyncio.create_task(publish(event))
    return {"status": "dispatched", "workflow_id": event.workflow_id, "topic": event.topic.value}
