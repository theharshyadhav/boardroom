import logging
import importlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .platform.gcp_config import gcp_settings
from .platform.pubsub_bus import ensure_infrastructure
from .agents.registry import init_agents
from .routers import (
    auth, data, kpis, events, driver, evidence, recommendations, feedback,
    simulate, narrative, telemetry, agents as agents_router, observability,
    watch, pubsub_push, boardroom, admin,
)


def _configure_logging():
    """Cloud Logging integration: when running on Cloud Run with a project
    configured, attach the Cloud Logging handler so agent execution logs,
    security audit events, and errors all land in Cloud Logging /
    Log Explorer alongside every other GCP service's logs. Falls back to
    plain stdout logging (which Cloud Run also captures automatically)
    when no project is configured."""
    logging.basicConfig(level=logging.INFO)
    if gcp_settings.CLOUD_LOGGING_ENABLED and gcp_settings.configured():
        try:
            cloud_logging = importlib.import_module("google.cloud.logging")
            client = cloud_logging.Client(project=gcp_settings.PROJECT_ID)
            client.setup_logging(log_level=logging.INFO)
        except Exception:  # noqa: BLE001
            logging.getLogger("boardmind").warning(
                "Cloud Logging client failed to initialize; falling back to stdout logging.", exc_info=True
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    logger = logging.getLogger("boardmind.startup")
    logger.info(
        "CORS configuration: origins=%s origin_regex=%s methods=%s headers=%s",
        settings.CORS_ORIGINS,
        settings.CORS_ORIGIN_REGEX,
        ["*"],
        ["*"],
    )

    instances = init_agents()
    logger.info("Initialized %d ADK agents: %s", len(instances), list(instances.keys()))

    if gcp_settings.configured():
        infra = ensure_infrastructure()
        logger.info("Pub/Sub infrastructure check: %s", infra)
    else:
        logger.warning(
            "GOOGLE_CLOUD_PROJECT is not set — running in local fallback mode "
            "(in-process event dispatch, in-memory Firestore substitute). "
            "Set GOOGLE_CLOUD_PROJECT + credentials to run against real GCP services."
        )
    yield


app = FastAPI(
    title="BoardMind API",
    description=(
        "Autonomous enterprise AI agent platform: Google ADK agents reasoning with "
        "Gemini via Vertex AI, communicating over Cloud Pub/Sub, with long-term memory "
        "in Firestore. The original deterministic decision-intelligence pipeline "
        "remains the source of truth the agents reason over."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in [auth.router, data.router, kpis.router, events.router, driver.router,
          evidence.router, recommendations.router, feedback.router, simulate.router,
          narrative.router, telemetry.router, agents_router.router, observability.router,
          watch.router, pubsub_push.router, boardroom.router, admin.router]:
    app.include_router(r)

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "boardmind-api",
        "gcp_configured": gcp_settings.configured(),
        "project": gcp_settings.PROJECT_ID or None,
    }
