import os
import psycopg2

url = os.environ.get('PG_URL') or os.environ.get('DATABASE_URL')
if not url:
    raise SystemExit('Set PG_URL or DATABASE_URL in env')

conn = psycopg2.connect(url)
cur = conn.cursor()

# Check and add conversation_id to actions
cur.execute("select column_name from information_schema.columns where table_schema='public' and table_name='actions' and column_name='conversation_id'")
exists = cur.fetchone()
if exists:
    print('actions.conversation_id already exists')
else:
    print('Adding actions.conversation_id column...')
    cur.execute("ALTER TABLE public.actions ADD COLUMN conversation_id VARCHAR(100)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_actions_conversation_id ON public.actions (conversation_id)")
    conn.commit()
    print('Added and indexed actions.conversation_id')

cur.close()
conn.close()
