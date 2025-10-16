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
    """
    Build psycopg3 connect args with correct SSL semantics.

    QUICK MODE:
    - If sslmode == 'require', return ONLY {'sslmode': 'require'} and do NOT pass any CA.
      (Avoids 'certificate verify failed' / psycopg rejecting sslrootcert with 'require'.)

    VERIFYING MODES:
    - If a PEM is provided (ca_pem), persist to a temp file and pass sslrootcert=<file>.
    - Else, if a root is provided (sslroot like 'system' or a bundle path) and
      sslmode is a verifying mode ('verify-full'/'verify-ca'), pass it through.
    """
    sslmode = str(cfg.get("sslmode", "")).strip().lower()
    sslroot = str(cfg.get("sslroot", "")).strip()
    ca_pem = str(cfg.get("ca_pem", "")).strip()

    # Always include sslmode if provided
    connect_args: dict = {}
    if sslmode:
        connect_args["sslmode"] = sslmode

    # QUICK FIX: for 'require', never pass a CA/root
    if sslmode == "require":
        return connect_args

    # Verifying modes only below
    if ca_pem:
        # Persist CA to a temp file so psycopg can read it
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
        f.write(ca_pem.encode("utf-8"))
        f.flush()
        f.close()
        connect_args["sslrootcert"] = f.name
    elif sslmode in {"verify-full", "verify-ca"} and sslroot:
        # e.g., "system" or a path to a CA bundle
        connect_args["sslrootcert"] = sslroot

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
    cfg = get_settings()
    print("DB SSL cfg:", {"sslmode": cfg["sslmode"], "sslroot": cfg["sslroot"], "has_ca": bool(cfg["ca_pem"])})

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
    # If the DB user lacks permission, this will raise.
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
