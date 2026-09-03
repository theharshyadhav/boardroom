"""
Strategy Agent — synthesizes every other agent's memory into recommendations
and strategic plans. This is the "combine outputs from every agent" node in
the mesh: it never talks to raw business data directly, only to what
Finance/Risk/Market/Compliance have already remembered.
"""
from ..events.topics import Topic, EventEnvelope
from ..recommendations import build_recommendations
from ..platform import firestore_memory as memory
from .base import BaseEnterpriseAgent, AgentContext


class StrategyAgent(BaseEnterpriseAgent):
    name = "strategy_agent"
    version = "1.0.0"
    description = "Synthesizes Finance/Risk/Market/Compliance signals into strategic recommendations."
    capabilities = ["cross_agent_synthesis", "strategic_planning", "opportunity_identification"]
    permissions = ["read:agent_memory", "write:agent_memory"]
    subscribes_to = [Topic.FINANCIAL_ALERT, Topic.MARKET_CHANGE, Topic.RISK_SCORE_CHANGED]
    instruction = (
        "You are BoardMind's Strategy Agent. Synthesize the latest finance, risk, and "
        "market signals plus the deterministic recommendation engine's output into a "
        "single coherent strategic recommendation for executives: what changed, why it "
        "matters, and the single highest-leverage action to take. 4-6 sentences."
    )

    def build_context(self, event: EventEnvelope) -> AgentContext:
        return AgentContext(
            finance_signals=[m["summary"] for m in memory.recall("finance_agent", limit=3)],
            risk_signals=[m["summary"] for m in memory.recall("risk_agent", kind="risk_profile", limit=3)],
            market_signals=[m["summary"] for m in memory.recall("market_intelligence_agent", limit=3)],
            deterministic_recommendations=[r["title"] for r in build_recommendations()],
            triggering_event=event.payload,
        )

    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        memory.remember(self.name, kind="recommendation", summary=model_output[:400], data=dict(context),
                         workflow_id=event.workflow_id)
        return [EventEnvelope(topic=Topic.STRATEGY_UPDATED, produced_by=self.name,
                               payload={"summary": model_output[:600]})]
