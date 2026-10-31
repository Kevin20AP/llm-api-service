"""
Dockerized LLM API Service — Step 3: save conversations to PostgreSQL.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from anthropic import Anthropic
from celery.result import AsyncResult

from tasks import generate_reply, celery_app
from db import SessionLocal, Conversation


@asynccontextmanager
async def lifespan(app: FastAPI):   #  # Alembic now manages the database schema.
    yield


app = FastAPI(title="LLM API Service", version="0.3.0", lifespan=lifespan)
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "").strip())
MODEL = "claude-sonnet-5"


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Synchronous chat — and save the result to Postgres."""
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=req.max_tokens,
            system=req.system,
            messages=[m.model_dump() for m in req.messages],  # type: ignore[arg-type]
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    db = SessionLocal()
    try:
        row = Conversation(
            user_message=req.messages[-1].content,
            reply=text,
            model=MODEL,
            tokens_used=resp.usage.output_tokens
        )
        db.add(row)
        db.commit()
    finally:
        db.close()

    return ChatResponse(reply=text, model=MODEL)


@app.post("/chat/async", response_model=JobResponse)
def chat_async(req: ChatRequest):
    task = generate_reply.delay(  # type: ignore[attr-defined]
        [m.model_dump() for m in req.messages], req.system, req.max_tokens
    )
    return JobResponse(task_id=task.id, status="queued")


@app.get("/chat/result/{task_id}")
def chat_result(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    if result.successful():
        return {"status": "done", "reply": result.get()}
    if result.failed():
        return {"status": "failed"}
    return {"status": result.status.lower()}


@app.get("/conversations")
def list_conversations():
    """Return the 20 most recent saved conversations."""
    db = SessionLocal()
    try:
        rows = (
            db.query(Conversation)
            .order_by(Conversation.created_at.desc())
            .limit(20)
            .all()
        )
        return [
            {
                "id": r.id,
                "user_message": r.user_message,
                "reply": r.reply,
                "model": r.model,
                "tokens_used": r.tokens_used, 
                "created_at": str(r.created_at),
            }
            for r in rows
        ]
    finally:
        db.close()