from __future__ import annotations
import os
from typing import Any, Dict

def get_settings() -> Dict[str, Any]:
    """
    Load DB settings from Streamlit Secrets if available, else env vars.
    Works in local + Streamlit Cloud + other hosts.
    """
    try:
        import streamlit as st  # only available in Streamlit runs
        src = st.secrets
        get = lambda k, d=None: src.get(k, d)
    except Exception:
        get = lambda k, d=None: os.getenv(k, d)

    return {
        "host": str(get("DATABASE_HOST", "")).strip(),
        "port": int(str(get("DATABASE_PORT", "5432"))),
        "name": str(get("DATABASE_NAME", "postgres")).strip(),
        "user": str(get("DATABASE_USER", "")).strip(),
        "password": str(get("DATABASE_PASSWORD", "")),
        "sslmode": str(get("DATABASE_SSLMODE", "verify-full")),
        # If provided, use this PEM; else prefer system store.
        "ca_pem": str(get("SUPABASE_CA_PEM", "")).strip(),
        "echo": str(get("SQLALCHEMY_ECHO", "false")).lower() in {"1","true","yes","on"},
        # App-specific:
        "embedding_dim": int(str(get("EMBEDDING_DIM", "1536"))),  # set your true dim
        "set_ivfflat_probes": int(str(get("IVFFLAT_PROBES", "10"))),  # 1..n
    }
