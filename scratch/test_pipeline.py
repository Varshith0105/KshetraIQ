import sys
sys.path.insert(0, 'backend')
from pathlib import Path
from app.services.intelligence_service import IntelligenceService
import time
import json

test_img = None
for p in Path('.uploads').rglob('*'):
    if p.suffix.lower() in ['.jpg', '.jpeg', '.png'] and 'original' in p.name:
        test_img = p
        break
if not test_img:
    for p in Path('capstone-final').rglob('*'):
        if p.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            test_img = p
            break

print('Testing with image:', test_img)
content = test_img.read_bytes()
svc = IntelligenceService()
res = svc.create_plant(content, test_img.name, 'test_user')
aid = res['analysis_id']
print('Created analysis ID:', aid)

for i in range(40):
    time.sleep(3)
    m = svc.get(aid, 'test_user')
    exec_m = m['executed_models']
    statuses = {k: v['status'] for k, v in exec_m.items()}
    print(f'[{i*3}s] Statuses: {statuses}')
    if all(s in ['COMPLETED', 'FAILED'] for s in statuses.values()):
        break

print('\n--- FINAL EXECUTION SUMMARY ---')
for k, v in m['executed_models'].items():
    print(f"Model: {k}")
    print(f"  Status: {v['status']}")
    print(f"  Runtime: {v.get('execution_time_sec')}s")
    print(f"  Assets: {v.get('visual_assets')}")
    if v.get('result'):
        print(f"  Result: {json.dumps(v['result'], indent=2)[:300]}...")
    if v.get('error'):
        print(f"  Error: {v['error']}")
print('Composite 2x2:', m.get('composite_2x2'))
