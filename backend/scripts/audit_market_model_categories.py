import sys
from pathlib import Path
import joblib

sys.path.insert(0, str(Path("backend").resolve()))

from app.services.market_price_service import POPULAR_COMMODITIES, POPULAR_MANDIS

model_path = Path("Agriverse_Models/kshetraiq_improved_model.pkl")
model = joblib.load(model_path)
dump = model.booster_.dump_model()
cats = dump.get("pandas_categorical", [])
states, districts, mandis, crops, varieties = cats[:5]

crop_set = {c.lower().strip(): c for c in crops}
mandi_set = {m.lower().strip(): m for m in mandis}
state_set = {s.lower().strip(): s for s in states}
dist_set = {d.lower().strip(): d for d in districts}

print("=== POPULAR COMMODITIES AUDIT ===")
commodity_mismatches = []
for item in POPULAR_COMMODITIES:
    cname = item["name"].lower().strip()
    match = cname in crop_set
    print(f"Commodity: {item['name']:30s} -> In Model: {match}")
    if not match:
        commodity_mismatches.append(item["name"])

print("\n=== POPULAR MANDIS AUDIT ===")
mandi_mismatches = []
for item in POPULAR_MANDIS:
    mname = item["name"].lower().strip()
    sname = item["state"].lower().strip()
    dname = item["district"].lower().strip()
    m_match = mname in mandi_set
    s_match = sname in state_set
    d_match = dname in dist_set
    print(f"Mandi: {item['name']:25s} | Mandi in Model: {m_match} | Dist: {d_match} | State: {s_match}")
    if not (m_match and s_match and d_match):
        mandi_mismatches.append(item)

print(f"\nTotal commodity mismatches: {len(commodity_mismatches)}")
print(f"Total mandi mismatches: {len(mandi_mismatches)}")

