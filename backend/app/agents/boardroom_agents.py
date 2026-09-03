"""
Boardroom department agents.

These implement the human-in-the-loop half of the architecture: unlike the
finance/risk/market/compliance/strategy mesh (which is meant to run
autonomously end-to-end), every one of these agents stops short of acting.
`propose()` is the one thing every department agent calls instead of
publishing a downstream event directly — it writes a proposal a human must
approve/edit/reject (see platform/firestore_memory.create_proposal and
routers/boardroom.py), and only that human decision causes the next event
to actually publish. This is what makes "the human always remains the
decision maker" true architecturally, not just in the UI copy.

Kept intentionally minimal per-agent (breadth over depth): each is a real
ADK agent with a short instruction and a small, deterministic proposal
shape, not a fully fleshed-out planner. Wiring them together is the point.
"""
from ..events.topics import Topic, EventEnvelope
from ..platform import firestore_memory as memory
from .base import BaseEnterpriseAgent, AgentContext

DEPT_COLOR = {
    "marketing_agent": "#22D3EE", "design_agent": "#F472B6",
    "engineering_agent": "#34D399", "hr_agent": "#FBBF24",
    "finance_agent": "#8B5CF6",
}


def propose(agent_name: str, event: EventEnvelope, kind: str, title: str, body: str,
            payload: dict, actions: list[str], next_topic: Topic | None) -> str:
    full_payload = {**payload, "_next_topic": next_topic.value if next_topic else None}
    pid = memory.create_proposal(agent_name, kind, title, body, full_payload, actions, event.workflow_id)
    memory.log_activity(agent_name, "proposed", title, event.workflow_id, DEPT_COLOR.get(agent_name))
    return pid


class MarketingAgent(BaseEnterpriseAgent):
    name = "marketing_agent"
    version = "1.0.0"
    description = "Proposes launch strategies and campaigns; requests landing pages from Design."
    capabilities = ["campaign_strategy", "launch_planning"]
    permissions = ["read:agent_memory", "write:agent_memory"]
    subscribes_to = [Topic.PROJECT_CREATED, Topic.BUDGET_REVIEWED]
    instruction = (
        "You are BoardMind Boardroom's Marketing Agent. Given a new product goal, propose "
        "exactly three concrete launch strategy options in one short sentence each, labeled "
        "Option A/B/C. You never launch anything yourself — a human approves your proposal."
    )

    def build_context(self, event: EventEnvelope) -> AgentContext:
        return AgentContext(goal=event.payload.get("goal") or event.payload.get("summary", ""),
                             budget_feedback=event.payload if event.topic == Topic.BUDGET_REVIEWED else None)

    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        if event.topic == Topic.BUDGET_REVIEWED:
            # Finance already came back with a verdict on Design's concept —
            # Marketing reacts and requests nothing further automatically;
            # this becomes visible on the activity feed only.
            memory.log_activity(self.name, "responded to budget review", model_output[:200],
                                 event.workflow_id, DEPT_COLOR[self.name])
            return []
        propose(
            self.name, event, kind="campaign_strategy", title="Launch strategy options ready",
            body=model_output, payload={"goal": context["goal"]},
            actions=["approve", "edit", "reject"], next_topic=Topic.LANDING_PAGE_REQUESTED,
        )
        return []


class DesignAgent(BaseEnterpriseAgent):
    name = "design_agent"
    version = "1.0.0"
    description = "Generates landing page / creative concepts on request from Marketing."
    capabilities = ["landing_page_design", "creative_concepts"]
    permissions = ["read:agent_memory", "write:agent_memory"]
    subscribes_to = [Topic.LANDING_PAGE_REQUESTED]
    instruction = (
        "You are BoardMind Boardroom's Design Agent. Given a marketing campaign brief, propose "
        "three short landing-page concepts (Concept A/B/C), one sentence each, with a rough "
        "relative cost tag (low/medium/high) for the creative assets involved."
    )

    def build_context(self, event: EventEnvelope) -> AgentContext:
        return AgentContext(campaign_brief=event.payload.get("summary", event.payload))

    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        propose(
            self.name, event, kind="design_concepts", title="3 landing page concepts ready",
            body=model_output, payload={"campaign_brief": context["campaign_brief"]},
            actions=["preview", "select", "reject"], next_topic=Topic.DESIGN_PROPOSED,
        )
        return []


class EngineeringAgent(BaseEnterpriseAgent):
    name = "engineering_agent"
    version = "1.0.0"
    description = "Estimates delivery timelines and proposes sprint/roadmap changes."
    capabilities = ["estimation", "sprint_planning"]
    permissions = ["read:agent_memory", "write:agent_memory"]
    subscribes_to = [Topic.PROJECT_CREATED]
    instruction = (
        "You are BoardMind Boardroom's Engineering Agent. Given a product goal and its stated "
        "deadline, estimate completion in weeks and state one concrete risk to that estimate. "
        "One short paragraph."
    )

    def build_context(self, event: EventEnvelope) -> AgentContext:
        return AgentContext(goal=event.payload.get("goal", ""))

    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        propose(
            self.name, event, kind="estimate", title="Delivery estimate ready",
            body=model_output, payload={"goal": context["goal"]},
            actions=["accept", "split_sprint", "reject"], next_topic=Topic.ROADMAP_UPDATED,
        )
        return []


class HRAgent(BaseEnterpriseAgent):
    name = "hr_agent"
    version = "1.0.0"
    description = "Flags staffing needs and proposes contractor hires for new initiatives."
    capabilities = ["staffing_analysis", "hiring_proposals"]
    permissions = ["read:agent_memory", "write:agent_memory"]
    subscribes_to = [Topic.PROJECT_CREATED]
    instruction = (
        "You are BoardMind Boardroom's HR Agent. Given a new product goal, state in one or two "
        "sentences whether existing headcount can deliver it or a contractor hire is recommended, "
        "and for which role."
    )

    def build_context(self, event: EventEnvelope) -> AgentContext:
        return AgentContext(goal=event.payload.get("goal", ""))

    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        if "contractor" in model_output.lower() or "hire" in model_output.lower():
            propose(
                self.name, event, kind="hiring", title="Contractor hire recommended",
                body=model_output, payload={"goal": context["goal"]},
                actions=["approve", "reject"], next_topic=Topic.HIRING_PROPOSED,
            )
        else:
            memory.log_activity(self.name, "assessed staffing", model_output[:200],
                                 event.workflow_id, DEPT_COLOR[self.name])
        return []
