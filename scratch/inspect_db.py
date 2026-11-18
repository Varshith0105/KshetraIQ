import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import sqlite3
import json
from app.core.config import get_settings

db = get_settings().resolved_sqlite_db_path
print("Connecting to:", db)
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT analysis_id, manifest_json FROM intelligence_analyses ORDER BY created_at DESC LIMIT 5")
for r in c.fetchall():
    print("ID:", r[0])
    m = json.loads(r[1])
    wf = m.get("workflow_type")
    print("  Workflow:", wf)
    if wf == "plant":
        for k, d in m.get("executed_models", {}).items():
            print(f"    {k}: status={d.get('status')} | error={d.get('error')} | assets={d.get('visual_assets')}")
