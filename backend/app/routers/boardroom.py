"""
Boardroom collaboration API — proposals/approvals, the live activity feed,
task tracking, and the workspace dashboard. This is the backend half of the
human-in-the-loop company-OS layer: department agents (agents/boardroom_agents.py)
never act directly, they call create_proposal(); everything here is either
reading that state or recording a human's decision on it.
"""
import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..platform import firestore_memory as memory
from ..platform.pubsub_bus import publish
from ..events.topics import Topic, EventEnvelope

router = APIRouter(prefix="/api/boardroom", tags=["boardroom"])


class LaunchRequest(BaseModel):
    goal: str
    role: str = "ceo"


class DecisionRequest(BaseModel):
    decision: str  # "approve" | "edit" | "reject" | a custom action like "reduce_budget"
    role: str
    edited_payload: dict | None = None


class TaskRequest(BaseModel):
    title: str
    owner: str
    department: str = "general"
    deadline: str | None = None
    kind: str = "task"


class DeadlineRequest(BaseModel):
    deadline: str


@router.post("/launch")
async def launch(req: LaunchRequest):
    """The CEO creates a product/initiative. This is the single entry point
    for the demo flow: Marketing + Engineering + HR all wake up in parallel
    (see TOPIC_SUBSCRIBERS[PROJECT_CREATED]) and each proposes something —
    nothing executes until a human approves it."""
    workflow_id = uuid.uuid4().hex
    event = EventEnvelope(topic=Topic.PROJECT_CREATED, produced_by=f"ceo:{req.role}",
                           workflow_id=workflow_id, payload={"goal": req.goal})
    memory.start_workflow(workflow_id, event.topic.value, event.event_id)
    memory.log_activity("CEO", "created product", req.goal, workflow_id, "#8B5CF6")
    await publish(event)
    return {"status": "dispatched", "workflow_id": workflow_id}


@router.get("/proposals")
def list_proposals(status: str = "pending"):
    return memory.list_proposals(status=status if status != "all" else None)


@router.post("/proposals/{proposal_id}/decision")
async def decide(proposal_id: str, req: DecisionRequest):
    proposal = memory.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Unknown proposal")
    if proposal["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Proposal already {proposal['status']}")

    updated = memory.decide_proposal(proposal_id, req.decision, req.role, req.edited_payload)
    memory.log_activity(req.role, f"{req.decision} \u2192 {proposal['agent']}", proposal["title"],
                         proposal["workflow_id"])

    # "approve" or "edit" (an approval with a modified payload) continues the
    # workflow by publishing whichever topic the proposing agent asked for.
    # "reject" or any other custom action (e.g. "reduce_budget") ends this
    # branch — the human's decision is recorded, but nothing further fires
    # automatically, by design.
    next_topic_name = proposal["payload"].get("_next_topic")
    if req.decision in ("approve", "edit") and next_topic_name:
        payload = req.edited_payload or proposal["payload"]
        await publish(EventEnvelope(
            topic=Topic(next_topic_name), produced_by=proposal["agent"],
            workflow_id=proposal["workflow_id"], payload=payload,
        ))
    return {"status": "ok", "proposal": updated}


@router.get("/activity")
def activity(limit: int = 60):
    return memory.list_activity(limit=limit)


@router.get("/workflows")
def recent_workflows(limit: int = 10):
    """Distinct workflow ids recently active in the Boardroom mesh, most
    recent first — used by the frontend to auto-select which conversation
    thread to display."""
    proposals = memory.list_proposals(status=None, limit=200)
    seen: dict[str, str] = {}
    for p in proposals:
        seen.setdefault(p["workflow_id"], p["created_at"])
    ordered = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)
    return [{"workflow_id": wf, "started_at": ts} for wf, ts in ordered[:limit]]


@router.get("/conversation/{workflow_id}")
def conversation(workflow_id: str):
    """Renders one workflow's real proposals + decisions + activity as an
    ordered conversation thread — chat bubbles are a presentation of actual
    agent output and human decisions, not a separately-generated transcript.
    Each message is {speaker, text, kind, ts}."""
    proposals = [p for p in memory.list_proposals(status=None, limit=200) if p["workflow_id"] == workflow_id]
    acts = [a for a in memory.list_activity(limit=200) if a.get("workflow_id") == workflow_id]

    messages = []
    for p in proposals:
        messages.append({"speaker": p["agent"], "text": p["body"], "kind": "proposal", "ts": p["created_at"]})
        if p["status"] not in ("pending",):
            messages.append({
                "speaker": p.get("decided_by") or "human", "kind": "decision",
                "text": f"{p['status'].replace('_', ' ')} \u2014 \u201c{p['title']}\u201d",
                "ts": p.get("decided_at", p["created_at"]),
            })
    for a in acts:
        if a["verb"] in ("proposed",) or "\u2192" in a["verb"]:
            continue  # already represented by the proposal/decision messages above
        messages.append({"speaker": a["agent"], "text": f"{a['verb']}: {a['detail']}", "kind": "activity", "ts": a["ts"]})

    messages.sort(key=lambda m: m["ts"])
    return {"workflow_id": workflow_id, "messages": messages}


@router.get("/tasks")
def tasks(status: str | None = None):
    return memory.list_tasks(status=status)


@router.post("/tasks")
def create_task(req: TaskRequest):
    task_id = memory.create_task(req.title, req.owner, req.department, req.deadline, kind=req.kind)
    memory.log_activity(req.owner, "created task", req.title)
    return {"status": "ok", "task_id": task_id}


@router.post("/tasks/{task_id}/complete")
def finish_task(task_id: str):
    memory.complete_task(task_id)
    memory.log_activity("system", "completed task", task_id)
    return {"status": "ok"}


@router.post("/tasks/{task_id}/deadline")
def set_deadline(task_id: str, req: DeadlineRequest):
    memory.update_task_deadline(task_id, req.deadline)
    memory.log_activity("system", "updated deadline", f"{task_id} -> {req.deadline}")
    return {"status": "ok"}


@router.get("/dashboard")
def dashboard():
    """Company Health Score, Budget, Sprint Progress, Campaign Status,
    Active AI Agents, Pending Human Approvals, Recent Decisions, Upcoming
    Milestones — all derived transparently from proposals/tasks/activity
    already recorded, not fabricated numbers."""
    proposals = memory.list_proposals(status=None, limit=200)
    pending = [p for p in proposals if p["status"] == "pending"]
    decided = [p for p in proposals if p["status"] not in ("pending",)]
    tasks_ = memory.list_tasks(limit=200)
    open_tasks = [t for t in tasks_ if t["status"] == "open"]
    done_tasks = [t for t in tasks_ if t["status"] == "complete"]
    sprint_progress = round(100 * len(done_tasks) / len(tasks_), 1) if tasks_ else 0.0

    budget_proposals = [p for p in proposals if p["kind"] == "budget_review"]
    budget_status = "over_budget" if any(p["status"] == "pending" for p in budget_proposals) else "on_track"

    campaign_proposals = [p for p in proposals if p["kind"] == "campaign_strategy"]
    design_proposals = [p for p in proposals if p["kind"] == "design_concepts"]
    if any(p["status"] == "pending" for p in campaign_proposals + design_proposals):
        campaign_status = "pending_approval"
    elif any(p["status"] in ("approve", "edit") for p in design_proposals):
        campaign_status = "launched"
    elif campaign_proposals:
        campaign_status = "in_review"
    else:
        campaign_status = "not_started"

    rejected = sum(1 for p in decided if p["status"] == "reject")
    approved = sum(1 for p in decided if p["status"] in ("approve", "edit"))
    # Health score: simple, explainable blend — not a black-box number.
    health_score = round(max(0, min(100, 70 + approved * 4 - rejected * 6 - len(pending) * 2)), 0)

    agents = memory.list_agents()

    return {
        "company_health_score": health_score,
        "budget_status": budget_status,
        "sprint_progress_pct": sprint_progress,
        "campaign_status": campaign_status,
        "active_agents": len([a for a in agents if a.get("status") == "running"]),
        "total_agents": len(agents),
        "pending_approvals": len(pending),
        "recent_decisions": decided[:5],
        "upcoming_milestones": [t for t in open_tasks if t.get("deadline")][:5],
    }
