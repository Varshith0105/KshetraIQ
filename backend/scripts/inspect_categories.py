import joblib
import pandas as pd
import numpy as np

m = joblib.load('market-model-review/kshetraiq_improved_model.pkl')
print("Model attributes:")
for k, v in m.__dict__.items():
    if not k.startswith('_'):
        print(f"  {k}: {type(v)}")
    else:
        print(f"  [private] {k}: {type(v)}")

# Check if model has _pandas_categorical
if hasattr(m, '_pandas_categorical'):
    cats = m._pandas_categorical
    print(f"Stored _pandas_categorical length: {len(cats)}")
    feature_names = m.feature_name_
    for i, c in enumerate(cats):
        if c is not None:
            print(f"Feature '{feature_names[i]}' has {len(c)} categories.")
            print(f"  Sample: {list(c[:10])}")
else:
    print("No _pandas_categorical attribute on model.")

