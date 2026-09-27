"""
Depth Metrics Calculation Module

Calculates comprehensive scientific validation metrics comparing observed vs predicted flood depths.

Metrics:
- MAE: Mean Absolute Error (cm)
- RMSE: Root Mean Square Error (cm)
- Bias: Mean Error (cm) (predicted - observed)
- MedAE: Median Absolute Error (cm)
- R²: Coefficient of Determination
- Pearson r: Linear correlation coefficient
- Spearman rho: Rank correlation coefficient
- Max Observed Depth (cm)
- Max Predicted Depth (cm)
- Peak Depth Error (cm)
- Underprediction Rate (% of points where predicted < observed)
- Overprediction Rate (% of points where predicted > observed)
"""

import math
from typing import List, Dict, Any, Optional

def calculate_depth_metrics(matched_records: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """
    Calculate scientific error and correlation metrics for paired observed & predicted depth records.
    """
    if not matched_records:
        return {
            "sample_count": 0,
            "mae_cm": None,
            "rmse_cm": None,
            "bias_cm": None,
            "median_ae_cm": None,
            "r2_score": None,
            "pearson_r": None,
            "spearman_rho": None,
            "max_observed_cm": None,
            "max_predicted_cm": None,
            "peak_depth_error_cm": None,
            "underprediction_rate_pct": None,
            "overprediction_rate_pct": None,
        }

    n = len(matched_records)
    y_obs = [r["observed_depth_cm"] for r in matched_records]
    y_pred = [r["predicted_depth_cm"] for r in matched_records]

    # 1. Basic Errors
    errors = [pred - obs for pred, obs in zip(y_pred, y_obs)]
    abs_errors = [abs(err) for err in errors]

    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(e**2 for e in errors) / n)
    bias = sum(errors) / n

    # 2. Median Absolute Error
    sorted_abs_errors = sorted(abs_errors)
    if n % 2 == 1:
        med_ae = sorted_abs_errors[n // 2]
    else:
        med_ae = (sorted_abs_errors[n // 2 - 1] + sorted_abs_errors[n // 2]) / 2.0

    # 3. Peak Depths
    max_obs = max(y_obs)
    max_pred = max(y_pred)
    peak_err = max_pred - max_obs

    # 4. Under / Overprediction Rates
    under_count = sum(1 for pred, obs in zip(y_pred, y_obs) if pred < obs)
    over_count = sum(1 for pred, obs in zip(y_pred, y_obs) if pred > obs)

    under_rate = round((under_count / n) * 100.0, 2)
    over_rate = round((over_count / n) * 100.0, 2)

    # 5. R² (Coefficient of Determination)
    mean_obs = sum(y_obs) / n
    ss_tot = sum((obs - mean_obs)**2 for obs in y_obs)
    ss_res = sum((obs - pred)**2 for obs, pred in zip(y_obs, y_pred))

    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # 6. Pearson Correlation (r)
    mean_pred = sum(y_pred) / n
    cov = sum((obs - mean_obs) * (pred - mean_pred) for obs, pred in zip(y_obs, y_pred))
    var_obs = sum((obs - mean_obs)**2 for obs in y_obs)
    var_pred = sum((pred - mean_pred)**2 for pred in y_pred)

    if var_obs > 0 and var_pred > 0:
        pearson_r = cov / (math.sqrt(var_obs) * math.sqrt(var_pred))
    else:
        pearson_r = 0.0

    # 7. Spearman Rank Correlation (rho)
    def rank_array(arr):
        sorted_indices = sorted(range(len(arr)), key=lambda i: arr[i])
        ranks = [0] * len(arr)
        for rank, idx in enumerate(sorted_indices):
            ranks[idx] = rank + 1
        return ranks

    rank_obs = rank_array(y_obs)
    rank_pred = rank_array(y_pred)
    mean_rank_obs = sum(rank_obs) / n
    mean_rank_pred = sum(rank_pred) / n

    cov_rank = sum((ro - mean_rank_obs) * (rp - mean_rank_pred) for ro, rp in zip(rank_obs, rank_pred))
    var_rank_obs = sum((ro - mean_rank_obs)**2 for ro in rank_obs)
    var_rank_pred = sum((rp - mean_rank_pred)**2 for rp in rank_pred)

    if var_rank_obs > 0 and var_rank_pred > 0:
        spearman_rho = cov_rank / (math.sqrt(var_rank_obs) * math.sqrt(var_rank_pred))
    else:
        spearman_rho = 0.0

    return {
        "sample_count": n,
        "mae_cm": round(mae, 2),
        "rmse_cm": round(rmse, 2),
        "bias_cm": round(bias, 2),
        "median_ae_cm": round(med_ae, 2),
        "r2_score": round(r2, 4),
        "pearson_r": round(pearson_r, 4),
        "spearman_rho": round(spearman_rho, 4),
        "max_observed_cm": round(max_obs, 2),
        "max_predicted_cm": round(max_pred, 2),
        "peak_depth_error_cm": round(peak_err, 2),
        "underprediction_rate_pct": under_rate,
        "overprediction_rate_pct": over_rate,
    }
