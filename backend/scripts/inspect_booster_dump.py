import joblib
import json

m = joblib.load('market-model-review/kshetraiq_improved_model.pkl')
booster = m.booster_
dump = booster.dump_model()
print("Keys in booster dump:", list(dump.keys()))
print("feature_names in dump:", dump.get('feature_names'))
print("feature_infos in dump:")
finfos = dump.get('feature_infos', {})
for k, v in finfos.items():
    if isinstance(v, list):
        print(f"  {k}: {len(v)} entries (sample: {v[:5]})")
    elif isinstance(v, dict):
        print(f"  {k}: dict with keys {list(v.keys())}")
    else:
        print(f"  {k}: {type(v)}")

# Also check pandas_categorical in model_to_string
m_str = booster.model_to_string()
for line in m_str.split('\n')[:40]:
    if any(term in line for term in ['pandas_categorical', 'categorical_feature', 'feature_names']):
        print("Model string header:", line[:200])

