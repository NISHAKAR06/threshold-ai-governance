import os
import psycopg2

PG_URL = os.environ.get('PG_URL') or os.environ.get('DATABASE_URL')
if PG_URL is None:
    raise SystemExit('PG_URL or DATABASE_URL must be set')
# psycopg2 needs a plain postgresql:// DSN
if PG_URL.startswith('postgresql+psycopg2://'):
    pg_conn = PG_URL.replace('postgresql+psycopg2://', 'postgresql://', 1)
else:
    pg_conn = PG_URL

conn = psycopg2.connect(pg_conn)
cur = conn.cursor()
cur.execute("SELECT version_num FROM alembic_version")
before = cur.fetchone()
print('before:', before)
cur.execute("UPDATE alembic_version SET version_num = %s", ('001_initial_schema',))
conn.commit()
cur.execute("SELECT version_num FROM alembic_version")
after = cur.fetchone()
print('after:', after)
cur.close()
conn.close()
