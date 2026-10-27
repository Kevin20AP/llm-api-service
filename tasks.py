import os
from celery import Celery
from anthropic import Anthropic

# Point Celery at Redis for both the job queue and the result store.
celery_app = Celery(
    "llm_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

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