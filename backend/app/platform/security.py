"""
Enterprise security layer sitting in front of every agent invocation.

Four controls, each real and independently testable (see backend/tests):

1. Prompt-injection detection   — heuristic pre-filter on any text an agent
   is about to hand to Gemini as untrusted input (uploaded docs, news
   snippets, user questions). Pattern-based, not a silver bullet — flagged
   content is logged and down-weighted, not silently executed as
   instructions.
2. PII detection                — regex-based scan (emails, phone numbers,
   card-like numbers, SSN-shaped numbers) used to redact before anything
   is persisted to Firestore memory or sent to an external LLM call.
3. Role-based access control    — maps the existing `roles.py` role model
   onto per-agent-tool permissions, enforced in agents/base.py before a
   tool executes.
4. Audit log                    — every security decision (allowed, denied,
   redacted, flagged) is written to Firestore `audit_log` so the platform
   has a durable, queryable trail. This is intentionally separate from the
   observability execution log — one is "what ran", this is "what was
   allowed to run and why."

`Model Armor` note: Google Cloud's Model Armor service (prompt-injection /
jailbreak / sensitive-data screening for Vertex AI traffic) is the
production-grade version of controls 1-2. It's referenced in
deploy/setup_gcp.sh as an optional `gcloud model-armor templates create`
step gated behind MODEL_ARMOR_ENABLED, since enabling it requires a
security-admin-provisioned template, and it should not be silently
simulated as if it were active by default.
"""
from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone

from .gcp_config import gcp_settings

_PROMPT_INJECTION_PATTERNS = [
    r"ignore (all|any|previous|prior) instructions",
    r"disregard (the|your) (system|previous) prompt",
    r"you are now (in )?(developer|debug|dan) mode",
    r"reveal (your|the) (system prompt|instructions)",
    r"act as if you (have no|had no) (restrictions|rules)",
    r"</?(system|assistant|user)>",
    r"BEGIN\s+(NEW|OVERRIDE)\s+INSTRUCTIONS",
]
_PROMPT_INJECTION_RE = re.compile("|".join(_PROMPT_INJECTION_PATTERNS), re.IGNORECASE)

_PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ssn_like": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}


class SecurityFinding(dict):
    """Lightweight typed dict: {ok, flagged_patterns, redacted_text, pii_found}"""


def scan_untrusted_text(text: str) -> SecurityFinding:
    """Run prompt-injection + PII scanning on any text an agent is about to
    treat as untrusted context (uploaded file contents, scraped news,
    free-text user questions)."""
    injection_hit = _PROMPT_INJECTION_RE.search(text or "")
    pii_found = {name: bool(pattern.search(text or "")) for name, pattern in _PII_PATTERNS.items()}
    redacted = text or ""
    for name, pattern in _PII_PATTERNS.items():
        redacted = pattern.sub(f"[REDACTED_{name.upper()}]", redacted)

    finding = SecurityFinding(
        ok=not injection_hit,
        flagged_patterns=[injection_hit.group(0)] if injection_hit else [],
        pii_found=[k for k, v in pii_found.items() if v],
        redacted_text=redacted,
    )
    _audit(
        action="scan_untrusted_text",
        decision="flagged" if injection_hit else "allowed",
        detail={"pii_found": finding["pii_found"], "injection_match": bool(injection_hit)},
    )
    return finding


# --------------------------------------------------------------------------
# RBAC — reuses the existing role model in app/roles.py
# --------------------------------------------------------------------------

# Which roles may trigger which agent (used by routers/agents.py and
# routers/watch.py before allowing a manual "run now" action; autonomous
# Pub/Sub-triggered runs are always allowed since they originate from the
# platform itself, not an end user).
AGENT_TRIGGER_PERMISSIONS: dict[str, list[str]] = {
    "finance_agent": ["cfo", "ceo", "admin"],
    "risk_agent": ["cfo", "ceo", "admin", "risk_officer"],
    "market_intelligence_agent": ["cfo", "ceo", "admin", "strategy"],
    "compliance_agent": ["compliance_officer", "admin", "ceo"],
    "strategy_agent": ["ceo", "admin", "strategy"],
    "ceo_brief_agent": ["ceo", "admin"],
}


def authorize_agent_trigger(role: str, agent_name: str) -> bool:
    allowed_roles = AGENT_TRIGGER_PERMISSIONS.get(agent_name, [])
    decision = role in allowed_roles or role == "admin"
    _audit(action="authorize_agent_trigger", decision="allowed" if decision else "denied",
           detail={"role": role, "agent": agent_name})
    return decision


def validate_tool_permission(agent_name: str, tool_name: str, agent_permissions: list[str]) -> bool:
    """Tool permission validation: an ADK agent may only invoke tools it was
    explicitly granted in its registry entry (agents/registry.py)."""
    decision = tool_name in agent_permissions
    _audit(action="validate_tool_permission", decision="allowed" if decision else "denied",
           detail={"agent": agent_name, "tool": tool_name})
    return decision


# --------------------------------------------------------------------------
# Audit log
# --------------------------------------------------------------------------

def _audit(action: str, decision: str, detail: dict) -> None:
    from . import firestore_memory  # local import avoids a circular import
    entry = {
        "action": action, "decision": decision, "detail": detail,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if not gcp_settings.configured():
        firestore_memory._local_store[f"audit_log/{uuid.uuid4().hex}"] = entry
        return
    firestore_memory._get_client().collection("audit_log").document(uuid.uuid4().hex).set(entry)


def list_audit_log(limit: int = 100) -> list[dict]:
    from . import firestore_memory
    if not gcp_settings.configured():
        items = [v for k, v in firestore_memory._local_store.items() if k.startswith("audit_log/")]
        return sorted(items, key=lambda i: i["ts"], reverse=True)[:limit]
    docs = (firestore_memory._get_client().collection("audit_log")
            .order_by("ts", direction="DESCENDING").limit(limit).stream())
    return [d.to_dict() for d in docs]
