import os
import psycopg2

url = os.environ.get('PG_URL') or os.environ.get('DATABASE_URL')
if not url:
    raise SystemExit('Set PG_URL or DATABASE_URL in env')

conn = psycopg2.connect(url)
cur = conn.cursor()

expected_columns = {
    'conversation_id': 'VARCHAR(100)',
    'requested_by': 'VARCHAR(200)',
    'department': 'VARCHAR(100)',
    'natural_language': 'VARCHAR(5000)',
    'intent': 'VARCHAR(300)',
    'operation_type': 'VARCHAR(50)',
    'target_resource': 'VARCHAR(300)',
    'target_table': 'VARCHAR(100)',
    'affected_records': 'INTEGER',
    'action_json': 'JSONB',
    'execution_plan': 'JSONB',
    'parameters': 'JSONB',
    'risk_score': 'DOUBLE PRECISION',
    'risk_level': 'VARCHAR(20)',
    'risk_breakdown': 'JSONB',
    'reversibility': 'VARCHAR(30)',
    'data_scope': 'VARCHAR(30)',
    'regulatory_category': 'VARCHAR(30)',
    'policy_result': 'VARCHAR(20)',
    'policy_violations': 'JSONB',
    'decision': 'VARCHAR(20)',
    'confidence': 'DOUBLE PRECISION',
    'workflow_stage': 'VARCHAR(30)',
    'status': 'VARCHAR(30)',
    'execution_result': 'JSONB',
    'execution_logs': 'JSONB',
    'rollback_available': 'BOOLEAN',
    'rollback_status': 'VARCHAR(30)',
    'reviewed_by': 'VARCHAR(200)',
    'review_comment': 'VARCHAR(2000)',
    'executed_at': 'TIMESTAMPTZ',
    'completed_at': 'TIMESTAMPTZ',
}

# get existing columns
cur.execute("select column_name from information_schema.columns where table_schema='public' and table_name='actions'")
existing = {r[0] for r in cur.fetchall()}

for col, typ in expected_columns.items():
    if col in existing:
        print(f'{col} already exists')
    else:
        print(f'Adding column {col} {typ} as nullable')
        cur.execute(f'ALTER TABLE public.actions ADD COLUMN {col} {typ}')
        conn.commit()

# Create indexes if missing
indexes = {
    'ix_actions_conversation_id': 'conversation_id',
    'ix_actions_operation_type': 'operation_type',
    'ix_actions_risk_level': 'risk_level',
    'ix_actions_decision': 'decision',
    'ix_actions_workflow_stage': 'workflow_stage',
    'ix_actions_status': 'status',
    'ix_actions_created_at': 'created_at',
}
for idx, col in indexes.items():
    # check if index exists
    cur.execute("select to_regclass(%s)", (f'public.{idx}',))
    if cur.fetchone()[0]:
        print(f'index {idx} exists')
    else:
        print(f'creating index {idx} on {col}')
        cur.execute(f'CREATE INDEX IF NOT EXISTS {idx} ON public.actions ({col})')
        conn.commit()

cur.close()
conn.close()
print('done')
