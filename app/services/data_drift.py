from typing import Dict, List
import math

def _ks_statistic(x: List[float], y: List[float]) -> float:
    x_sorted = sorted(x)
    y_sorted = sorted(y)

    n = len(x_sorted)
    m = len(y_sorted)

    i = 0
    j = 0
    cdf_x = 0.0
    cdf_y = 0.0
    d = 0.0

    while i < n and j < m:
        if x_sorted[i] <= y_sorted[j]:
            i += 1
            cdf_x = i / n
        else:
            j += 1
            cdf_y = j / m
        d = max(d, abs(cdf_x - cdf_y))

    while i < n:
        i += 1
        cdf_x = i / n
        d = max(d, abs(cdf_x - cdf_y))

    while j < m:
        j += 1
        cdf_y = j / m
        d = max(d, abs(cdf_x - cdf_y))

    return d

def detect_data_drift(reference: Dict[str, List[float]], current: Dict[str, List[float]], alpha: float = 0.05) -> Dict:
    """
    Data drift via KS test (2-samples).
    Decision rule:
      D > D_crit where D_crit = c(alpha) * sqrt((n+m)/(n*m))
      with c(alpha)=1.36 for alpha=0.05, ~1.63 for alpha=0.01
    """
    if alpha <= 0 or alpha >= 1:
        raise ValueError("alpha doit être entre 0 et 1")

    c_alpha = 1.36 if alpha == 0.05 else 1.63 if alpha == 0.01 else 1.36

    feature_results = {}
    drift_count = 0
    compared = 0

    common_features = sorted(set(reference.keys()).intersection(set(current.keys())))

    for feat in common_features:
        ref_vals = reference.get(feat, [])
        cur_vals = current.get(feat, [])

        if len(ref_vals) < 5 or len(cur_vals) < 5:
            feature_results[feat] = {
                "status": "skipped",
                "reason": "pas assez de données (min 5 valeurs par feature)",
            }
            continue

        n = len(ref_vals)
        m = len(cur_vals)

        d = _ks_statistic(ref_vals, cur_vals)
        d_crit = c_alpha * math.sqrt((n + m) / (n * m))

        drift_detected = d > d_crit
        compared += 1
        if drift_detected:
            drift_count += 1

        feature_results[feat] = {
            "status": "ok",
            "n_ref": n,
            "n_cur": m,
            "ks_stat": float(d),
            "ks_crit": float(d_crit),
            "drift_detected": bool(drift_detected)
        }

    global_drift = drift_count > 0

    return {
        "alpha": alpha,
        "features_compared": compared,
        "features_drifted": drift_count,
        "global_drift": bool(global_drift),
        "feature_results": feature_results
    }
  
