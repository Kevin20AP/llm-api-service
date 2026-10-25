"""
Dockerized LLM API Service — Step 1: the FastAPI core.
 
A type-safe HTTP API that wraps Claude. The client sends the full
conversation (a list of messages) and gets back the assistant's reply.
This is the foundation; later steps add Redis/Celery, Postgres, an MCP
server, and Docker.
 
RUN LOCALLY:
  uv run uvicorn main:app --reload
Then open http://127.0.0.1:8000/docs  (interactive API tester)
"""
 
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from anthropic import Anthropic
 
app = FastAPI(title="LLM API Service", version="0.1.0")
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY","").strip())
 
MODEL = "claude-sonnet-5"
 
 
# ---- Pydantic models: these validate every request/response automatically ----
class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$", description="'user' or 'assistant'")
    content: str = Field(..., min_length=1)
 
 
class ChatRequest(BaseModel):
    # The whole conversation so far. Memory lives here: the client keeps the
    # history and sends it each turn — the LLM itself is stateless.
    messages: list[Message] = Field(..., min_length=1)
    system: str = Field(default="You are a concise, helpful assistant.")
    max_tokens: int = Field(default=1000, ge=1, le=4096)
 
 
class ChatResponse(BaseModel):
    reply: str
    model: str
 
 
# ---- Endpoints ----
@app.get("/health")
def health():
    """Liveness check — every production service needs one."""
    return {"status": "ok"}
 
 
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Send a conversation, get the assistant's next reply."""
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=req.max_tokens,
            system=req.system,
            messages=[m.model_dump() for m in req.messages],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return ChatResponse(reply=text, model=MODEL)
    except Exception as e:
        # Never leak raw stack traces to clients in production.
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")
 

