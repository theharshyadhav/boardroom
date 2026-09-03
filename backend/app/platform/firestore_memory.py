"""
Firestore-backed long-term memory for every agent.

Schema (all under a single Firestore database, native mode):

  agents/{agent_name}
      name, version, description, capabilities[], permissions[],
      status, health, last_execution_ts, execution_count,
      avg_runtime_ms, memory_entry_count, updated_at

  agents/{agent_name}/memory/{memory_id}
      kind            "report" | "recommendation" | "feedback" | "kpi_snapshot"
                       | "risk_profile" | "market_signal" | "board_decision"
      summary         short human-readable text (shown in Memory Viewer)
      data            arbitrary JSON payload
      workflow_id     ties it back to the Execution Timeline
      created_at

  workflows/{workflow_id}
      root_event, root_topic, started_at, status
  workflows/{workflow_id}/steps/{step_id}
      agent, topic_in, topic_out, started_at, finished_at,
      duration_ms, status, reasoning_summary, error

  alerts/{alert_id}
      severity, title, body, agent, workflow_id, created_at, acknowledged

This module is the ONLY place in the codebase that talks to Firestore, so
every agent's persistence goes through the same audited path.
"""
from __future__ import annotations
import time
import uuid
import logging
from datetime import datetime, timezone

from .gcp_config import gcp_settings

logger = logging.getLogger("boardmind.firestore")

_client = None
_local_store: dict[str, dict] = {}  # used only when Firestore isn't configured


def _get_client():
    global _client
    if _client is None:
        from google.cloud import firestore
        _client = firestore.Client(project=gcp_settings.PROJECT_ID or None,
                                    database=gcp_settings.FIRESTORE_DATABASE)
    return _client


def _live() -> bool:
    return gcp_settings.configured()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Agent registry documents
# --------------------------------------------------------------------------

def upsert_agent_metadata(agent_name: str, fields: dict) -> None:
    fields = {**fields, "updated_at": _now()}
    if not _live():
        _local_store.setdefault(f"agents/{agent_name}", {}).update(fields)
        return
    _get_client().collection("agents").document(agent_name).set(fields, merge=True)


def record_execution(agent_name: str, duration_ms: float, status: str) -> None:
    """Called by BaseADKAgent after every run to keep registry stats live."""
    if not _live():
        doc = _local_store.setdefault(f"agents/{agent_name}", {})
        count = doc.get("execution_count", 0) + 1
        avg = ((doc.get("avg_runtime_ms", 0) * (count - 1)) + duration_ms) / count
        doc.update({
            "execution_count": count, "avg_runtime_ms": round(avg, 1),
            "last_execution_ts": _now(), "status": status, "health": "healthy" if status == "success" else "degraded",
        })
        return

    client = _get_client()
    ref = client.collection("agents").document(agent_name)

    @client.transactional
    def _txn(transaction):
        snap = ref.get(transaction=transaction)
        current = snap.to_dict() or {}
        count = current.get("execution_count", 0) + 1
        avg = ((current.get("avg_runtime_ms", 0) * (count - 1)) + duration_ms) / count
        transaction.set(ref, {
            "execution_count": count, "avg_runtime_ms": round(avg, 1),
            "last_execution_ts": _now(), "status": status,
            "health": "healthy" if status == "success" else "degraded",
            "updated_at": _now(),
        }, merge=True)

    _txn(client.transaction())


def list_agents() -> list[dict]:
    if not _live():
        return [{"name": k.split("/")[1], **v} for k, v in _local_store.items() if k.startswith("agents/") and "/memory/" not in k]
    docs = _get_client().collection("agents").stream()
    return [{"name": d.id, **(d.to_dict() or {})} for d in docs]


# --------------------------------------------------------------------------
# Per-agent long-term memory
# --------------------------------------------------------------------------

def remember(agent_name: str, kind: str, summary: str, data: dict, workflow_id: str | None = None) -> str:
    memory_id = uuid.uuid4().hex
    entry = {"kind": kind, "summary": summary, "data": data,
              "workflow_id": workflow_id, "created_at": _now()}
    if not _live():
        _local_store[f"agents/{agent_name}/memory/{memory_id}"] = entry
        return memory_id
    (_get_client().collection("agents").document(agent_name)
        .collection("memory").document(memory_id).set(entry))
    return memory_id


def recall(agent_name: str, kind: str | None = None, limit: int = 25) -> list[dict]:
    """Fetch this agent's most recent memories, optionally filtered by kind.
    This is what makes an agent's next run informed by its history instead
    of starting from a blank slate every time."""
    if not _live():
        items = [{"id": k.split("/")[-1], **v} for k, v in _local_store.items()
                  if k.startswith(f"agents/{agent_name}/memory/")]
        if kind:
            items = [i for i in items if i.get("kind") == kind]
        return sorted(items, key=lambda i: i["created_at"], reverse=True)[:limit]

    col = _get_client().collection("agents").document(agent_name).collection("memory")
    q = col.where("kind", "==", kind) if kind else col
    docs = q.order_by("created_at", direction="DESCENDING").limit(limit).stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]


# --------------------------------------------------------------------------
# Workflow / execution timeline
# --------------------------------------------------------------------------

def start_workflow(workflow_id: str, root_topic: str, root_event_id: str) -> None:
    doc = {"root_topic": root_topic, "root_event": root_event_id, "started_at": _now(), "status": "running"}
    if not _live():
        _local_store[f"workflows/{workflow_id}"] = doc
        return
    _get_client().collection("workflows").document(workflow_id).set(doc, merge=True)


def log_step(workflow_id: str, agent: str, topic_in: str, topic_out: str | None,
             duration_ms: float, status: str, reasoning_summary: str, error: str | None = None) -> None:
    step_id = uuid.uuid4().hex
    step = {"agent": agent, "topic_in": topic_in, "topic_out": topic_out,
            "duration_ms": duration_ms, "status": status,
            "reasoning_summary": reasoning_summary, "error": error, "ts": _now()}
    if not _live():
        _local_store[f"workflows/{workflow_id}/steps/{step_id}"] = step
        return
    (_get_client().collection("workflows").document(workflow_id)
        .collection("steps").document(step_id).set(step))


def get_timeline(workflow_id: str) -> dict:
    if not _live():
        wf = _local_store.get(f"workflows/{workflow_id}", {})
        steps = sorted(
            [v for k, v in _local_store.items() if k.startswith(f"workflows/{workflow_id}/steps/")],
            key=lambda s: s["ts"],
        )
        return {**wf, "workflow_id": workflow_id, "steps": steps}
    client = _get_client()
    wf_doc = client.collection("workflows").document(workflow_id).get()
    steps = client.collection("workflows").document(workflow_id).collection("steps").order_by("ts").stream()
    return {**(wf_doc.to_dict() or {}), "workflow_id": workflow_id,
            "steps": [s.to_dict() for s in steps]}


def list_recent_workflows(limit: int = 20) -> list[dict]:
    if not _live():
        wfs = [{"workflow_id": k.split("/")[1], **v} for k, v in _local_store.items()
               if k.startswith("workflows/") and "/steps/" not in k]
        return sorted(wfs, key=lambda w: w["started_at"], reverse=True)[:limit]
    docs = (_get_client().collection("workflows")
            .order_by("started_at", direction="DESCENDING").limit(limit).stream())
    return [{"workflow_id": d.id, **(d.to_dict() or {})} for d in docs]


# --------------------------------------------------------------------------
# Executive alerts
# --------------------------------------------------------------------------

def raise_alert(severity: str, title: str, body: str, agent: str, workflow_id: str | None = None) -> str:
    alert_id = uuid.uuid4().hex
    alert = {"severity": severity, "title": title, "body": body, "agent": agent,
              "workflow_id": workflow_id, "created_at": _now(), "acknowledged": False}
    if not _live():
        _local_store[f"alerts/{alert_id}"] = alert
        return alert_id
    _get_client().collection("alerts").document(alert_id).set(alert)
    return alert_id


def list_alerts(unacknowledged_only: bool = False, limit: int = 50) -> list[dict]:
    if not _live():
        items = [{"id": k.split("/")[1], **v} for k, v in _local_store.items() if k.startswith("alerts/")]
        if unacknowledged_only:
            items = [i for i in items if not i["acknowledged"]]
        return sorted(items, key=lambda i: i["created_at"], reverse=True)[:limit]
    col = _get_client().collection("alerts")
    q = col.where("acknowledged", "==", False) if unacknowledged_only else col
    docs = q.order_by("created_at", direction="DESCENDING").limit(limit).stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]


# --------------------------------------------------------------------------
# Small platform-wide config doc (Executive Watch Mode on/off, last tick, ...)
# --------------------------------------------------------------------------

def get_platform_state(key: str, default: dict | None = None) -> dict:
    if not _live():
        return _local_store.get(f"platform_state/{key}", default or {})
    doc = _get_client().collection("platform_state").document(key).get()
    return doc.to_dict() if doc.exists else (default or {})


def set_platform_state(key: str, fields: dict) -> None:
    fields = {**fields, "updated_at": _now()}
    if not _live():
        _local_store.setdefault(f"platform_state/{key}", {}).update(fields)
        return
    _get_client().collection("platform_state").document(key).set(fields, merge=True)


def acknowledge_alert(alert_id: str) -> None:
    if not _live():
        _local_store.get(f"alerts/{alert_id}", {})["acknowledged"] = True
        return
    _get_client().collection("alerts").document(alert_id).set({"acknowledged": True}, merge=True)


# --------------------------------------------------------------------------
# Proposals — the human-approval primitive for the Boardroom collaboration
# layer. A department agent that wants to take a consequential action
# (spend budget, publish a campaign, ship a design) does not act directly:
# it calls create_proposal(). A human decides via decide_proposal(), and
# only an "approve" (or "edit", which approves a modified payload) causes
# the caller to actually publish the downstream event that lets the mesh
# continue. "reject" ends that branch of the workflow.
# --------------------------------------------------------------------------

def create_proposal(agent: str, kind: str, title: str, body: str, payload: dict,
                     actions: list[str], workflow_id: str) -> str:
    proposal_id = uuid.uuid4().hex
    doc = {
        "agent": agent, "kind": kind, "title": title, "body": body, "payload": payload,
        "actions": actions,           # e.g. ["approve", "edit", "reject"] or ["reduce_budget"]
        "status": "pending", "decision": None, "decided_by": None, "decided_payload": None,
        "workflow_id": workflow_id, "created_at": _now(),
    }
    if not _live():
        _local_store[f"proposals/{proposal_id}"] = doc
        return proposal_id
    _get_client().collection("proposals").document(proposal_id).set(doc)
    return proposal_id


def decide_proposal(proposal_id: str, decision: str, role: str, edited_payload: dict | None = None) -> dict:
    fields = {"status": decision, "decision": decision, "decided_by": role,
              "decided_payload": edited_payload, "decided_at": _now()}
    if not _live():
        doc = _local_store.setdefault(f"proposals/{proposal_id}", {})
        doc.update(fields)
        return doc
    ref = _get_client().collection("proposals").document(proposal_id)
    ref.set(fields, merge=True)
    return ref.get().to_dict() or {}


def get_proposal(proposal_id: str) -> dict | None:
    if not _live():
        return _local_store.get(f"proposals/{proposal_id}")
    doc = _get_client().collection("proposals").document(proposal_id).get()
    return doc.to_dict() if doc.exists else None


def list_proposals(status: str | None = None, limit: int = 50) -> list[dict]:
    if not _live():
        items = [{"id": k.split("/")[1], **v} for k, v in _local_store.items() if k.startswith("proposals/")]
        if status:
            items = [i for i in items if i.get("status") == status]
        return sorted(items, key=lambda i: i["created_at"], reverse=True)[:limit]
    col = _get_client().collection("proposals")
    q = col.where("status", "==", status) if status else col
    docs = q.order_by("created_at", direction="DESCENDING").limit(limit).stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]


# --------------------------------------------------------------------------
# Activity feed — a flattened, human-readable merge of workflow steps,
# proposal creation, and proposal decisions, sorted by time. This is what
# powers the live "Marketing Agent requested landing page / Design Agent
# generated version A / Finance rejected..." collaboration feed.
# --------------------------------------------------------------------------

def log_activity(agent: str, verb: str, detail: str, workflow_id: str | None = None,
                  department_color: str | None = None) -> str:
    activity_id = uuid.uuid4().hex
    entry = {"agent": agent, "verb": verb, "detail": detail, "workflow_id": workflow_id,
              "department_color": department_color, "ts": _now()}
    if not _live():
        _local_store[f"activity/{activity_id}"] = entry
        return activity_id
    _get_client().collection("activity").document(activity_id).set(entry)
    return activity_id


def list_activity(limit: int = 60) -> list[dict]:
    if not _live():
        items = [v for k, v in _local_store.items() if k.startswith("activity/")]
        return sorted(items, key=lambda i: i["ts"], reverse=True)[:limit]
    docs = (_get_client().collection("activity")
            .order_by("ts", direction="DESCENDING").limit(limit).stream())
    return [d.to_dict() for d in docs]


# --------------------------------------------------------------------------
# Lightweight task tracking backing the WebMCP assign_task/create_sprint/
# complete_task/update_deadline tools.
# --------------------------------------------------------------------------

def create_task(title: str, owner: str, department: str, deadline: str | None,
                 workflow_id: str | None = None, kind: str = "task") -> str:
    task_id = uuid.uuid4().hex
    doc = {"title": title, "owner": owner, "department": department, "deadline": deadline,
            "kind": kind, "status": "open", "workflow_id": workflow_id, "created_at": _now()}
    if not _live():
        _local_store[f"tasks/{task_id}"] = doc
        return task_id
    _get_client().collection("tasks").document(task_id).set(doc)
    return task_id


def complete_task(task_id: str) -> None:
    if not _live():
        _local_store.get(f"tasks/{task_id}", {})["status"] = "complete"
        return
    _get_client().collection("tasks").document(task_id).set({"status": "complete"}, merge=True)


def update_task_deadline(task_id: str, deadline: str) -> None:
    if not _live():
        _local_store.get(f"tasks/{task_id}", {})["deadline"] = deadline
        return
    _get_client().collection("tasks").document(task_id).set({"deadline": deadline}, merge=True)


def list_tasks(status: str | None = None, limit: int = 100) -> list[dict]:
    if not _live():
        items = [{"id": k.split("/")[1], **v} for k, v in _local_store.items() if k.startswith("tasks/")]
        if status:
            items = [i for i in items if i.get("status") == status]
        return sorted(items, key=lambda i: i["created_at"], reverse=True)[:limit]
    col = _get_client().collection("tasks")
    q = col.where("status", "==", status) if status else col
    docs = q.order_by("created_at", direction="DESCENDING").limit(limit).stream()
    return [{"id": d.id, **(d.to_dict() or {})} for d in docs]
