"""
Custom MCP server — exposes your app's data as TOOLS that any MCP-aware AI
client (like Claude Desktop) can discover and call.

Each function decorated with @mcp.tool() becomes a tool the AI can use.
This server reads from the same PostgreSQL database your API writes to.

RUN / TEST:
  uv run mcp dev mcp_server.py      # opens the MCP Inspector (a web UI to test tools)
"""

from mcp.server.fastmcp import FastMCP
from db import SessionLocal, Conversation

# The MCP server. The name is how clients identify it.
mcp = FastMCP("llm-api-tools")


@mcp.tool()
def conversation_count() -> int:
    """Return the total number of conversations saved in the database."""
    db = SessionLocal()
    try:
        return db.query(Conversation).count()
    finally:
        db.close()


@mcp.tool()
def get_recent_conversations(limit: int = 5) -> list[dict]:
    """Return the most recent saved conversations (newest first)."""
    db = SessionLocal()
    try:
        rows = (
            db.query(Conversation)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "user_message": r.user_message,
                "reply": r.reply,
                "tokens_used": r.tokens_used,
            }
            for r in rows
        ]
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()