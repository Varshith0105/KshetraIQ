import joblib
import json

m = joblib.load('market-model-review/kshetraiq_improved_model.pkl')
dump = m.booster_.dump_model()
pcats = dump.get('pandas_categorical', [])
print(f"Total pandas_categorical arrays: {len(pcats)}")
for idx, col_cats in enumerate(pcats):
    col_name = dump['feature_names'][idx]
    if col_cats:
        print(f"Column '{col_name}': {len(col_cats)} categories. First 10: {col_cats[:10]}")
    else:
        print(f"Column '{col_name}': None (numeric)")

