from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy import text
from pgvector.sqlalchemy import Vector
from .config import get_settings

class Base(DeclarativeBase):
    pass

DIM = get_settings()["embedding_dim"]  # app-level expectation

class EmbeddingArticle(Base):
    __tablename__ = "embeddings_financial_articles"
    __table_args__ = {"schema": "public"}  # map to public.<table>

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str | None]
    content: Mapped[str]  # NOT NULL
    # DB column is 'public.vector' (no fixed dim in DDL). We still use Vector(DIM)
    # so SQLAlchemy gives you vector helpers (cosine/l2/ip).
    embedding: Mapped[list[float]] = mapped_column(Vector(DIM), nullable=False)
    source: Mapped[str | None]
    url: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )
    sent_to_stakeholders: Mapped[bool | None]
    # 'metadata' clashes with Base.metadata symbol; map Python attr -> DB column.
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
