"""
GCP platform configuration for BoardMind's agentic layer.

Every value here is read from the environment so the exact same container
image runs unchanged on a laptop (with `gcloud auth application-default
login` set up) and on Cloud Run (with a service account attached). Nothing
below hardcodes a project, region, or credential.

Required environment variables in production (see backend/.env.example and
deploy/cloudrun-service.yaml):

    GOOGLE_CLOUD_PROJECT        GCP project id
    GOOGLE_CLOUD_LOCATION       Vertex AI region, e.g. us-central1
    GOOGLE_GENAI_USE_VERTEXAI   "1" to route Gemini calls through Vertex AI
                                (as opposed to the public Gemini API)
    GEMINI_MODEL                e.g. gemini-2.5-flash
    PUBSUB_TOPIC_PREFIX         namespacing for topics, e.g. "boardmind"
    FIRESTORE_DATABASE          Firestore database id, "(default)" unless
                                you provisioned a named database
    EXEC_WATCH_ENABLED          "1" to run the in-process watch loop in
                                addition to Cloud Scheduler-driven ticks
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class GCPSettings:
    PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    USE_VERTEXAI: bool = _bool_env("GOOGLE_GENAI_USE_VERTEXAI", "1")

    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    FIRESTORE_DATABASE: str = os.getenv("FIRESTORE_DATABASE", "(default)")

    PUBSUB_TOPIC_PREFIX: str = os.getenv("PUBSUB_TOPIC_PREFIX", "boardmind")
    PUBSUB_ENABLED: bool = _bool_env("PUBSUB_ENABLED", "1")
    # Push subscriptions call back into Cloud Run over HTTPS; this is the base
    # URL Cloud Scheduler / Pub/Sub push subscriptions are configured against.
    SERVICE_BASE_URL: str = os.getenv("SERVICE_BASE_URL", "http://localhost:8000")
    PUBSUB_PUSH_AUDIENCE: str = os.getenv("PUBSUB_PUSH_AUDIENCE", SERVICE_BASE_URL)

    # Shared secret Cloud Scheduler sends in an "X-Scheduler-Token" header so
    # the scheduler-triggered endpoints aren't wide open on the public
    # Cloud Run URL. Cloud Run's own OIDC-authenticated invoker check (see
    # deploy/README.md) is the primary control; this is defense in depth.
    SCHEDULER_SHARED_SECRET: str = os.getenv("SCHEDULER_SHARED_SECRET", "")
    PUBSUB_PUSH_SHARED_SECRET: str = os.getenv("PUBSUB_PUSH_SHARED_SECRET", "")

    EXEC_WATCH_ENABLED: bool = _bool_env("EXEC_WATCH_ENABLED", "1")
    EXEC_WATCH_INTERVAL_SECONDS: int = int(os.getenv("EXEC_WATCH_INTERVAL_SECONDS", "300"))

    CLOUD_LOGGING_ENABLED: bool = _bool_env("CLOUD_LOGGING_ENABLED", "1")

    def configured(self) -> bool:
        return bool(self.PROJECT_ID)

    def topic(self, short_name: str) -> str:
        return f"{self.PUBSUB_TOPIC_PREFIX}-{short_name}"

    def subscription(self, short_name: str, agent_name: str) -> str:
        return f"{self.PUBSUB_TOPIC_PREFIX}-{short_name}-{agent_name}-sub"


gcp_settings = GCPSettings()
