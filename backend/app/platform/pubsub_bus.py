"""
Cloud Pub/Sub event bus.

Design choice, stated plainly: Cloud Run instances are stateless and can be
scaled to zero, so a long-lived pull-subscriber loop inside the container is
the wrong pattern here — it either dies with the instance or forces
min-instances=1 forever. The idiomatic serverless-agentic pattern (and what
this module implements) is:

    1. Agents PUBLISH events with PublisherClient (this module).
    2. Each topic has a push subscription, provisioned once by
       `ensure_infrastructure()`, whose endpoint is this same Cloud Run
       service (`/pubsub/push/{agent_name}`, see routers/pubsub_push.py).
    3. Pub/Sub itself wakes the right agent by POSTing to that endpoint —
       Cloud Run scales up an instance on demand. This is genuinely
       autonomous, event-driven execution with no polling loop to babysit.

If GOOGLE_CLOUD_PROJECT isn't set (e.g. `pytest` in CI with no GCP
credentials at all), publish() degrades to an in-process dispatcher so the
rest of the app — and its test suite — still runs; this is the one place a
local fallback exists, and it's logged loudly so it's never silently mistaken
for the real thing.
"""
from __future__ import annotations
import asyncio
import json
import logging
from concurrent.futures import TimeoutError as FuturesTimeoutError

from .gcp_config import gcp_settings
from ..events.topics import Topic, EventEnvelope, TOPIC_SUBSCRIBERS

logger = logging.getLogger("boardmind.pubsub")

_publisher = None
_local_dispatch_handlers: dict[str, list] = {}


def _get_publisher():
    global _publisher
    if _publisher is None:
        from google.cloud import pubsub_v1
        _publisher = pubsub_v1.PublisherClient()
    return _publisher


def _live_mode() -> bool:
    return gcp_settings.PUBSUB_ENABLED and gcp_settings.configured()


def register_local_handler(topic: Topic, handler):
    """Used only when PUBSUB_ENABLED=0 / no project configured (local unit
    tests). Production traffic never touches this path — see module
    docstring."""
    _local_dispatch_handlers.setdefault(topic.value, []).append(handler)


async def publish(event: EventEnvelope) -> str:
    """Publish an event and return the Pub/Sub message id (or a synthetic
    local id in fallback mode)."""
    if not _live_mode():
        logger.warning(
            "PUBSUB FALLBACK MODE (no GOOGLE_CLOUD_PROJECT / PUBSUB_ENABLED=0): "
            "dispatching '%s' in-process instead of via Cloud Pub/Sub.",
            event.topic.value,
        )
        for handler in _local_dispatch_handlers.get(event.topic.value, []):
            asyncio.create_task(handler(event))
        return f"local-{event.event_id}"

    publisher = _get_publisher()
    topic_path = publisher.topic_path(gcp_settings.PROJECT_ID, gcp_settings.topic(event.topic.value))
    data = json.dumps(event.payload).encode("utf-8")
    future = publisher.publish(topic_path, data=data, **event.to_pubsub_attributes())
    loop = asyncio.get_event_loop()
    try:
        message_id = await loop.run_in_executor(None, lambda: future.result(timeout=10))
    except FuturesTimeoutError:
        logger.error("Pub/Sub publish timed out for topic %s", event.topic.value)
        raise
    logger.info("Published %s -> topic=%s message_id=%s workflow=%s",
                event.event_id, event.topic.value, message_id, event.workflow_id)
    return message_id


def ensure_infrastructure() -> dict:
    """Idempotently creates every topic and the push subscriptions wired in
    TOPIC_SUBSCRIBERS. Safe to run repeatedly (e.g. from deploy/setup_gcp.sh
    on every deploy) — already-exists errors are swallowed.

    Each push subscription is configured with OIDC authentication so that a
    private (non-public) Cloud Run service can still receive the push:
    Pub/Sub signs the request with the service account passed here, and
    Cloud Run's IAM invoker check validates it. This is the standard secure
    push pattern and avoids making the service publicly invokable.
    """
    if not gcp_settings.configured():
        return {"status": "skipped", "reason": "GOOGLE_CLOUD_PROJECT not set"}

    from google.cloud import pubsub_v1
    from google.api_core.exceptions import AlreadyExists

    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    created_topics, created_subs = [], []

    for topic_enum in Topic:
        topic_path = publisher.topic_path(gcp_settings.PROJECT_ID, gcp_settings.topic(topic_enum.value))
        try:
            publisher.create_topic(name=topic_path)
            created_topics.append(topic_path)
        except AlreadyExists:
            pass

        for agent_name in TOPIC_SUBSCRIBERS.get(topic_enum, []):
            sub_path = subscriber.subscription_path(
                gcp_settings.PROJECT_ID, gcp_settings.subscription(topic_enum.value, agent_name)
            )
            push_endpoint = f"{gcp_settings.SERVICE_BASE_URL}/pubsub/push/{agent_name}"
            push_config = pubsub_v1.types.PushConfig(
                push_endpoint=push_endpoint,
                oidc_token=pubsub_v1.types.PushConfig.OidcToken(
                    service_account_email=f"boardmind-pubsub-invoker@{gcp_settings.PROJECT_ID}.iam.gserviceaccount.com",
                    audience=gcp_settings.PUBSUB_PUSH_AUDIENCE,
                ),
            )
            try:
                subscriber.create_subscription(
                    name=sub_path, topic=topic_path, push_config=push_config,
                    ack_deadline_seconds=60,
                )
                created_subs.append(sub_path)
            except AlreadyExists:
                pass

    return {"status": "ok", "created_topics": created_topics, "created_subscriptions": created_subs}
