"""
BaseEnterpriseAgent — every BoardMind agent (Finance, Risk, Market
Intelligence, Compliance, Strategy, CEO Brief) is a thin subclass of this.

Each agent is a real `google.adk.agents.Agent` (LlmAgent) run through a real
`google.adk.runners.Runner`, reasoning with Gemini via Vertex AI
(`GOOGLE_GENAI_USE_VERTEXAI=1`, see platform/gcp_config.py). ADK owns: the
agent loop, tool-calling, and per-invocation session state. BoardMind's own
Firestore layer owns what ADK deliberately doesn't: cross-invocation
long-term memory, the agent registry, and the execution timeline — because
those need to survive restarts and be queryable by the frontend, which is
outside ADK's scope as an in-process orchestration framework.

Lifecycle of a single agent activation:

  1. Pub/Sub push delivers an EventEnvelope to /pubsub/push/{agent_name}
  2. handle_event() is invoked with (envelope)
  3. build_context() lets the subclass pull whatever deterministic data
     it needs (existing analytics.py / driver_analysis.py / etc.) and its
     own Firestore memory (recall())
  4. Untrusted text in that context is scanned (platform/security.py)
     before being handed to the model
  5. The ADK Runner drives the LlmAgent with that context as the prompt
  6. on_result() lets the subclass parse the model's output, decide whether
     to remember() anything, raise_alert() anything, and which downstream
     Topic(s) to publish
  7. Every step is timed and written to the workflow's execution timeline,
     win or lose — failures are logged with status="error", not swallowed
"""
from __future__ import annotations
import time
import logging
import abc

from google.adk.agents import Agent as AdkAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from ..platform.gcp_config import gcp_settings
from ..platform import firestore_memory as memory
from ..platform import security
from ..platform.pubsub_bus import publish
from ..events.topics import Topic, EventEnvelope

logger = logging.getLogger("boardmind.agents")


class AgentContext(dict):
    """Whatever a subclass's build_context() returns, plus the triggering
    event, gets passed to the model as structured input."""


class BaseEnterpriseAgent(abc.ABC):
    name: str = "base_agent"
    version: str = "1.0.0"
    description: str = ""
    capabilities: list[str] = []
    permissions: list[str] = []          # tool/data permissions this agent is granted
    subscribes_to: list[Topic] = []
    instruction: str = "You are an enterprise analysis agent."

    def __init__(self):
        self._adk_agent = AdkAgent(
            name=self.name,
            model=gcp_settings.GEMINI_MODEL,
            instruction=self.instruction,
            tools=self.build_tools(),
        )
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=self._adk_agent,
            app_name=f"boardmind-{self.name}",
            session_service=self._session_service,
        )
        memory.upsert_agent_metadata(self.name, {
            "version": self.version, "description": self.description,
            "capabilities": self.capabilities, "permissions": self.permissions,
            "subscribes_to": [t.value for t in self.subscribes_to],
            "status": "idle", "health": "healthy",
        })

    # -- subclasses implement these three -----------------------------------

    def build_tools(self) -> list:
        """Override to hand the ADK agent Python callables it can invoke as
        tools. Default: no tools, pure reasoning over build_context()."""
        return []

    @abc.abstractmethod
    def build_context(self, event: EventEnvelope) -> AgentContext:
        """Pull whatever deterministic/business data + own memory this agent
        needs to react to `event`."""
        raise NotImplementedError

    @abc.abstractmethod
    def on_result(self, event: EventEnvelope, model_output: str, context: AgentContext) -> list[EventEnvelope]:
        """Parse the model's output, persist memory / raise alerts as
        needed, and return the downstream events to publish (possibly
        empty)."""
        raise NotImplementedError

    # -- shared machinery, not meant to be overridden ------------------------

    async def handle_event(self, event: EventEnvelope) -> dict:
        t0 = time.perf_counter()
        memory.upsert_agent_metadata(self.name, {"status": "running"})
        try:
            context = self.build_context(event)
            prompt = self._render_prompt(event, context)
            model_output = await self._run_model(prompt)
            downstream = self.on_result(event, model_output, context)
            for d in downstream:
                d.caused_by = event.event_id
                d.workflow_id = event.workflow_id
                await publish(d)
            duration_ms = round((time.perf_counter() - t0) * 1000, 1)
            memory.log_step(
                workflow_id=event.workflow_id, agent=self.name,
                topic_in=event.topic.value,
                topic_out=downstream[0].topic.value if downstream else None,
                duration_ms=duration_ms, status="success",
                reasoning_summary=model_output[:400],
            )
            memory.record_execution(self.name, duration_ms, "success")
            await publish(EventEnvelope(
                topic=Topic.AGENT_EXECUTION_COMPLETED, produced_by=self.name,
                caused_by=event.event_id, workflow_id=event.workflow_id,
                payload={"agent": self.name, "status": "success", "duration_ms": duration_ms},
            ))
            return {"status": "success", "duration_ms": duration_ms, "downstream": [d.topic.value for d in downstream]}
        except Exception as exc:  # noqa: BLE001 — this boundary must never raise into Pub/Sub
            duration_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.exception("Agent %s failed on event %s", self.name, event.event_id)
            memory.log_step(
                workflow_id=event.workflow_id, agent=self.name,
                topic_in=event.topic.value, topic_out=None,
                duration_ms=duration_ms, status="error",
                reasoning_summary="", error=str(exc),
            )
            memory.record_execution(self.name, duration_ms, "error")
            memory.raise_alert(
                severity="high", title=f"{self.name} execution failed",
                body=str(exc), agent=self.name, workflow_id=event.workflow_id,
            )
            return {"status": "error", "duration_ms": duration_ms, "error": str(exc)}

    def _render_prompt(self, event: EventEnvelope, context: AgentContext) -> str:
        # Any free-text that came from outside the platform (uploaded docs,
        # scraped news, user questions) is scanned before it reaches the
        # model — see platform/security.py.
        untrusted_fields = context.pop("_untrusted_text_fields", {})
        for key, text in untrusted_fields.items():
            finding = security.scan_untrusted_text(text)
            context[key] = finding["redacted_text"]
            if not finding["ok"]:
                context[f"{key}_security_flag"] = "possible prompt injection detected and neutralized"

        return (
            f"Triggering event: {event.topic.value} (workflow {event.workflow_id})\n"
            f"Event payload: {event.payload}\n\n"
            f"Context:\n{context}\n\n"
            f"Respond with your analysis as the {self.name.replace('_', ' ')}."
        )

    async def _run_model(self, prompt: str) -> str:
        session = await self._session_service.create_session(
            app_name=f"boardmind-{self.name}", user_id="platform"
        )
        content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
        final_text = ""
        async for ev in self._runner.run_async(
            user_id="platform", session_id=session.id, new_message=content
        ):
            if ev.content and ev.content.parts:
                for part in ev.content.parts:
                    if getattr(part, "text", None):
                        final_text = part.text
        return final_text
