from typing import List, Dict
import math

def compute_metrics(y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true et y_pred doivent avoir la même taille")
    if len(y_true) == 0:
        raise ValueError("Les listes ne doivent pas être vides")

    n = len(y_true)
    errors = [t - p for t, p in zip(y_true, y_pred)]    

    mae = sum(abs(e) for e in errors) / n
    mse = sum(e * e for e in errors) / n
    rmse = math.sqrt(mse)

    mean_y = sum(y_true) / n
    ss_tot = sum((y - mean_y) ** 2 for y in y_true)
    ss_res = sum((y_true[i] - y_pred[i]) ** 2 for i in range(n))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    return {
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(rmse),
        "r2": float(r2),
    }
