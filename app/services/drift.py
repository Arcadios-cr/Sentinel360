from typing import Dict, Optional

def detect_performance_drift(
    current_rmse: float,
    baseline_rmse: Optional[float],
    warn_ratio: float = 1.10,   # +10%
    alert_ratio: float = 1.25   # +25%
) -> Dict:
    if baseline_rmse is None or baseline_rmse <= 0:
        return {
            "baseline_rmse": baseline_rmse,
            "current_rmse": current_rmse,
            "ratio": None,
            "delta": None,
            "severity": "unknown",
            "drift_detected": False,
            "reason": "baseline_rmse manquant ou invalide"
        }

    ratio = current_rmse / baseline_rmse
    delta = current_rmse - baseline_rmse

    if ratio >= alert_ratio:
        severity = "high"
        drift_detected = True
        reason = "dégradation forte de performance"
    elif ratio >= warn_ratio:
        severity = "medium"
        drift_detected = True
        reason = "dégradation modérée de performance"
    else:
        severity = "low"
        drift_detected = False
        reason = "performance stable"

    return {
        "baseline_rmse": float(baseline_rmse),
        "current_rmse": float(current_rmse),
        "ratio": float(ratio),
        "delta": float(delta),
        "severity": severity,
        "drift_detected": drift_detected,
        "reason": reason
    }