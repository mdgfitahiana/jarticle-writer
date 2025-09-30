from db.engine import get_engine, session_scope
from db.repository import (
    create_article, list_articles, search_by_vector, delete_article
)

get_engine()  # initialize once

with session_scope() as s:
    a = create_article(
        s,
        title="Hello finance",
        content="Some financial article content",
        embedding=[0.01, 0.02, 0.03, 0.04, 0.05][:3],  # match your EMBEDDING_DIM
        source="manual",
        url=None,
        metadata={"sector": "banking"},
    )
    print("Created:", a.id)

with session_scope() as s:
    print("Total now:", len(list_articles(s, limit=5)))

with session_scope() as s:
    hits = search_by_vector(s, [0.01, 0.02, 0.03][:3], k=5)
    print("Search top IDs:", [h.id for h in hits])

# Cleanup
# with session_scope() as s:
#     delete_article(s, a.id)
