import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def run_evaluation():
    print("Loading models...")
    m_orig = joblib.load('market-model-review/kshetraiq_model.pkl')
    m_impr = joblib.load('market-model-review/kshetraiq_improved_model.pkl')
    
    # 1. Inspect supported categories
    dump_orig = m_orig.booster_.dump_model()
    dump_impr = m_impr.booster_.dump_model()
    
    cats_orig = dump_orig.get('pandas_categorical', [])
    cats_impr = dump_impr.get('pandas_categorical', [])
    
    crops_orig = cats_orig[3] if len(cats_orig) > 3 else []
    crops_impr = cats_impr[3] if len(cats_impr) > 3 else []
    
    mandis_orig = cats_orig[2] if len(cats_orig) > 2 else []
    mandis_impr = cats_impr[2] if len(cats_impr) > 2 else []
    
    print(f"Original model: {len(crops_orig)} crops, {len(mandis_orig)} mandis")
    print(f"Improved model: {len(crops_impr)} crops, {len(mandis_impr)} mandis")
    
    # 2. Load historical chronological AGMARKNET Varanasi Wheat dataset
    df = pd.read_csv('market-model-review/historical_agmarknet_varanasi.csv')
    df['Price Date'] = pd.to_datetime(df['Price Date'], format='%d-%b-%y')
    df = df.sort_values('Price Date').reset_index(drop=True)
    
    min_date = df['Price Date'].min()
    max_date = df['Price Date'].max()
    print(f"Chronological dataset: {len(df)} rows from {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
    
    # Split chronologically: Held-out test set is the most recent 20% of dates
    split_idx = int(len(df) * 0.8)
    test_df = df.iloc[split_idx:].copy().reset_index(drop=True)
    print(f"Held-out test set size: {len(test_df)} records (from {test_df['Price Date'].min().strftime('%Y-%m-%d')} to {test_df['Price Date'].max().strftime('%Y-%m-%d')})")
    
    # Prepare features for LightGBM
    # Features required: ["state_name", "district_name", "market_name", "crop", "variety", "year", "month", "day"]
    features_df = pd.DataFrame({
        "state_name": "Uttar Pradesh",
        "district_name": test_df["District Name"],
        "market_name": test_df["Market Name"],
        "crop": test_df["Commodity"],
        "variety": test_df["Variety"],
        "year": test_df["Price Date"].dt.year,
        "month": test_df["Price Date"].dt.month,
        "day": test_df["Price Date"].dt.day
    })
    
    for c in ["state_name", "district_name", "market_name", "crop", "variety"]:
        features_df[c] = features_df[c].astype("category")
        
    y_true = test_df["Modal Price (Rs./Quintal)"].astype(float).values
    
    # Predict with Original Model
    pred_orig = m_orig.predict(features_df)
    mae_orig = mean_absolute_error(y_true, pred_orig)
    rmse_orig = np.sqrt(mean_squared_error(y_true, pred_orig))
    r2_orig = r2_score(y_true, pred_orig)
    mape_orig = mape(y_true, pred_orig)
    
    # Predict with Improved Model
    pred_impr = m_impr.predict(features_df)
    mae_impr = mean_absolute_error(y_true, pred_impr)
    rmse_impr = np.sqrt(mean_squared_error(y_true, pred_impr))
    r2_impr = r2_score(y_true, pred_impr)
    mape_impr = mape(y_true, pred_impr)
    
    print("\n" + "="*70)
    print("CHRONOLOGICAL HELD-OUT TEST EVALUATION REPORT (Varanasi Wheat Series)")
    print("="*70)
    print(f"{'Metric':<25} | {'Original Model':<20} | {'Improved Model':<20}")
    print("-" * 70)
    print(f"{'Algorithm':<25} | {'LGBMRegressor (200t)':<20} | {'LGBMRegressor (500t)':<20}")
    print(f"{'MAE (Rs/Quintal)':<25} | {mae_orig:<20.2f} | {mae_impr:<20.2f}")
    print(f"{'RMSE (Rs/Quintal)':<25} | {rmse_orig:<20.2f} | {rmse_impr:<20.2f}")
    print(f"{'R² Score':<25} | {r2_orig:<20.4f} | {r2_impr:<20.4f}")
    print(f"{'MAPE (%)':<25} | {mape_orig:<20.2f}% | {mape_impr:<20.2f}%")
    print(f"{'Supported Commodities':<25} | {len(crops_orig):<20} | {len(crops_impr):<20}")
    print(f"{'Supported Mandis':<25} | {len(mandis_orig):<20} | {len(mandis_impr):<20}")
    print("="*70)
    
    # Comparison summary
    print(f"\nVerdict:")
    if mae_impr < mae_orig and r2_impr > r2_orig:
        print(f"-> Improved Model outperforms Original Model by reducing MAE by {mae_orig - mae_impr:.2f} Rs/Quintal ({((mae_orig - mae_impr)/mae_orig)*100:.1f}%) and increasing R² from {r2_orig:.4f} to {r2_impr:.4f}.")
    else:
        print(f"-> Original Model MAE: {mae_orig:.2f}, Improved Model MAE: {mae_impr:.2f}")

if __name__ == '__main__':
    run_evaluation()

