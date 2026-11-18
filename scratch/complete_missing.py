import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.intelligence_service import IntelligenceService
import json

svc = IntelligenceService()
with svc._conn() as conn:
    rows = conn.execute("SELECT analysis_id, manifest_json FROM intelligence_analyses WHERE workflow_type = 'plant'").fetchall()

for r in rows:
    aid = r['analysis_id']
    m = json.loads(r['manifest_json'])
    exec_m = m.get('executed_models', {})
    missing = [k for k, v in exec_m.items() if v.get('status') in ('NOT_RUN', 'PROCESSING')]
    if missing:
        print(f"Completing missing models {missing} for {aid}...")
        for mod in missing:
            try:
                svc.run_plant(aid, mod, m.get('user_id'))
                print(f"  {mod}: DONE")
            except Exception as e:
                print(f"  {mod}: FAILED ({e})")
        svc._generate_composite_2x2(aid, m.get('user_id'))
        print(f"Finished {aid}")
print("All done!")
