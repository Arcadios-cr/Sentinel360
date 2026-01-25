from pydantic import BaseModel
from typing import List, Optional, Dict

class EvaluateRequest(BaseModel):
    y_true: List[float]
    y_pred: List[float]
    baseline_rmse: Optional[float] = None

class DataDriftRequest(BaseModel):
    reference: Dict[str, List[float]]
    current: Dict[str, List[float]]
    alpha: float = 0.05