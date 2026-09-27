import math
from typing import List, Dict, Any, Optional

class TemporalMetrics:
    """
    Computes hydrologic and forecast skill metrics for temporal gauge validation.
    Includes continuous statistics (MAE, RMSE, Bias, R², Pearson, Spearman, NSE, KGE),
    peak characteristics, horizon decay skill (+30 to +180 min), and categorical event detection metrics.
    Handles empty / null datasets safely.
    """

    @staticmethod
    def calculate_continuous_metrics(obs: List[float], pred: List[float]) -> Dict[str, Any]:
        if not obs or not pred or len(obs) != len(pred) or len(obs) == 0:
            return {
                "sample_count": 0,
                "mae_cm": None,
                "rmse_cm": None,
                "bias_cm": None,
                "median_ae_cm": None,
                "r2_score": None,
                "pearson_r": None,
                "spearman_rho": None,
                "nse": None,
                "kge": None,
                "peak_observed_cm": None,
                "peak_predicted_cm": None,
                "peak_depth_error_cm": None,
                "underprediction_rate_pct": None,
                "overprediction_rate_pct": None
            }

        n = len(obs)
        errors = [p - o for o, p in zip(obs, pred)]
        abs_errors = [abs(e) for e in errors]

        mae = sum(abs_errors) / n
        rmse = math.sqrt(sum(e ** 2 for e in errors) / n)
        bias = sum(errors) / n

        sorted_ae = sorted(abs_errors)
        median_ae = sorted_ae[n // 2] if n % 2 != 0 else (sorted_ae[n // 2 - 1] + sorted_ae[n // 2]) / 2.0

        mean_obs = sum(obs) / n
        mean_pred = sum(pred) / n

        ss_tot = sum((o - mean_obs) ** 2 for o in obs)
        ss_res = sum(e ** 2 for e in errors)

        # R² score
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-9 else 0.0

        # NSE (Nash-Sutcliffe Efficiency)
        nse = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-9 else 0.0

        # Pearson correlation
        var_obs = sum((o - mean_obs) ** 2 for o in obs)
        var_pred = sum((p - mean_pred) ** 2 for p in pred)
        cov = sum((o - mean_obs) * (p - mean_pred) for o, p in zip(obs, pred))

        if var_obs > 1e-9 and var_pred > 1e-9:
            pearson_r = cov / math.sqrt(var_obs * var_pred)
        else:
            pearson_r = 0.0

        # Spearman rank correlation
        def rank_array(arr):
            sorted_indices = sorted(range(len(arr)), key=lambda i: arr[i])
            ranks = [0.0] * len(arr)
            for rank, idx in enumerate(sorted_indices):
                ranks[idx] = float(rank + 1)
            return ranks

        rank_obs = rank_array(obs)
        rank_pred = rank_array(pred)
        mean_ro = sum(rank_obs) / n
        mean_rp = sum(rank_pred) / n
        cov_r = sum((ro - mean_ro) * (rp - mean_rp) for ro, rp in zip(rank_obs, rank_pred))
        var_ro = sum((ro - mean_ro) ** 2 for ro in rank_obs)
        var_rp = sum((rp - mean_rp) ** 2 for rp in rank_pred)

        if var_ro > 1e-9 and var_rp > 1e-9:
            spearman_rho = cov_r / math.sqrt(var_ro * var_rp)
        else:
            spearman_rho = 0.0

        # KGE (Kling-Gupta Efficiency)
        if mean_obs > 1e-9 and var_obs > 1e-9 and var_pred > 1e-9:
            r_kge = pearson_r
            alpha_kge = math.sqrt(var_pred / n) / math.sqrt(var_obs / n) if var_obs > 0 else 1.0
            beta_kge = mean_pred / mean_obs if mean_obs > 0 else 1.0
            kge = 1.0 - math.sqrt((r_kge - 1.0) ** 2 + (alpha_kge - 1.0) ** 2 + (beta_kge - 1.0) ** 2)
        else:
            kge = None

        peak_obs = max(obs)
        peak_pred = max(pred)
        peak_error = peak_pred - peak_obs

        underpredict_count = sum(1 for e in errors if e < 0)
        overpredict_count = sum(1 for e in errors if e > 0)

        return {
            "sample_count": n,
            "mae_cm": round(mae, 2),
            "rmse_cm": round(rmse, 2),
            "bias_cm": round(bias, 2),
            "median_ae_cm": round(median_ae, 2),
            "r2_score": round(r2, 4),
            "pearson_r": round(pearson_r, 4),
            "spearman_rho": round(spearman_rho, 4),
            "nse": round(nse, 4) if nse is not None else None,
            "kge": round(kge, 4) if kge is not None else None,
            "peak_observed_cm": round(peak_obs, 2),
            "peak_predicted_cm": round(peak_pred, 2),
            "peak_depth_error_cm": round(peak_error, 2),
            "underprediction_rate_pct": round((underpredict_count / n) * 100.0, 1),
            "overprediction_rate_pct": round((overpredict_count / n) * 100.0, 1)
        }

    @staticmethod
    def calculate_threshold_metrics(obs: List[float], pred: List[float], threshold_cm: float = 10.0) -> Dict[str, Any]:
        if not obs or not pred or len(obs) != len(pred) or len(obs) == 0:
            return {
                "threshold_cm": threshold_cm,
                "tp": 0, "tn": 0, "fp": 0, "fn": 0,
                "precision": None, "recall_pod": None, "f1_score": None, "csi": None, "far": None
            }

        tp = sum(1 for o, p in zip(obs, pred) if o >= threshold_cm and p >= threshold_cm)
        tn = sum(1 for o, p in zip(obs, pred) if o < threshold_cm and p < threshold_cm)
        fp = sum(1 for o, p in zip(obs, pred) if o < threshold_cm and p >= threshold_cm)
        fn = sum(1 for o, p in zip(obs, pred) if o >= threshold_cm and p < threshold_cm)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        csi = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
        far = fp / (tp + fp) if (tp + fp) > 0 else 0.0

        return {
            "threshold_cm": threshold_cm,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "precision": round(precision, 4),
            "recall_pod": round(recall, 4),
            "f1_score": round(f1, 4),
            "csi": round(csi, 4),
            "far": round(far, 4)
        }
