from fastapi import FastAPI
from app.schemas import EvaluateRequest
from app.services.metrics import compute_metrics
from app.services.drift import detect_performance_drift
from app.services.scoring import compute_score
from app.schemas import DataDriftRequest
from app.services.data_drift import detect_data_drift

app = FastAPI(title="Sentinel360 API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/evaluate")
def evaluate(payload: EvaluateRequest):
    metrics = compute_metrics(payload.y_true, payload.y_pred)

    drift = detect_performance_drift(
        current_rmse=metrics["rmse"],
        baseline_rmse=payload.baseline_rmse
    )

    score = compute_score(metrics, drift)

    return {
        "metrics": metrics,
        "performance_drift": drift,
        "score": score
    }

@app.post("/drift-data")
def drift_data(payload: DataDriftRequest):
    result = detect_data_drift(payload.reference, payload.current, payload.alpha)
    return result
