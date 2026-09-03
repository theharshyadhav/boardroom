"""
Finance Agent — financial analysis, anomaly/trend detection, forecasting.

Wakes on REPORT_UPLOADED (new financial data landed) and SCHEDULED_TICK
(periodic health check driven by Cloud Scheduler, see routers/watch.py).
Reuses the existing deterministic KPI/driver-decomposition layer
(analytics.py, driver_analysis.py) so the numbers agents reason over are the
same numbers the dashboard already trusts — the agent's job is detection +
narration + deciding whether to escalate, not re-deriving statistics Gemini
would just be guessing at.
"""
from ..events.topics import Topic, EventEnvelope
from ..analytics import build_kpi_series, z_score_of_window_change, materiality_band
from ..driver_analysis import decompose_revenue_drivers
from ..platform import firestore_memory as memory
from .base import BaseEnterpriseAgent, AgentContext

ANOMALY_Z_THRESHOLD = 2.0
DEMO_CAMPAIGN_BUDGET_USD = 15000  # deterministic budget ceiling used for the Boardroom demo scenario


class FinanceAgent(BaseEnterpriseAgent):
    name = "finance_agent"
    version = "1.0.0"
    description = "Continuous financial analysis, anomaly detection, forecasting, and financial memory."
    capabilities = ["kpi_analysis", "anomaly_detection", "trend_detection", "forecasting"]
    permissions = ["read:financial_data", "read:agent_memory", "write:agent_memory"]
    subscribes_to = [Topic.REPORT_UPLOADED, Topic.SCHEDULED_TICK, Topic.DESIGN_PROPOSED]
    instruction = (
        "You are BoardMind's Finance Agent, an enterprise financial analyst. "
        "You are given a deterministic KPI series and driver decomposition, already "
        "computed via SQL. Do not invent numbers not present in the context. Identify "
        "the most material financial development, explain its likely driver in plain "
        "executive language, and state your confidence. Be concise: 4-6 sentences. "
        "If instead you are given a design concept's estimated cost against a campaign "
        "budget, state clearly whether it fits, and by how much it's over or under, in "
        "one sentence."
    )

    def build_context(self, event: EventEnvelope) -> AgentContext:
        if event.topic == Topic.DESIGN_PROPOSED:
            # Deterministic, reproducible "cost estimate" derived from the length of the
            # design brief text, so the demo doesn't depend on the model inventing a number.
            brief = str(event.payload.get("campaign_brief", ""))
            estimated_cost = round(min(30000, 4000 + len(brief) * 35), -2)
            over_by_pct = round((estimated_cost - DEMO_CAMPAIGN_BUDGET_USD) / DEMO_CAMPAIGN_BUDGET_USD * 100, 1)
            return AgentContext(
                mode="budget_check", estimated_cost_usd=estimated_cost,
                budget_ceiling_usd=DEMO_CAMPAIGN_BUDGET_USD, over_budget_pct=over_by_pct,
                campaign_brief=brief,
            )
        kpis = build_kpi_series()
        drivers = decompose_revenue_drivers()
        revenue_series = kpis.get("revenue", [])
        z = z_score_of_window_change(revenue_series) if revenue_series else 0.0
        past_reports = memory.recall(self.name, kind="report", limit=5)
        latest_by_kpi = {k: v[-1] for k, v in kpis.items() if isinstance(v, list) and v}
        return AgentContext(
            kpi_summary=latest_by_kpi,
            revenue_z_score=z,
            materiality=materiality_band(z),
            driver_decomposition=drivers,
            past_reports=[p["summary"] for p in past_reports],
        )

    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        if context.get("mode") == "budget_check":
            memory.remember(self.name, kind="report", summary=model_output[:300], data=dict(context),
                             workflow_id=event.workflow_id)
            if context["over_budget_pct"] > 0:
                from .boardroom_agents import propose
                propose(
                    self.name, event, kind="budget_review",
                    title=f"Campaign design exceeds budget by {context['over_budget_pct']}%",
                    body=model_output, payload={"estimated_cost_usd": context["estimated_cost_usd"],
                                                 "budget_ceiling_usd": context["budget_ceiling_usd"]},
                    actions=["reduce_budget", "approve_anyway"], next_topic=Topic.BUDGET_REVIEWED,
                )
                return []
            memory.log_activity(self.name, "approved budget", model_output[:200],
                                 event.workflow_id, "#8B5CF6")
            return [EventEnvelope(topic=Topic.BUDGET_REVIEWED, produced_by=self.name,
                                   payload={"approved": True, "summary": model_output[:400]})]

        memory.remember(self.name, kind="report", summary=model_output[:300], data=dict(context),
                         workflow_id=event.workflow_id)

        downstream = []
        if abs(context["revenue_z_score"]) >= ANOMALY_Z_THRESHOLD:
            memory.raise_alert(
                severity="high" if context["materiality"] == "high" else "medium",
                title="Finance Agent detected a material revenue anomaly",
                body=model_output, agent=self.name, workflow_id=event.workflow_id,
            )
            downstream.append(EventEnvelope(
                topic=Topic.FINANCIAL_ALERT, produced_by=self.name,
                payload={"z_score": context["revenue_z_score"], "materiality": context["materiality"],
                         "summary": model_output[:500]},
            ))
        return downstream
