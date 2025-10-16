from __future__ import annotations
import os
from typing import Any, Dict

def get_settings() -> Dict[str, Any]:
    try:
        import streamlit as st
        src = st.secrets
        get = lambda k, d=None: src.get(k, d)
    except Exception:
        get = lambda k, d=None: os.getenv(k, d)

    sslmode = str(get("DATABASE_SSLMODE", "require")).strip().lower()
    sslroot = str(get("DATABASE_SSLROOT", "")).strip()
    ca_pem  = str(get("SUPABASE_CA_PEM", "")).strip()

    # If quick mode is on, force-clear any CA to avoid verification.
    if sslmode == "require":
        sslroot = ""
        ca_pem = ""

    return {
        "host": str(get("DATABASE_HOST", "")).strip(),
        "port": int(str(get("DATABASE_PORT", "5432"))),
        "name": str(get("DATABASE_NAME", "postgres")).strip(),
        "user": str(get("DATABASE_USER", "")).strip(),
        "password": str(get("DATABASE_PASSWORD", "")),
        "sslmode": sslmode,
        "sslroot": sslroot,          # empty in quick mode
        "ca_pem": ca_pem,            # empty in quick mode
        "echo": str(get("SQLALCHEMY_ECHO", "false")).lower() in {"1", "true", "yes", "on"},
        "embedding_dim": int(str(get("EMBEDDING_DIM", "1536"))),
        "set_ivfflat_probes": int(str(get("IVFFLAT_PROBES", "10"))),
    }
