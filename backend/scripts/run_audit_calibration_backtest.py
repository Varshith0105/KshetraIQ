import sys
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

def main():
    print("=" * 80)
    print("AUDIT SECTION 2 & 3: CALIBRATION, UNCERTAINTY INTERVALS & HORIZON BACKTEST")
    print("=" * 80)
    
    # Load model
    model = joblib.load('Agriverse_Models/kshetraiq_improved_model.pkl')
    
    # Load dataset
    df = pd.read_csv('market-model-review/historical_agmarknet_varanasi.csv')
    df['Price Date'] = pd.to_datetime(df['Price Date'], format='%d-%b-%y')
    df = df.sort_values('Price Date').reset_index(drop=True)
    
    total_len = len(df)
    print(f"Total dataset: {total_len} records ({df['Price Date'].min().strftime('%Y-%m-%d')} to {df['Price Date'].max().strftime('%Y-%m-%d')})")
    
    # Chronological partition:
    # 80% Train/Pre-evaluation (4,520 records)
    # 10% Calibration partition (565 records: ~2019 to ~2021)
    # 10% Test / Verification partition (566 records: ~2021 to 2023-12-30)
    idx_80 = int(total_len * 0.80)
    idx_90 = int(total_len * 0.90)
    
    train_df = df.iloc[:idx_80].copy().reset_index(drop=True)
    cal_df = df.iloc[idx_80:idx_90].copy().reset_index(drop=True)
    test_df = df.iloc[idx_90:].copy().reset_index(drop=True)
    
    print(f"Partition 1 (Pre/Train): {len(train_df)} rows ({train_df['Price Date'].min().date()} to {train_df['Price Date'].max().date()})")
    print(f"Partition 2 (Calibration): {len(cal_df)} rows ({cal_df['Price Date'].min().date()} to {cal_df['Price Date'].max().date()})")
    print(f"Partition 3 (Held-out Test): {len(test_df)} rows ({test_df['Price Date'].min().date()} to {test_df['Price Date'].max().date()})")
    
    def prepare_lgbm_features(sub_df):
        feat = pd.DataFrame({
            "state_name": "Uttar Pradesh",
            "district_name": sub_df["District Name"],
            "market_name": sub_df["Market Name"],
            "crop": sub_df["Commodity"],
            "variety": sub_df["Variety"],
            "year": sub_df["Price Date"].dt.year,
            "month": sub_df["Price Date"].dt.month,
            "day": sub_df["Price Date"].dt.day
        })
        for c in ["state_name", "district_name", "market_name", "crop", "variety"]:
            feat[c] = feat[c].astype("category")
        return feat
    
    # -------------------------------------------------------------
    # SECTION 2: CONFIDENCE INTERVAL & CONFORMAL CALIBRATION AUDIT
    # -------------------------------------------------------------
    cal_feat = prepare_lgbm_features(cal_df)
    y_cal = cal_df["Modal Price (Rs./Quintal)"].astype(float).values
    pred_cal = model.predict(cal_feat)
    
    cal_signed_residuals = y_cal - pred_cal
    cal_abs_errors = np.abs(y_cal - pred_cal)
    
    cal_mae = mean_absolute_error(y_cal, pred_cal)
    cal_rmse = np.sqrt(mean_squared_error(y_cal, pred_cal))
    
    # Conformal absolute quantile for 95% coverage:
    # conformal quantile at ceil((n+1)*0.95)/n
    n_cal = len(y_cal)
    q_level = min(1.0, np.ceil((n_cal + 1) * 0.95) / n_cal)
    q_conformal_95 = float(np.quantile(cal_abs_errors, q_level))
    
    # Empirical signed quantiles (2.5% and 97.5%)
    q_lower_2_5 = float(np.quantile(cal_signed_residuals, 0.025))
    q_upper_97_5 = float(np.quantile(cal_signed_residuals, 0.975))
    
    print("\n" + "=" * 70)
    print("CALIBRATION PARTITION METRICS & QUANTILE EXTRACTION:")
    print("=" * 70)
    print(f"Calibration MAE: Rs. {cal_mae:.2f}/Q | RMSE: Rs. {cal_rmse:.2f}/Q")
    print(f"Calibration 95% Conformal Absolute Bound: ± Rs. {q_conformal_95:.2f}/Q")
    print(f"Calibration 2.5% Signed Residual Bound: Rs. {q_lower_2_5:.2f}/Q")
    print(f"Calibration 97.5% Signed Residual Bound: Rs. {q_upper_97_5:.2f}/Q")
    
    # Evaluate on held-out test partition
    test_feat = prepare_lgbm_features(test_df)
    y_test = test_df["Modal Price (Rs./Quintal)"].astype(float).values
    pred_test = model.predict(test_feat)
    
    test_mae = mean_absolute_error(y_test, pred_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, pred_test))
    
    # Evaluate Coverage under different interval formulations on held-out test set
    cov_mae = np.mean((y_test >= (pred_test - cal_mae)) & (y_test <= (pred_test + cal_mae))) * 100
    
    sigma_est = cal_mae / 0.7979
    half_width_gauss = 1.96 * sigma_est
    cov_gauss = np.mean((y_test >= (pred_test - half_width_gauss)) & (y_test <= (pred_test + half_width_gauss))) * 100
    
    half_width_naive_196 = 1.96 * cal_mae
    cov_naive_196 = np.mean((y_test >= (pred_test - half_width_naive_196)) & (y_test <= (pred_test + half_width_naive_196))) * 100
    
    cov_conformal = np.mean((y_test >= (pred_test - q_conformal_95)) & (y_test <= (pred_test + q_conformal_95))) * 100
    cov_asymmetric = np.mean((y_test >= (pred_test + q_lower_2_5)) & (y_test <= (pred_test + q_upper_97_5))) * 100
    
    print("\n" + "=" * 70)
    print("HELD-OUT TEST COVERAGE VERIFICATION (566 Chronological Future Observations):")
    print("=" * 70)
    print(f"Test Set Ground Truth MAE: Rs. {test_mae:.2f}/Q | RMSE: Rs. {test_rmse:.2f}/Q")
    print(f"{'Methodology':<40} | {'Half-Width / Bound':<20} | {'Empirical Coverage':<18}")
    print("-" * 70)
    print(f"{'A. Approximate Uncertainty (± MAE)':<40} | {'± Rs. ' + str(round(cal_mae, 1)):<20} | {cov_mae:<17.2f}%")
    print(f"{'B. Gaussian Proxy 1.96*(MAE/0.798)':<40} | {'± Rs. ' + str(round(half_width_gauss, 1)):<20} | {cov_gauss:<17.2f}%")
    print(f"{'C. Naive Multiplier (± 1.96*MAE)':<40} | {'± Rs. ' + str(round(half_width_naive_196, 1)):<20} | {cov_naive_196:<17.2f}%")
    print(f"{'D. Conformal Calibrated (95%)':<40} | {'± Rs. ' + str(round(q_conformal_95, 1)):<20} | {cov_conformal:<17.2f}%")
    print(f"{'E. Asymmetric Quantile Interval':<40} | {f'[{q_lower_2_5:.1f}, +{q_upper_97_5:.1f}]':<20} | {cov_asymmetric:<17.2f}%")
    print("=" * 70)
    
    # -------------------------------------------------------------
    # SECTION 3: SEVEN-DAY FORECAST QUALITY & CHRONOLOGICAL BACKTEST
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("SECTION 3: CHRONOLOGICAL MULTI-HORIZON BACKTEST (Model vs. Baselines)")
    print("=" * 80)
    
    horizons = [1, 3, 5, 7, 14]
    monthly_means = train_df.groupby(train_df["Price Date"].dt.month)["Modal Price (Rs./Quintal)"].mean().to_dict()
    
    all_test_preds = model.predict(test_feat)
    all_test_actuals = y_test
    all_test_months = test_df["Price Date"].dt.month.values
    all_seasonal_preds = np.array([monthly_means.get(m, 1500.0) for m in all_test_months])
    
    results = []
    for h in horizons:
        y_true_h = all_test_actuals[h:]
        y_model_h = all_test_preds[h:]
        y_naive_h = all_test_actuals[:-h]
        y_season_h = all_seasonal_preds[h:]
        
        actual_moves = np.sign(y_true_h - y_naive_h)
        model_moves = np.sign(y_model_h - y_naive_h)
        
        mae_m = mean_absolute_error(y_true_h, y_model_h)
        rmse_m = np.sqrt(mean_squared_error(y_true_h, y_model_h))
        r2_m = r2_score(y_true_h, y_model_h)
        
        mae_n = mean_absolute_error(y_true_h, y_naive_h)
        rmse_n = np.sqrt(mean_squared_error(y_true_h, y_naive_h))
        r2_n = r2_score(y_true_h, y_naive_h)
        
        mae_s = mean_absolute_error(y_true_h, y_season_h)
        rmse_s = np.sqrt(mean_squared_error(y_true_h, y_season_h))
        r2_s = r2_score(y_true_h, y_season_h)
        
        non_zero = actual_moves != 0
        if np.sum(non_zero) > 0:
            dir_acc = np.mean(actual_moves[non_zero] == model_moves[non_zero]) * 100
        else:
            dir_acc = 50.0
            
        results.append({
            "horizon": f"{h}-day",
            "model_mae": mae_m, "model_rmse": rmse_m, "model_r2": r2_m, "dir_acc": dir_acc,
            "naive_mae": mae_n, "naive_rmse": rmse_n, "naive_r2": r2_n,
            "season_mae": mae_s, "season_rmse": rmse_s, "season_r2": r2_s,
        })
        
    print(f"{'Horizon':<8} | {'Model MAE':<10} | {'Naive MAE':<10} | {'Season MAE':<10} | {'Model R²':<10} | {'Naive R²':<10} | {'Dir Acc (%)':<12}")
    print("-" * 80)
    for r in results:
        print(f"{r['horizon']:<8} | Rs.{r['model_mae']:<7.1f} | Rs.{r['naive_mae']:<7.1f} | Rs.{r['season_mae']:<7.1f} | {r['model_r2']:<10.3f} | {r['naive_r2']:<10.3f} | {r['dir_acc']:<11.1f}%")
    print("=" * 80)

if __name__ == '__main__':
    main()
