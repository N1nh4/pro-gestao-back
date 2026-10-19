"""Camada de banco de dados: engine, sessão, Base declarativa e utilitários."""

from __future__ import annotations

import uuid
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite precisa de connect_args extra; Postgres não.
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base declarativa compartilhada por todos os modelos."""


def gen_uuid() -> str:
    """Gera um id UUID em string (PKs dos modelos)."""
    return str(uuid.uuid4())


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI: injeta uma sessão por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
