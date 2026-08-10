import os
import psycopg2

TABLES = ["actions", "review_queue", "audit_logs"]

url = os.environ.get("PG_URL") or os.environ.get("DATABASE_URL")
if not url:
    raise SystemExit("PG_URL or DATABASE_URL must be set")
if url.startswith("postgresql+psycopg2://"):
    url = url.replace("postgresql+psycopg2://", "postgresql://", 1)

conn = psycopg2.connect(url)
cur = conn.cursor()
for table in TABLES:
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    print(f"\n== {table} ==")
    for row in cur.fetchall():
        print(row)
cur.close()
conn.close()
