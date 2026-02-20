from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from app.schemas import (
    EvaluateRequest, 
    DataDriftRequest, 
    ScheduleRequest,
    DataCleaningRequest,
    DataCleaningResponse,
    DataPreviewRequest,
    DataPreviewResponse,
    DataFilesResponse
)
from app.services.metrics import compute_metrics
from app.services.drift import detect_performance_drift
from app.services.scoring import compute_score
from app.services.data_drift import detect_data_drift
from app.services.data_cleaning import data_cleaning_service
from app.services.history import (
    store_evaluation, 
    list_evaluations, 
    compare_models, 
    list_models,
    rank_models,
    get_active_alerts,
    get_model_alert_history,
    get_alerts_summary
)
from app.services.scheduler import scheduler


def _evaluate_and_store(model_id: str, y_true: list, y_pred: list, baseline_rmse: float = None):
    """Fonction callback pour le scheduler."""
    metrics = compute_metrics(y_true, y_pred)
    drift = detect_performance_drift(
        current_rmse=metrics["rmse"],
        baseline_rmse=baseline_rmse
    )
    score = compute_score(metrics, drift)
    result = {
        "metrics": metrics,
        "performance_drift": drift,
        "score": score
    }
    store_evaluation(model_id, result)
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    # Démarrage : configurer et lancer le scheduler
    scheduler.set_evaluation_callback(_evaluate_and_store)
    await scheduler.start()
    yield
    # Arrêt : stopper le scheduler
    await scheduler.stop()


app = FastAPI(
    title="Sentinel360 API",
    description="Module d'audit, de surveillance et de notation de modèles IA prédictifs",
    version="1.0.0",
    lifespan=lifespan
)


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


@app.post("/models/{model_id}/evaluate")
def evaluate_and_store(model_id: str, payload: EvaluateRequest):
    result = evaluate(payload)            # réutilise ton endpoint existant
    store_evaluation(model_id, result)    # sauvegarde dans un fichier
    return {"model_id": model_id, "saved": True, "result": result}


@app.get("/models/{model_id}/evaluations")
def get_evaluations(
    model_id: str,
    from_ts: str | None = Query(default=None),
    to_ts: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=10000)
):
    hist = list_evaluations(model_id, from_ts=from_ts, to_ts=to_ts, limit=limit)
    return {"model_id": model_id, "count": len(hist), "items": hist}


@app.get("/compare")
def compare(
    model_a: str,
    model_b: str,
    window_days: int = Query(default=7, ge=1, le=365)
):
    """Compare deux modèles sur une période donnée."""
    return compare_models(model_a, model_b, window_days=window_days)


@app.get("/models")
def get_models():
    """Liste tous les modèles ayant des évaluations enregistrées."""
    models = list_models()
    return {
        "total": len(models),
        "models": models
    }


@app.get("/models/ranking")
def get_ranking(
    window_days: int = Query(default=7, ge=1, le=365)
):
    """
    Classe tous les modèles par score moyen sur une période.
    Permet de comparer rapidement les performances de tous les modèles.
    """
    return rank_models(window_days=window_days)


@app.post("/drift-data")
def drift_data(payload: DataDriftRequest):
    """Analyse la dérive des données d'entrée."""
    result = detect_data_drift(payload.reference, payload.current, payload.alpha)
    return result


# =============================================================================
# ENDPOINTS ALERTES (F3-UC4)
# =============================================================================

@app.get("/alerts")
def get_alerts(
    severity: str | None = Query(default=None, description="Filtrer par sévérité: 'high', 'medium', 'low'"),
    limit: int = Query(default=50, ge=1, le=500)
):
    """
    Liste les alertes actives (modèles avec drift détecté).
    
    Retourne les modèles dont la dernière évaluation a détecté un drift de performance.
    Les alertes sont triées par sévérité (high > medium > low).
    """
    alerts = get_active_alerts(severity=severity, limit=limit)
    return {
        "total": len(alerts),
        "severity_filter": severity,
        "alerts": alerts
    }


@app.get("/alerts/summary")
def alerts_summary():
    """
    Retourne un résumé des alertes actives.
    
    Inclut le nombre d'alertes par sévérité et la liste des modèles concernés.
    """
    return get_alerts_summary()


@app.get("/models/{model_id}/alerts")
def get_model_alerts(
    model_id: str,
    limit: int = Query(default=20, ge=1, le=500)
):
    """
    Historique des alertes pour un modèle spécifique.
    
    Retourne toutes les évaluations où un drift a été détecté pour ce modèle,
    triées par date décroissante.
    """
    alerts = get_model_alert_history(model_id, limit=limit)
    return {
        "model_id": model_id,
        "total": len(alerts),
        "alerts": alerts
    }


# =============================================================================
# ENDPOINTS SCHEDULER (F2-UC3)
# =============================================================================

@app.get("/scheduler/status")
def scheduler_status():
    """Retourne l'état du scheduler et ses statistiques."""
    return scheduler.get_stats()


@app.post("/scheduler/schedules")
def create_schedule(payload: ScheduleRequest):
    """
    Crée une tâche planifiée pour évaluer automatiquement un modèle.
    
    L'évaluation sera exécutée à intervalles réguliers avec les données fournies.
    """
    schedule = scheduler.create_schedule(
        model_id=payload.model_id,
        interval_minutes=payload.interval_minutes,
        y_true=payload.y_true,
        y_pred=payload.y_pred,
        baseline_rmse=payload.baseline_rmse,
        max_runs=payload.max_runs
    )
    return {
        "message": "Schedule créé avec succès",
        "schedule_id": schedule.schedule_id,
        "next_run": schedule.next_run
    }


@app.get("/scheduler/schedules")
def list_schedules(model_id: str | None = Query(default=None)):
    """Liste toutes les tâches planifiées."""
    schedules = scheduler.list_schedules(model_id=model_id)
    return {
        "total": len(schedules),
        "schedules": schedules
    }


@app.get("/scheduler/schedules/{schedule_id}")
def get_schedule(schedule_id: str):
    """Récupère les détails d'une tâche planifiée."""
    schedule = scheduler.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule non trouvé")
    
    from dataclasses import asdict
    result = asdict(schedule)
    result["status"] = schedule.status.value
    return result


@app.post("/scheduler/schedules/{schedule_id}/pause")
def pause_schedule(schedule_id: str):
    """Met en pause une tâche planifiée."""
    success = scheduler.pause_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule non trouvé")
    return {"message": "Schedule mis en pause", "schedule_id": schedule_id}


@app.post("/scheduler/schedules/{schedule_id}/resume")
def resume_schedule(schedule_id: str):
    """Reprend une tâche planifiée en pause."""
    success = scheduler.resume_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule non trouvé ou non en pause")
    return {"message": "Schedule repris", "schedule_id": schedule_id}


@app.post("/scheduler/schedules/{schedule_id}/trigger")
def trigger_schedule(schedule_id: str):
    """Déclenche immédiatement une évaluation pour un schedule."""
    result = scheduler.trigger_now(schedule_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Schedule non trouvé ou erreur d'exécution")
    return {
        "message": "Évaluation déclenchée",
        "schedule_id": schedule_id,
        "result": result
    }


@app.delete("/scheduler/schedules/{schedule_id}")
def delete_schedule(schedule_id: str):
    """Supprime une tâche planifiée."""
    success = scheduler.delete_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule non trouvé")
    return {"message": "Schedule supprimé", "schedule_id": schedule_id}


# =============================================================================
# ENDPOINTS DATA CLEANING (F1-UC2)
# =============================================================================

@app.get("/data/files", response_model=DataFilesResponse)
def list_data_files():
    """
    Liste tous les fichiers de données disponibles.
    
    Retourne les fichiers bruts et les fichiers nettoyés séparément.
    """
    from pathlib import Path
    
    data_dir = data_cleaning_service.data_dir
    
    # Fichiers bruts
    raw_files = [f.name for f in data_dir.glob("*.json") if "cleaned" not in str(f)]
    
    # Fichiers nettoyés
    cleaned_dir = data_dir / "cleaned"
    cleaned_files = []
    if cleaned_dir.exists():
        cleaned_files = [f.name for f in cleaned_dir.glob("*.json")]
    
    return DataFilesResponse(
        files=sorted(raw_files),
        cleaned_files=sorted(cleaned_files),
        total_count=len(raw_files) + len(cleaned_files)
    )


@app.post("/data/preview", response_model=DataPreviewResponse)
def preview_data(payload: DataPreviewRequest):
    """
    Prévisualise un fichier de données avec des statistiques.
    
    Utile pour inspecter les données avant le nettoyage.
    """
    try:
        data = data_cleaning_service.load_data(payload.filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Fichier non trouvé: {payload.filename}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de lecture: {str(e)}")
    
    # Convertir les types pour les statistiques
    converted_data = data_cleaning_service.convert_types(data)
    
    # Calculer les statistiques
    stats = data_cleaning_service.get_statistics(converted_data)
    
    # Colonnes
    columns = list(data[0].keys()) if data else []
    
    return DataPreviewResponse(
        filename=payload.filename,
        total_records=len(data),
        preview=data[:payload.limit],
        columns=columns,
        statistics=stats
    )


@app.post("/data/clean", response_model=DataCleaningResponse)
def clean_data(payload: DataCleaningRequest):
    """
    Nettoie un fichier de données selon la configuration fournie.
    
    Étapes de nettoyage:
    1. Conversion des types
    2. Suppression des doublons
    3. Gestion des valeurs manquantes
    4. Validation des plages
    5. Suppression des outliers (optionnel)
    
    Le fichier nettoyé est sauvegardé dans data/cleaned/
    """
    try:
        # Convertir la config Pydantic en dict si fournie
        config = payload.config.model_dump() if payload.config else None
        
        report = data_cleaning_service.clean_dataset(payload.filename, config)
        
        # Retirer cleaned_data du rapport pour la réponse API
        report.pop("cleaned_data", None)
        
        return DataCleaningResponse(**report)
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Fichier non trouvé: {payload.filename}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de nettoyage: {str(e)}")


@app.post("/data/clean-all")
def clean_all_data():
    """
    Nettoie tous les fichiers de données du dossier data/.
    
    Utilise la configuration par défaut pour chaque fichier.
    """
    try:
        reports = data_cleaning_service.clean_all_datasets()
        
        return {
            "message": f"{len(reports)} fichier(s) traité(s)",
            "reports": reports
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@app.get("/data/{filename}/statistics")
def get_data_statistics(filename: str):
    """
    Retourne les statistiques détaillées d'un fichier de données.
    """
    try:
        data = data_cleaning_service.load_data(filename)
        converted_data = data_cleaning_service.convert_types(data)
        stats = data_cleaning_service.get_statistics(converted_data)
        
        return {
            "filename": filename,
            "total_records": len(data),
            "statistics": stats
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Fichier non trouvé: {filename}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur: {str(e)}")