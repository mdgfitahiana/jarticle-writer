# utils/embeddings.py
from __future__ import annotations
import os

# Choose provider via env/secret: "openai" or "sentence_transformers"
PROVIDER = os.getenv("EMBED_PROVIDER", "openai").lower()
MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")  # openai default
DIM = int(os.getenv("EMBEDDING_DIM", "1536"))  # must match your DB usage

def embed_text(text: str) -> list[float]:
    text = (text or "").strip()
    if not text:
        return [0.0] * DIM

    if PROVIDER == "sentence_transformers":
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL)  # e.g. "all-MiniLM-L6-v2"
        v = _model.encode(text, normalize_embeddings=True)
        return v.tolist()

    # default: OpenAI
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    res = client.embeddings.create(model=MODEL, input=text)
    v = res.data[0].embedding
    # Optionally trim/pad to DIM if you force a specific size
    return v[:DIM] if len(v) >= DIM else v + [0.0] * (DIM - len(v))
