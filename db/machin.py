from sqlalchemy import text

with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    print(conn.execute(text("select version()")).scalar())
