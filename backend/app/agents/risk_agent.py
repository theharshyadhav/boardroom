"""
Risk Agent — operational + financial risk scoring, historical risk profile.

Wakes on FINANCIAL_ALERT, MARKET_CHANGE, and COMPLIANCE_WARNING. Maintains a
running risk score in Firestore memory (kind="risk_profile") so each new
score is contextualized against the agent's own history rather than
computed from scratch every time.
"""
from ..events.topics import Topic, EventEnvelope
from ..platform import firestore_memory as memory
from .base import BaseEnterpriseAgent, AgentContext

RISK_ESCALATION_THRESHOLD = 70  # 0-100 scale


class RiskAgent(BaseEnterpriseAgent):
    name = "risk_agent"
    version = "1.0.0"
    description = "Operational and financial risk scoring with a persistent historical risk profile."
    capabilities = ["risk_scoring", "predictive_risk", "risk_history"]
    permissions = ["read:agent_memory", "write:agent_memory"]
    subscribes_to = [Topic.FINANCIAL_ALERT, Topic.MARKET_CHANGE, Topic.COMPLIANCE_WARNING]
    instruction = (
        "You are BoardMind's Risk Agent. Given a triggering signal and the organization's "
        "risk history, produce an updated risk score from 0-100 (state it as 'RISK_SCORE: N' "
        "on its own line) and a two-sentence justification referencing the historical trend "
        "if one exists."
    )

    def build_context(self, event: EventEnvelope) -> AgentContext:
        history = memory.recall(self.name, kind="risk_profile", limit=10)
        last_score = history[0]["data"].get("score", 40) if history else 40
        return AgentContext(
            triggering_topic=event.topic.value,
            triggering_payload=event.payload,
            last_risk_score=last_score,
            risk_history=[{"score": h["data"].get("score"), "at": h["created_at"]} for h in history],
        )

    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        score = self._extract_score(model_output, fallback=context["last_risk_score"])
        memory.remember(self.name, kind="risk_profile", summary=model_output[:300],
                         data={"score": score, "trigger": event.topic.value}, workflow_id=event.workflow_id)

        downstream = [EventEnvelope(
            topic=Topic.RISK_SCORE_CHANGED, produced_by=self.name,
            payload={"score": score, "previous_score": context["last_risk_score"], "summary": model_output[:500]},
        )]
        if score >= RISK_ESCALATION_THRESHOLD:
            memory.raise_alert(severity="high", title=f"Risk score escalated to {score}",
                                body=model_output, agent=self.name, workflow_id=event.workflow_id)
        return downstream

    @staticmethod
    def _extract_score(text: str, fallback: float) -> float:
        for line in text.splitlines():
            if "RISK_SCORE" in line.upper():
                digits = "".join(ch for ch in line if ch.isdigit())
                if digits:
                    return min(100, max(0, int(digits[:3])))
        return fallback
