"""
Celery background tasks — run slow LLM calls OFF the web request.

The broker/result-store address is read from an environment variable so the
SAME code works both locally (Redis on localhost) and in Docker (Redis is a
service named 'redis'). Local default = localhost.
"""

import os
from celery import Celery
from anthropic import Anthropic

# Read Redis address from env; fall back to localhost for local development.
BROKER = os.environ.get("CELERY_BROKER", "redis://localhost:6379/0")

celery_app = Celery("llm_tasks", broker=BROKER, backend=BROKER)

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "").strip())
MODEL = "claude-sonnet-5"


@celery_app.task
def generate_reply(messages: list[dict], system: str, max_tokens: int) -> str:
    """This runs in the background worker, not in the web request."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,  # type: ignore[arg-type]
    )
    return "".join(block.text for block in resp.content if block.type == "text")