"""
Database layer — PostgreSQL via SQLAlchemy.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Integer, String, Text, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column

# Local Postgres (installed via Homebrew) uses your Mac username, no password.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://localhost:5432/llm_api"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_message: Mapped[str] = mapped_column(Text)
    reply: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


def init_db():
    """Create tables based on the models above (safe to run repeatedly)."""
    Base.metadata.create_all(engine)