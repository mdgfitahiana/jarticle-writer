from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy import text
from pgvector.sqlalchemy import Vector
from .config import get_settings

class Base(DeclarativeBase):
    pass

DIM = get_settings()["embedding_dim"]

class EmbeddingArticle(Base):
    __tablename__ = "vector_embeddings"
    __table_args__ = {"schema": "public"}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str | None]
    content: Mapped[str]                   # NOT NULL
    embedding: Mapped[list[float]] = mapped_column(Vector(DIM), nullable=False)
    embedding_dimension: Mapped[int | None] = int(get_settings().get('embedding_dim', 1536))
    source: Mapped[str | None]
    url: Mapped[str | None]
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )
    sent_to_stakeholders: Mapped[bool | None]
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
