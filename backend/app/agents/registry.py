"""
In-process agent registry: single place that instantiates every
BaseEnterpriseAgent exactly once (Runner/session_service construction isn't
free) and dispatches an incoming EventEnvelope to the right agent instance.

Used by:
  - routers/pubsub_push.py     (Pub/Sub push delivery -> agent.handle_event)
  - routers/agents.py          (Agent Registry API — reads Firestore, not this)
  - routers/watch.py           (Executive Watch "run now" -> direct dispatch)
"""
from ..platform.pubsub_bus import register_local_handler
from ..platform.gcp_config import gcp_settings
from .finance_agent import FinanceAgent
from .risk_agent import RiskAgent
from .market_agent import MarketIntelligenceAgent
from .compliance_agent import ComplianceAgent
from .strategy_agent import StrategyAgent
from .ceo_brief_agent import CEOBriefAgent
from .boardroom_agents import MarketingAgent, DesignAgent, EngineeringAgent, HRAgent

_AGENT_CLASSES = [
    FinanceAgent, RiskAgent, MarketIntelligenceAgent,
    ComplianceAgent, StrategyAgent, CEOBriefAgent,
    MarketingAgent, DesignAgent, EngineeringAgent, HRAgent,
]

_instances: dict[str, object] = {}


def init_agents() -> dict[str, object]:
    """Instantiate every agent once, at app startup (see main.py lifespan)."""
    for cls in _AGENT_CLASSES:
        agent = cls()
        _instances[agent.name] = agent
        # Local fallback dispatch only fires when Pub/Sub isn't configured
        # (see platform/pubsub_bus.py) — production traffic arrives via the
        # push endpoint in routers/pubsub_push.py instead.
        if not gcp_settings.configured():
            for topic in agent.subscribes_to:
                register_local_handler(topic, agent.handle_event)
    return _instances


def get_agent(name: str):
    if name not in _instances:
        raise KeyError(f"Unknown or uninitialized agent: {name}")
    return _instances[name]


def all_agent_names() -> list[str]:
    return list(_instances.keys())
