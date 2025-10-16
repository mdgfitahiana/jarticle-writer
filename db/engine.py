from __future__ import annotations

import tempfile
from urllib.parse import quote_plus
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from pgvector.psycopg import register_vector

from .config import get_settings

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def _build_connect_args(cfg: dict) -> dict:
    connect_args = {"sslmode": cfg["sslmode"]}
    if cfg.get("ca_pem"):
        # Persist CA to a temp file so psycopg can read it
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
        f.write(cfg["ca_pem"].encode("utf-8"))
        f.flush()
        f.close()
        connect_args["sslrootcert"] = f.name
    else:
        connect_args["sslrootcert"] = "system"
    return connect_args


def get_engine() -> Engine:
    """
    Create (or return) a global SQLAlchemy Engine.
    Guarantees that the global session factory is initialized as well.
    """
    global _engine, _SessionLocal

    # If an engine already exists, make sure the session factory exists too.
    if _engine is not None:
        if _SessionLocal is None:
            _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)
        return _engine

    cfg = get_settings()
    user = cfg["user"]
    pwd = quote_plus(cfg["password"])
    host = cfg["host"]
    port = cfg["port"]
    db = cfg["name"]

    if not (host and user and cfg["password"]):
        raise RuntimeError("DB config missing: DATABASE_HOST/USER/PASSWORD")

    dsn = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"

    _engine = create_engine(
        dsn,
        connect_args=_build_connect_args(cfg),
        pool_pre_ping=True,
        echo=cfg.get("echo", False),
        future=True,
    )

    @event.listens_for(_engine, "connect")
    def _on_connect(dbapi_conn, _):  # noqa: F811 - SQLAlchemy handler signature
        # Ensure pgvector is registered on each new DBAPI connection
        register_vector(dbapi_conn)

    # Ensure the pgvector extension exists (safe to run repeatedly).
    # If the DB user lacks permission, this will raise—which is usually what you want.
    with _engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Initialize the session factory whenever we (re)initialize the engine.
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)

    return _engine


def get_session_factory() -> sessionmaker:
    """
    Return a configured sessionmaker. Ensures engine (and factory) are initialized.
    """
    global _SessionLocal
    if _SessionLocal is None:
        get_engine()
    if _SessionLocal is None:
        # Defensive: if we still don't have it, surface a clear error.
        raise RuntimeError("Session factory failed to initialize; check DB config/engine init.")
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for a DB session with automatic commit/rollback."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
