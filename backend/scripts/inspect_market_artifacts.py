import joblib
import sys
import os
import pandas as pd
import numpy as np

def inspect_model(path):
    print(f"\n{'='*50}\nInspecting: {path}\n{'='*50}")
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")
    
    try:
        model = joblib.load(path)
    except Exception as e:
        print(f"FAILED TO LOAD with joblib: {e}")
        return None
        
    print(f"Model type: {type(model)}")
    print(f"Class name: {model.__class__.__name__}")
    print(f"Module: {model.__class__.__module__}")
    
    # Check attributes
    for attr in ['n_estimators', 'learning_rate', 'num_leaves', 'random_state', 'n_features_', 'n_features_in_']:
        if hasattr(model, attr):
            print(f"  {attr}: {getattr(model, attr)}")
            
    if hasattr(model, 'feature_name_'):
        print(f"feature_name_: {model.feature_name_}")
    elif hasattr(model, 'feature_names_in_'):
        print(f"feature_names_in_: {model.feature_names_in_}")
        
    booster = getattr(model, 'booster_', None)
    if booster:
        print(f"Booster num_trees: {booster.num_trees()}")
        print(f"Booster feature_names: {booster.feature_name()}")
        
        # Check if pandas categorical information is stored
        if hasattr(model, '_pandas_categorical'):
            cats = model._pandas_categorical
            print(f"_pandas_categorical count: {len(cats)}")
            for i, col_cats in enumerate(cats):
                col_name = model.feature_name_[i] if hasattr(model, 'feature_name_') else f"col_{i}"
                if col_cats is not None:
                    print(f"  {col_name}: {len(col_cats)} unique categories (sample: {list(col_cats[:5])})")
                else:
                    print(f"  {col_name}: numeric (None)")

    # Test inference with sample inputs
    test_df = pd.DataFrame([{
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
        test_df[c] = test_df[c].astype("category")
        
    try:
        pred = model.predict(test_df)
        print(f"Inference test successful! Predicted price: {pred[0]:.2f}")
    except Exception as e:
        print(f"Inference test failed: {e}")
        
    return model

if __name__ == '__main__':
    m1 = inspect_model('market-model-review/kshetraiq_model.pkl')
    m2 = inspect_model('market-model-review/kshetraiq_improved_model.pkl')
