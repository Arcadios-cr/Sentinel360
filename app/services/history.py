from pathlib import Path
from typing import Any, Dict, List, Optional
import json
from datetime import datetime, timezone, timedelta

def _data_dir() -> Path:
    # .../app/services/history.py -> parents[1] = .../app
    d = Path(__file__).resolve().parents[1] / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _safe_model_id(model_id: str) -> str:
    # évite les / et trucs bizarres dans le nom de fichier
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in model_id)

def _model_file(model_id: str) -> Path:
    return _data_dir() / f"evals_{_safe_model_id(model_id)}.json"

def _parse_ts(ts: str) -> datetime:
    # on accepte "2026-02-01T12:00:00Z"
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)

def list_models() -> List[Dict[str, Any]]:
    """
    Liste tous les modèles ayant des évaluations enregistrées.
    Retourne pour chaque modèle : id, nombre d'évaluations, dernière évaluation.
    """
    data_dir = _data_dir()
    models = []
    
    for file_path in data_dir.glob("evals_*.json"):
        # Extraire le model_id du nom de fichier
        model_id = file_path.stem.replace("evals_", "")
        
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    # Trier par timestamp pour obtenir le dernier
                    sorted_data = sorted(
                        [d for d in data if "timestamp" in d],
                        key=lambda x: _parse_ts(x["timestamp"])
                    )
                    last_eval = sorted_data[-1] if sorted_data else None
                    last_score = last_eval.get("score") if last_eval else None
                    last_timestamp = last_eval.get("timestamp") if last_eval else None
                    
                    models.append({
                        "model_id": model_id,
                        "evaluation_count": len(data),
                        "last_score": last_score,
                        "last_evaluation": last_timestamp
                    })
        except (json.JSONDecodeError, KeyError):
            continue
    
    # Trier par score décroissant (meilleurs modèles en premier)
    models.sort(key=lambda x: x.get("last_score") or 0, reverse=True)
    return models

def store_evaluation(model_id: str, evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ajoute une évaluation dans un fichier JSON par modèle.
    Return = l'objet stocké (avec timestamp si manquant).
    """
    if "timestamp" not in evaluation:
        evaluation["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    path = _model_file(model_id)

    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = []
    else:
        data = []

    data.append(evaluation)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return evaluation

def list_evaluations(
    model_id: str,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    limit: int = 200
) -> List[Dict[str, Any]]:
    path = _model_file(model_id)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        if not isinstance(data, list):
            return []

    if from_ts:
        from_dt = _parse_ts(from_ts)
    else:
        from_dt = None

    if to_ts:
        to_dt = _parse_ts(to_ts)
    else:
        to_dt = None

    out = []
    for item in data:
        ts = item.get("timestamp")
        if not ts:
            continue
        dt = _parse_ts(ts)

        if from_dt and dt < from_dt:
            continue
        if to_dt and dt > to_dt:
            continue

        out.append(item)

    # tri par date croissante (bien pour les courbes)
    out.sort(key=lambda x: _parse_ts(x["timestamp"]))
    return out[-max(1, limit):]

def compare_models(model_a: str, model_b: str, window_days: int = 7) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=window_days)

    a_hist = list_evaluations(model_a, from_ts=start.isoformat().replace("+00:00", "Z"), limit=10000)
    b_hist = list_evaluations(model_b, from_ts=start.isoformat().replace("+00:00", "Z"), limit=10000)

    def _avg(hist: List[Dict[str, Any]], key_path: List[str]) -> Optional[float]:
        vals = []
        for item in hist:
            cur = item
            ok = True
            for k in key_path:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    ok = False
                    break
            if ok and isinstance(cur, (int, float)):
                vals.append(float(cur))
        return (sum(vals) / len(vals)) if vals else None

    a_avg_score = _avg(a_hist, ["score"])
    b_avg_score = _avg(b_hist, ["score"])
    a_avg_rmse = _avg(a_hist, ["metrics", "rmse"])
    b_avg_rmse = _avg(b_hist, ["metrics", "rmse"])

    # winner = meilleur score moyen
    winner = None
    if a_avg_score is not None and b_avg_score is not None:
        winner = model_a if a_avg_score >= b_avg_score else model_b

    def _last(hist: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return hist[-1] if hist else None

    return {
        "window_days": window_days,
        "model_a": {
            "id": model_a,
            "n": len(a_hist),
            "avg_score": a_avg_score,
            "avg_rmse": a_avg_rmse,
            "last": _last(a_hist)
        },
        "model_b": {
            "id": model_b,
            "n": len(b_hist),
            "avg_score": b_avg_score,
            "avg_rmse": b_avg_rmse,
            "last": _last(b_hist)
        },
        "winner": winner
    }


def rank_models(window_days: int = 7) -> Dict[str, Any]:
    """
    Classe tous les modèles par score moyen sur une période donnée.
    Retourne un ranking avec statistiques détaillées.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=window_days)
    start_ts = start.isoformat().replace("+00:00", "Z")
    
    models = list_models()
    rankings = []
    
    for model_info in models:
        model_id = model_info["model_id"]
        hist = list_evaluations(model_id, from_ts=start_ts, limit=10000)
        
        if not hist:
            continue
        
        # Calcul des statistiques
        scores = [h.get("score") for h in hist if h.get("score") is not None]
        rmses = [h.get("metrics", {}).get("rmse") for h in hist if h.get("metrics", {}).get("rmse") is not None]
        
        # Déterminer le statut de drift dominant
        drift_statuses = [h.get("performance_drift", {}).get("severity") for h in hist]
        drift_counts = {"high": 0, "medium": 0, "low": 0}
        for status in drift_statuses:
            if status and status.lower() in drift_counts:
                drift_counts[status.lower()] += 1
        
        avg_score = sum(scores) / len(scores) if scores else None
        avg_rmse = sum(rmses) / len(rmses) if rmses else None
        min_score = min(scores) if scores else None
        max_score = max(scores) if scores else None
        
        rankings.append({
            "model_id": model_id,
            "evaluation_count": len(hist),
            "avg_score": round(avg_score, 2) if avg_score else None,
            "min_score": round(min_score, 2) if min_score else None,
            "max_score": round(max_score, 2) if max_score else None,
            "avg_rmse": round(avg_rmse, 4) if avg_rmse else None,
            "drift_summary": drift_counts,
            "last_evaluation": hist[-1].get("timestamp") if hist else None
        })
    
    # Trier par score moyen décroissant
    rankings.sort(key=lambda x: x.get("avg_score") or 0, reverse=True)
    
    # Ajouter le rang
    for i, r in enumerate(rankings, 1):
        r["rank"] = i
    
    return {
        "window_days": window_days,
        "total_models": len(rankings),
        "ranking": rankings
    }


def get_active_alerts(severity: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Récupère les alertes actives (modèles avec drift détecté).
    
    Args:
        severity: Filtrer par sévérité ('high', 'medium', ou None pour tous)
        limit: Nombre max d'alertes à retourner
    
    Returns:
        Liste des alertes avec détails du modèle et de l'évaluation
    """
    alerts = []
    models = list_models()
    
    for model_info in models:
        model_id = model_info["model_id"]
        # Récupérer la dernière évaluation
        hist = list_evaluations(model_id, limit=1)
        
        if not hist:
            continue
        
        last_eval = hist[-1]
        drift_info = last_eval.get("performance_drift", {})
        
        # Vérifier si drift détecté
        if not drift_info.get("drift_detected", False):
            continue
        
        eval_severity = drift_info.get("severity", "").lower()
        
        # Filtrer par sévérité si spécifié
        if severity and eval_severity != severity.lower():
            continue
        
        alerts.append({
            "model_id": model_id,
            "severity": eval_severity,
            "timestamp": last_eval.get("timestamp"),
            "score": last_eval.get("score"),
            "current_rmse": drift_info.get("current_rmse"),
            "baseline_rmse": drift_info.get("baseline_rmse"),
            "ratio": drift_info.get("ratio"),
            "reason": drift_info.get("reason"),
            "metrics": last_eval.get("metrics", {})
        })
    
    # Trier par sévérité (high > medium > low) puis par timestamp
    severity_order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    alerts.sort(key=lambda x: (severity_order.get(x["severity"], 99), x.get("timestamp", "") or ""))
    
    return alerts[:limit]


def get_model_alert_history(model_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Récupère l'historique des alertes (évaluations avec drift) pour un modèle.
    
    Args:
        model_id: Identifiant du modèle
        limit: Nombre max d'alertes à retourner
    
    Returns:
        Liste des évaluations où un drift a été détecté
    """
    hist = list_evaluations(model_id, limit=1000)
    
    alerts = []
    for eval_item in hist:
        drift_info = eval_item.get("performance_drift", {})
        
        if drift_info.get("drift_detected", False):
            alerts.append({
                "timestamp": eval_item.get("timestamp"),
                "severity": drift_info.get("severity"),
                "score": eval_item.get("score"),
                "current_rmse": drift_info.get("current_rmse"),
                "baseline_rmse": drift_info.get("baseline_rmse"),
                "ratio": drift_info.get("ratio"),
                "reason": drift_info.get("reason")
            })
    
    # Trier par timestamp décroissant (plus récent en premier)
    alerts.sort(key=lambda x: x.get("timestamp", "") or "", reverse=True)
    
    return alerts[:limit]


def get_alerts_summary() -> Dict[str, Any]:
    """
    Retourne un résumé des alertes actives par sévérité.
    
    Returns:
        Dictionnaire avec compteurs par sévérité et liste des modèles concernés
    """
    alerts = get_active_alerts(limit=1000)
    
    summary = {
        "total": len(alerts),
        "by_severity": {
            "high": 0,
            "medium": 0,
            "low": 0
        },
        "models_with_alerts": []
    }
    
    for alert in alerts:
        severity = alert.get("severity", "").lower()
        if severity in summary["by_severity"]:
            summary["by_severity"][severity] += 1
        summary["models_with_alerts"].append(alert["model_id"])
    
    return summary

