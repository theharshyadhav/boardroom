"""
Compliance Agent — validates other agents' outputs, checks evidence,
detects hallucinations, enforces policy.

This is BoardMind's guardrail agent: it doesn't produce business analysis,
it audits the analysis other agents already produced. Wakes on
REPORT_UPLOADED to validate new source documents, and (via
AGENT_EXECUTION_COMPLETED, subscribed at the registry level) samples other
agents' recent memory to check claims are actually traceable to the
deterministic evidence graph already in evidence_graph.py rather than to
model-invented figures.
"""
from ..events.topics import Topic, EventEnvelope
from ..evidence_graph import build_source_freshness
from ..platform import firestore_memory as memory
from .base import BaseEnterpriseAgent, AgentContext


class ComplianceAgent(BaseEnterpriseAgent):
    name = "compliance_agent"
    version = "1.0.0"
    description = "Validates AI-generated outputs against evidence, flags hallucinations, enforces policy."
    capabilities = ["output_validation", "evidence_verification", "hallucination_detection", "policy_enforcement"]
    permissions = ["read:agent_memory", "write:agent_memory", "read:financial_data"]
    subscribes_to = [Topic.REPORT_UPLOADED]
    instruction = (
        "You are BoardMind's Compliance Agent. You are given a recent agent-generated "
        "report and the list of underlying evidence sources with their freshness. Check "
        "whether the report's claims are plausibly supported by sources that are actually "
        "fresh and available. Flag any claim that looks unsupported or that references a "
        "source not in the evidence list as a possible hallucination. Respond with either "
        "'VALIDATION: PASS' or 'VALIDATION: FLAGGED' on the first line, followed by your reasoning."
    )

    def build_context(self, event: EventEnvelope) -> AgentContext:
        recent_reports = memory.recall("finance_agent", kind="report", limit=1)
        sources = build_source_freshness()
        report_text = recent_reports[0]["summary"] if recent_reports else "(no recent finance report to validate)"
        return AgentContext(
            report_under_review={"_untrusted": True, "text": report_text},
            evidence_sources=[{"id": s["id"], "freshness_mins": s["freshnessMins"]} for s in sources],
            _untrusted_text_fields={"report_under_review": report_text},
        )

    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        flagged = model_output.strip().upper().startswith("VALIDATION: FLAGGED")
        memory.remember(self.name, kind="report", summary=model_output[:300],
                         data={"flagged": flagged}, workflow_id=event.workflow_id)
        if not flagged:
            return []
        memory.raise_alert(severity="medium", title="Compliance Agent flagged a possible hallucination",
                            body=model_output, agent=self.name, workflow_id=event.workflow_id)
        return [EventEnvelope(topic=Topic.COMPLIANCE_WARNING, produced_by=self.name,
                               payload={"summary": model_output[:500]})]
