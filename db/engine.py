from __future__ import annotations
import tempfile
from urllib.parse import quote_plus
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from pgvector.psycopg import register_vector

from .config import get_settings

_engine = None
_SessionLocal = None

def get_engine():
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    cfg = get_settings()
    user = cfg["user"]
    pwd  = quote_plus(cfg["password"])
    host = cfg["host"]
    port = cfg["port"]
    db   = cfg["name"]

    if not (host and user and cfg["password"]):
        raise RuntimeError("DB config missing: DATABASE_HOST/USER/PASSWORD")

    dsn = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"

    connect_args = {"sslmode": cfg["sslmode"]}
    if cfg["ca_pem"]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as f:
            f.write(cfg["ca_pem"].encode("utf-8"))
            connect_args["sslrootcert"] = f.name
    else:
        connect_args["sslrootcert"] = "system"

    _engine = create_engine(
        dsn,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=cfg["echo"],
        future=True,
    )

    @event.listens_for(_engine, "connect")
    def _on_connect(dbapi_conn, _):
        register_vector(dbapi_conn)

    # Safe to run each start: make sure vector extension exists.
    with _engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session)
    return _engine

def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        get_engine()
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
