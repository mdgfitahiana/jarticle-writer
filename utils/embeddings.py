# utils/embeddings.py
from __future__ import annotations
import os
from typing import List

# Provider/model config
PROVIDER = os.getenv("EMBED_PROVIDER", "openai").lower()
MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")  # openai default
DIM = int(os.getenv("EMBEDDING_DIM", "1536"))               # must match your DB usage

# --- Chunking config: prefer Streamlit secrets, then env, then defaults ---
def _get_chunk_params():
    # Defaults
    size_default = 1800
    overlap_default = 200

    # Try streamlit secrets first (if available)
    chunk_size = None
    chunk_overlap = None
    try:
        import streamlit as st  # only used to read secrets
        chunk_size = int(st.secrets.get("CHUNK_SIZE", size_default))
        chunk_overlap = int(st.secrets.get("CHUNK_OVERLAP", overlap_default))
    except Exception:
        # Fallback to environment variables
        chunk_size = int(os.getenv("CHUNK_SIZE", size_default))
        chunk_overlap = int(os.getenv("CHUNK_OVERLAP", overlap_default))

    # Safety: ensure sane values
    if chunk_size <= 0:
        chunk_size = size_default
    if chunk_overlap < 0:
        chunk_overlap = 0
    if chunk_overlap >= chunk_size:
        # Cap overlap to at most half of chunk_size
        chunk_overlap = max(0, chunk_size // 2)

    return chunk_size, chunk_overlap


def _chunk_text(text: str) -> List[str]:
    """
    Simple, robust character-based chunking with overlap.
    If you later add token-based chunking, you can swap this implementation.
    """
    chunk_size, chunk_overlap = _get_chunk_params()
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    step = max(1, chunk_size - chunk_overlap)
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += step
    return chunks


def _mean_pool(vectors: List[List[float]], dim: int) -> List[float]:
    """Mean-pool a list of equal-length vectors (dim) into one vector."""
    if not vectors:
        return [0.0] * dim
    # Initialize sum vector
    acc = [0.0] * dim
    for v in vectors:
        # Be tolerant: trim/pad each vector to expected dim
        if len(v) < dim:
            v = v + [0.0] * (dim - len(v))
        elif len(v) > dim:
            v = v[:dim]
        for i in range(dim):
            acc[i] += v[i]
    n = float(len(vectors))
    return [x / n for x in acc]


def _embed_single(text: str) -> List[float]:
    """Embed a single chunk to a vector of length DIM using the configured provider."""
    if PROVIDER == "sentence_transformers":
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL)  # e.g. "all-MiniLM-L6-v2"
        v = _model.encode(text, normalize_embeddings=True)
        v = v.tolist()
        return v[:DIM] if len(v) >= DIM else v + [0.0] * (DIM - len(v))

    # default: OpenAI
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    res = client.embeddings.create(model=MODEL, input=text)
    v = res.data[0].embedding
    return v[:DIM] if len(v) >= DIM else v + [0.0] * (DIM - len(v))


def embed_text(text: str) -> List[float]:
    """
    Embed (possibly long) text:
    - Split into overlapping chunks using CHUNK_SIZE / CHUNK_OVERLAP from Streamlit secrets.
    - Embed each chunk.
    - Mean-pool the chunk embeddings to a single vector (length = DIM).
    """
    text = (text or "").strip()
    if not text:
        return [0.0] * DIM

    chunks = _chunk_text(text)
    vectors = [_embed_single(c) for c in chunks]
    return _mean_pool(vectors, DIM)
