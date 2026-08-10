import os
import psycopg2

url = os.environ.get('PG_URL') or os.environ.get('DATABASE_URL')
if not url:
    raise SystemExit('Set PG_URL or DATABASE_URL')

conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("select column_name from information_schema.columns where table_schema='public' and table_name='actions' and column_name='updated_at'")
if cur.fetchone():
    print('updated_at exists')
else:
    cur.execute("ALTER TABLE public.actions ADD COLUMN updated_at TIMESTAMPTZ")
    conn.commit()
    print('added updated_at')
cur.close()
conn.close()
