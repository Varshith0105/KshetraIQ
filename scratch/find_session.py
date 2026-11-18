import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import sqlite3
import json
from app.core.config import get_settings

db = get_settings().resolved_sqlite_db_path
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT analysis_id, created_at, updated_at, manifest_json FROM intelligence_analyses WHERE analysis_id LIKE '%99d50%'")
row = c.fetchone()
if row:
    print("Found ID:", row[0])
    print("Created at:", row[1])
    print("Updated at:", row[2])
    m = json.loads(row[3])
    for k, d in m.get("executed_models", {}).items():
        print(f"  {k}: status={d.get('status')} | error={d.get('error')}")
