# LLM API Service

A production-style backend service that wraps a large language model (Claude) behind a clean, type-safe HTTP API — with background job processing, a real database, schema migrations, a custom MCP server, and full containerization.

Built as a hands-on project to learn the modern AI-engineering stack end to end.

---

## Features

- **Type-safe REST API** built with **FastAPI** and **Pydantic** — automatic request validation and interactive OpenAPI docs at `/docs`.
- **Synchronous and asynchronous chat** — call the LLM directly, or offload it to a background worker and poll for the result.
- **Background job processing** with **Celery** + **Redis** — slow LLM calls run off the request thread so the API stays responsive.
- **Persistent storage** with **PostgreSQL** + **SQLAlchemy** — every conversation is saved and retrievable.
- **Database migrations** with **Alembic** — schema changes are versioned and applied safely, with no data loss.
- **Token-usage tracking** — each reply records how many tokens it used, for cost monitoring.
- **Custom MCP server** — exposes database-backed tools (e.g. conversation history) over the **Model Context Protocol**, so any MCP client (like Claude Desktop) can discover and call them.
- **Fully containerized** with **Docker** + **Docker Compose** — the entire stack (API, worker, database, cache) starts with one command.

## Tech stack

`Python 3.13` · `FastAPI` · `Pydantic` · `Celery` · `Redis` · `PostgreSQL` · `SQLAlchemy` · `Alembic` · `MCP` · `Docker` · `uv`

## Architecture

```
          ┌─────────────┐      enqueue job      ┌──────────┐
  HTTP →  │  FastAPI    │ ───────────────────→  │  Redis   │
          │  (web)      │ ←─────────────────    │ (broker) │
          └──────┬──────┘      poll result      └────┬─────┘
                 │                                    │ pulls job
                 │ read/write                         ▼
          ┌──────▼──────┐                       ┌──────────┐
          │ PostgreSQL  │ ←──── writes result ──│  Celery  │
          │ (storage)   │                       │ (worker) │
          └─────────────┘                       └──────────┘
```

- **web** — FastAPI server, handles requests and reads/writes the database.
- **worker** — Celery worker, runs LLM calls in the background.
- **db** — PostgreSQL, stores conversations (data persists via a Docker volume).
- **redis** — message broker + result store for Celery.

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Liveness check |
| `POST` | `/chat` | Send a conversation, get a reply (saved to the database) |
| `POST` | `/chat/async` | Submit the LLM call as a background job; returns a `task_id` |
| `GET`  | `/chat/result/{task_id}` | Fetch a background job's result |
| `GET`  | `/conversations` | List recent saved conversations |

## Running it

**Prerequisites:** Docker Desktop, and an Anthropic API key.

1. Create a `.env` file in the project root:
   ```
   ANTHROPIC_API_KEY=sk-ant-...your-key...
   ```
2. Build and start the whole stack:
   ```
   docker compose up --build
   ```
3. Apply the database migrations (first run only), in another terminal:
   ```
   docker compose exec web uv run alembic upgrade head
   ```
4. Open the interactive API docs: **http://localhost:8000/docs**

To stop: `docker compose down` (your data persists in the `pgdata` volume).

## The MCP server

The project includes a custom MCP server (`mcp_server.py`) that exposes tools over the Model Context Protocol:

- `conversation_count()` — total conversations stored
- `get_recent_conversations(limit)` — the most recent conversations

Test it locally with the MCP Inspector:
```
uv run mcp dev mcp_server.py
```

## What I learned

Building this covered the real AI-engineering backend stack: designing type-safe APIs, decoupling slow work with a task queue, persisting and migrating relational data, exposing tools to AI clients via MCP, and packaging everything reproducibly with Docker Compose.