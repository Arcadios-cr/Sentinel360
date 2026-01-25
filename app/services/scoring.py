from typing import Dict

def compute_score(metrics: Dict, drift: Dict) -> int:
    rmse = float(metrics.get("rmse", 0.0))
    baseline = drift.get("baseline_rmse", None)

    # 1) Score performance (0..100)
    # Si baseline dispo : score basé sur ratio
    if baseline is not None and isinstance(baseline, (int, float)) and baseline > 0:
        ratio = rmse / baseline  # 1.0 = pareil, >1.0 = pire
        # mapping simple :
        # ratio <=1.0 -> 100
        # ratio >=2.0 -> 0
        score_perf = int(max(0, min(100, 100 * (2.0 - ratio))))
    else:
        # fallback : rmse absolu
        # rmse 0.0 => 100 / rmse 1.0 => 0 (adaptable)
        score_perf = int(max(0, min(100, 100 * (1.0 - rmse))))

    # 2) Pénalité drift
    severity = drift.get("severity", "unknown")
    if severity == "high":
        penalty = 40
    elif severity == "medium":
        penalty = 20
    elif severity == "low":
        penalty = 0
    else:
        penalty = 10  # unknown => petite pénalité

    # 3) Score final
    score = int(0.7 * score_perf + 0.3 * (100 - penalty))
    score = max(0, min(100, score))
    return score
