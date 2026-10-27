"""
Dockerized LLM API Service — Step 2: background jobs with Redis + Celery.
"""

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from anthropic import Anthropic
from celery.result import AsyncResult

from tasks import generate_reply, celery_app

app = FastAPI(title="LLM API Service", version="0.2.0")
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "").strip())
MODEL = "claude-sonnet-5"


# ---- Data models ----
class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$", description="'user' or 'assistant'")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1)
    system: str = Field(default="You are a concise, helpful assistant.")
    max_tokens: int = Field(default=1000, ge=1, le=4096)


class ChatResponse(BaseModel):
    reply: str
    model: str


class JobResponse(BaseModel):
    task_id: str
    status: str


# ---- Endpoints ----
@app.get("/health")
def health():
    """Liveness check — every production service needs one."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Synchronous: waits for Claude and returns the reply directly."""
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=req.max_tokens,
            system=req.system,
            messages=[m.model_dump() for m in req.messages],  # type: ignore[arg-type]
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return ChatResponse(reply=text, model=MODEL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")


@app.post("/chat/async", response_model=JobResponse)
def chat_async(req: ChatRequest):
    """Hand the work to the background worker; return a task id immediately."""
    task = generate_reply.delay( # type: ignore[attr-defined]
        [m.model_dump() for m in req.messages], req.system, req.max_tokens
    )
    return JobResponse(task_id=task.id, status="queued")


@app.get("/chat/result/{task_id}")
def chat_result(task_id: str):
    """Check a background job by its task id."""
    result = AsyncResult(task_id, app=celery_app)
    if result.successful():
        return {"status": "done", "reply": result.get()}
    if result.failed():
        return {"status": "failed"}
    return {"status": result.status.lower()}  # e.g. "pending", "started"