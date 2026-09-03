"""
CEO Brief Agent — the terminal node of every workflow. Turns whatever
upstream signal fired (financial, risk, market, compliance, or strategy)
into an executive-ready summary with concrete action items, then publishes
CEO_REPORT_READY, which the dashboard and notification center subscribe to
directly (no further agent hops).
"""
from ..events.topics import Topic, EventEnvelope
from ..platform import firestore_memory as memory
from .base import BaseEnterpriseAgent, AgentContext


class CEOBriefAgent(BaseEnterpriseAgent):
    name = "ceo_brief_agent"
    version = "1.0.0"
    description = "Executive summaries, board-ready reports, decision recommendations, action items."
    capabilities = ["executive_summary", "board_report", "action_items"]
    permissions = ["read:agent_memory", "write:agent_memory"]
    subscribes_to = [Topic.STRATEGY_UPDATED, Topic.RISK_SCORE_CHANGED,
                      Topic.COMPLIANCE_WARNING, Topic.BOARD_MEETING_APPROACHING]
    instruction = (
        "You are BoardMind's CEO Brief Agent. Given the latest strategy synthesis and "
        "the recent board-decision history, write a short executive brief: one headline "
        "sentence, the business impact, and exactly one recommended action item with an "
        "owner role (e.g. CFO, Head of Ops). Keep it under 120 words — this goes straight "
        "onto the executive dashboard."
    )

    def build_context(self, event: EventEnvelope) -> AgentContext:
        return AgentContext(
            latest_strategy=[m["summary"] for m in memory.recall("strategy_agent", kind="recommendation", limit=1)],
            triggering_event={"topic": event.topic.value, "payload": event.payload},
            past_board_decisions=[m["summary"] for m in memory.recall(self.name, kind="board_decision", limit=5)],
        )

    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        memory.remember(self.name, kind="board_decision", summary=model_output[:400], data=dict(context),
                         workflow_id=event.workflow_id)
        memory.raise_alert(severity="info", title="New executive brief ready",
                            body=model_output, agent=self.name, workflow_id=event.workflow_id)
        return [EventEnvelope(topic=Topic.CEO_REPORT_READY, produced_by=self.name,
                               payload={"brief": model_output})]
