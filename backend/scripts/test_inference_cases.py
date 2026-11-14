import joblib
import pandas as pd
import numpy as np

m = joblib.load('market-model-review/kshetraiq_improved_model.pkl')
dump = m.booster_.dump_model()
pcats = dump.get('pandas_categorical', [])

# Case 1: Known crop and mandi with raw .astype('category')
df1 = pd.DataFrame([{
    "state_name": "Andhra Pradesh",
    "district_name": "Guntur",
    "market_name": "Tenali",
    "crop": "Tomato",
    "variety": "Local",
    "year": 2026,
    "month": 11,
    "day": 10
}])
for c in ["state_name", "district_name", "market_name", "crop", "variety"]:
    df1[c] = df1[c].astype("category")

p1 = m.predict(df1)
print(f"Case 1 (raw astype category): {p1[0]:.2f}")

# Case 2: Exact categories set using dump['pandas_categorical']
df2 = pd.DataFrame([{
    "state_name": "Andhra Pradesh",
    "district_name": "Guntur",
    "market_name": "Tenali",
    "crop": "Tomato",
    "variety": "Local",
    "year": 2026,
    "month": 11,
    "day": 10
}])
for i, c in enumerate(["state_name", "district_name", "market_name", "crop", "variety"]):
    df2[c] = pd.Categorical(df2[c], categories=pcats[i])

p2 = m.predict(df2)
print(f"Case 2 (exact trained categories): {p2[0]:.2f}")

# Case 3: What if an UNKNOWN commodity or mandi is passed?
df3 = pd.DataFrame([{
    "state_name": "Andhra Pradesh",
    "district_name": "Guntur",
    "market_name": "NonExistentMarket",
    "crop": "DragonFruitUnknown",
    "variety": "UnknownVariety",
    "year": 2026,
    "month": 11,
    "day": 10
}])
for i, c in enumerate(["state_name", "district_name", "market_name", "crop", "variety"]):
    df3[c] = pd.Categorical(df3[c], categories=pcats[i])

p3 = m.predict(df3)
print(f"Case 3 (unknown category handled by pd.Categorical): {p3[0]:.2f}")

