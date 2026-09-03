"""
Canonical event catalogue for BoardMind's event-driven agent mesh.

Every cross-agent interaction flows through exactly one of these Pub/Sub
topics. Agents never call each other directly (see agents/base.py) —
they publish an event here and any agent subscribed to that topic wakes
up independently. This module is the single source of truth for topic
names and their payload shape so producers and consumers can't drift.
"""
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class Topic(str, Enum):
    REPORT_UPLOADED = "report-uploaded"
    FINANCIAL_ALERT = "financial-alert"
    MARKET_CHANGE = "market-change"
    BOARD_MEETING_APPROACHING = "board-meeting-approaching"
    RISK_SCORE_CHANGED = "risk-score-changed"
    COMPLIANCE_WARNING = "compliance-warning"
    CEO_REPORT_READY = "ceo-report-ready"
    STRATEGY_UPDATED = "strategy-updated"
    SCHEDULED_TICK = "scheduled-tick"          # Cloud Scheduler -> watch loop
    AGENT_EXECUTION_COMPLETED = "agent-execution-completed"  # -> observability

    # --- Boardroom collaboration mesh (human-in-the-loop departments) -----
    PROJECT_CREATED = "project-created"
    LANDING_PAGE_REQUESTED = "landing-page-requested"
    DESIGN_PROPOSED = "design-proposed"
    BUDGET_REVIEWED = "budget-reviewed"
    ROADMAP_UPDATED = "roadmap-updated"
    CAMPAIGN_UPDATED = "campaign-updated"
    HIRING_PROPOSED = "hiring-proposed"
    PROPOSAL_APPROVED = "proposal-approved"


TOPIC_SUBSCRIBERS: dict[Topic, list[str]] = {
    Topic.REPORT_UPLOADED: ["finance_agent", "compliance_agent"],
    Topic.SCHEDULED_TICK: ["finance_agent", "market_intelligence_agent"],
    Topic.FINANCIAL_ALERT: ["risk_agent", "strategy_agent"],
    Topic.MARKET_CHANGE: ["strategy_agent", "risk_agent"],
    Topic.RISK_SCORE_CHANGED: ["strategy_agent", "ceo_brief_agent"],
    Topic.COMPLIANCE_WARNING: ["risk_agent", "ceo_brief_agent"],
    Topic.STRATEGY_UPDATED: ["ceo_brief_agent"],
    Topic.BOARD_MEETING_APPROACHING: ["ceo_brief_agent"],
    Topic.CEO_REPORT_READY: [],   # terminal — dashboard/notification consumers only
    Topic.AGENT_EXECUTION_COMPLETED: [],  # terminal — observability only

    # Boardroom mesh: CEO creates product -> Marketing + Engineering + HR
    # react in parallel; Marketing's landing-page ask fans out to Design;
    # Design's concept triggers a Finance budget check; every one of these
    # produces a PROPOSAL, not an automatic action (see agents/boardroom_*).
    Topic.PROJECT_CREATED: ["marketing_agent", "engineering_agent", "hr_agent"],
    Topic.LANDING_PAGE_REQUESTED: ["design_agent"],
    Topic.DESIGN_PROPOSED: ["finance_agent"],
    Topic.BUDGET_REVIEWED: ["marketing_agent"],
    Topic.ROADMAP_UPDATED: [],
    Topic.CAMPAIGN_UPDATED: [],
    Topic.HIRING_PROPOSED: [],
    Topic.PROPOSAL_APPROVED: [],  # dispatched directly to the originating agent, not broadcast
}


class EventEnvelope(BaseModel):
    """Every message published to Pub/Sub is wrapped in this envelope so
    every consumer can trace causality (`caused_by`) across the whole
    workflow, which is what powers the Execution Timeline view."""
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    topic: Topic
    produced_by: str
    caused_by: str | None = None          # event_id of the upstream event, if any
    workflow_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: dict = Field(default_factory=dict)

    def to_pubsub_attributes(self) -> dict[str, str]:
        return {
            "event_id": self.event_id,
            "topic": self.topic.value,
            "produced_by": self.produced_by,
            "caused_by": self.caused_by or "",
            "workflow_id": self.workflow_id,
            "ts": self.ts,
        }
