import os
import psycopg2

def main():
    url = os.environ.get('PG_URL') or os.environ.get('DATABASE_URL')
    if not url:
        print('PG_URL or DATABASE_URL not set')
        return
    # psycopg2 expects a plain postgresql:// URL (no +driver)
    if url.startswith('postgresql+psycopg2://'):
        url = url.replace('postgresql+psycopg2://', 'postgresql://', 1)
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    tables = cur.fetchall()
    print('tables:', tables)
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
