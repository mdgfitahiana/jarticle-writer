# test.py
import os
import tempfile
import streamlit as st
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Integer, Index, event, select
from sqlalchemy.orm import DeclarativeBase, mapped_column, Session
from pgvector.sqlalchemy import Vector
from pgvector.psycopg import register_vector

# --- 1) Load configuration ----------------------------------------------------
secrets = st.secrets

DB_HOST = secrets.get("DATABASE_HOST", "").strip()
DB_PORT = int(secrets.get("DATABASE_PORT", "5432"))
DB_NAME = secrets.get("DATABASE_NAME", "postgres").strip()
DB_USER = secrets.get("DATABASE_USER", "").strip()
DB_PASSWORD = secrets.get("DATABASE_PASSWORD", "")
SSL_MODE = secrets.get("DATABASE_SSLMODE", "verify-full")  # verify-full | require
# Prefer system trust store; if SUPABASE_CA_PEM is set, we'll use it automatically
CA_PEM = secrets.get("SUPABASE_CA_PEM", "").strip()
SQLALCHEMY_ECHO = secrets.get("SQLALCHEMY_ECHO", False)

if not (DB_HOST and DB_USER and DB_PASSWORD):
    raise SystemExit("DATABASE_HOST, DATABASE_USER, and DATABASE_PASSWORD are required.")

# Build DSN with percent-encoded password (handles #, @, etc.)
dsn = (
    f"postgresql+psycopg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# --- 2) SSL connect_args ------------------------------------------------------
connect_args = {"sslmode": SSL_MODE}

# If a PEM is provided in secrets (e.g., on Streamlit/Lovable), write it to a temp file.
# Otherwise, rely on the system trust store (works on most platforms).
temp_ca_path = None
if CA_PEM:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as f:
        f.write(CA_PEM.encode("utf-8"))
        temp_ca_path = f.name
    connect_args["sslrootcert"] = temp_ca_path
else:
    connect_args["sslrootcert"] = "system"

# --- 3) Create engine & register pgvector ------------------------------------
engine = create_engine(
    dsn,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=SQLALCHEMY_ECHO,
    future=True,
)

@event.listens_for(engine, "connect")
def _on_connect(dbapi_conn, _):
    # Needed so the driver understands 'vector' over the wire (psycopg3)
    register_vector(dbapi_conn)

# --- 4) Ensure extension exists & sanity check --------------------------------
with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    ver = conn.scalar(text("select version()"))
    print("Connected to:", ver.splitlines()[0])

# --- 5) ORM models ------------------------------------------------------------
class Base(DeclarativeBase):
    pass

DIM = int(secrets.get("EMBEDDING_DIM", "3"))  # set to your real embedding size

class Item(Base):
    __tablename__ = "items"
    id = mapped_column(Integer, primary_key=True)
    embedding = mapped_column(Vector(DIM), nullable=False)

# --- 6) Create schema ---------------------------------------------------------
Base.metadata.create_all(engine)

# --- 7) Optional: ANN index (HNSW by default) --------------------------------
USE_INDEX = secrets.get("VECTOR_INDEX", True)
METRIC = secrets.get("VECTOR_METRIC", "cosine").lower()  # l2 | ip | cosine
OPCLASS = {
    "l2": "vector_l2_ops",
    "ip": "vector_ip_ops",
    "cosine": "vector_cosine_ops",
}.get(METRIC, "vector_cosine_ops")

if USE_INDEX:
    idx = Index(
        "ix_items_embedding_hnsw",
        Item.embedding,
        postgresql_using="hnsw",  # or "ivfflat"
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": OPCLASS},
    )
    try:
        idx.create(bind=engine)
    except Exception:
        # Safe on re-runs / already exists
        pass

# --- 8) Tiny CRUD / KNN demo --------------------------------------------------
RUN_DEMO = secrets.get("RUN_DEMO", True)

if RUN_DEMO:
    with Session(engine) as session:
        # Insert a row
        session.add(Item(embedding=[1.0, 2.0, 3.0][:DIM]))
        session.commit()

        # KNN using the same metric as your index (here: l2)
        qvec = [1.0, 2.0, 3.1][:DIM]
        rows = session.scalars(
            select(Item).order_by(Item.embedding.l2_distance(qvec)).limit(5)
        ).all()
        print("Nearest IDs:", [r.id for r in rows])
