import os
import re

db_path = r"c:\Users\NISHAKART\Documents\GitHub\threshold-ai-governance\app\database\database.py"
with open(db_path, 'r', encoding='utf-8') as file:
    db_content = file.read()

if 'class AwareDateTime' not in db_content:
    aware_datetime_code = """
from datetime import timezone
from sqlalchemy import DateTime

class AwareDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
"""
    db_content = db_content.replace(
        'class JSONType(TypeDecorator):',
        aware_datetime_code + '\n\nclass JSONType(TypeDecorator):'
    )
    with open(db_path, 'w', encoding='utf-8') as file:
        file.write(db_content)
    print("Updated database.py")

models_dir = r"c:\Users\NISHAKART\Documents\GitHub\threshold-ai-governance\app\models"
for root, _, files in os.walk(models_dir):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            if 'DateTime(timezone=True)' in content:
                # Add import for AwareDateTime if not there
                if 'AwareDateTime' not in content:
                    content = content.replace(
                        'from app.database.database import Base', 
                        'from app.database.database import Base, AwareDateTime'
                    )
                    content = content.replace(
                        'from app.database.database import Base, GUID',
                        'from app.database.database import Base, GUID, AwareDateTime'
                    )
                    content = content.replace(
                        'from app.database.database import Base, GUID, JSONType',
                        'from app.database.database import Base, GUID, JSONType, AwareDateTime'
                    )
                
                # Replace DateTime(timezone=True) with AwareDateTime()
                content = content.replace('DateTime(timezone=True)', 'AwareDateTime()')
                
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(content)
                print(f"Updated {f}")
