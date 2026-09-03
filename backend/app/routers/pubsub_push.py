"""
Receives Cloud Pub/Sub push deliveries and dispatches them to the right
agent. This is the "agents wake up automatically" mechanism described in
the architecture: Pub/Sub calls this endpoint, Cloud Run scales an instance
up on demand, the agent runs, and the instance can scale back to zero when
idle — no polling loop, no always-on worker.

Security: in production, Pub/Sub push requests carry a signed OIDC token in
the Authorization header (configured in pubsub_bus.ensure_infrastructure's
PushConfig.oidc_token). We verify that token's audience and issuer before
doing anything with the payload, so this endpoint can't be driven by
arbitrary internet traffic even if Cloud Run's ingress isn't fully locked
down. This check is skipped only when running locally without a configured
GCP project.
"""
import base64
import json
import logging

from fastapi import APIRouter, Request, HTTPException, Header

from ..platform.gcp_config import gcp_settings
from ..events.topics import EventEnvelope, Topic
from ..agents import registry

logger = logging.getLogger("boardmind.pubsub_push")
router = APIRouter(prefix="/pubsub", tags=["pubsub"])


def _verify_oidc(authorization: str | None) -> None:
    if not gcp_settings.configured():
        return  # local dev without a GCP project — nothing to verify against
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Pub/Sub push OIDC token")
    token = authorization.split(" ", 1)[1]
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(),
                                               audience=gcp_settings.PUBSUB_PUSH_AUDIENCE)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail=f"Invalid Pub/Sub push token: {exc}")
    if claims.get("email_verified") is False:
        raise HTTPException(status_code=401, detail="Unverified push token issuer")


@router.post("/push/{agent_name}")
async def push(agent_name: str, request: Request, authorization: str | None = Header(default=None)):
    _verify_oidc(authorization)

    envelope = await request.json()
    message = envelope.get("message", {})
    attributes = message.get("attributes", {}) or {}
    raw_data = message.get("data", "")
    payload = json.loads(base64.b64decode(raw_data).decode("utf-8")) if raw_data else {}

    try:
        topic = Topic(attributes.get("topic"))
    except ValueError:
        logger.warning("Push to unknown topic %s ignored", attributes.get("topic"))
        return {"status": "ignored"}

    event = EventEnvelope(
        event_id=attributes.get("event_id", message.get("messageId", "")),
        topic=topic,
        produced_by=attributes.get("produced_by", "unknown"),
        caused_by=attributes.get("caused_by") or None,
        workflow_id=attributes.get("workflow_id", ""),
        payload=payload,
    )

    try:
        agent = registry.get_agent(agent_name)
    except KeyError:
        logger.error("Push delivered for unknown agent %s", agent_name)
        # Ack anyway (return 200) — redelivery of a message for an agent
        # that doesn't exist will never succeed and would otherwise loop
        # forever until the subscription's max-delivery-attempts kicks in.
        return {"status": "unknown_agent"}

    result = await agent.handle_event(event)
    if result["status"] == "error":
        # Non-2xx tells Pub/Sub to retry per the subscription's retry policy.
        raise HTTPException(status_code=500, detail=result.get("error", "agent execution failed"))
    return {"status": "ok", **result}
