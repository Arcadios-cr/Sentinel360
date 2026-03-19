"""
F1-UC3 : Construction et gestion d'un Dataset de Référence (Golden Set).

Ce module permet de :
- Créer un golden set par modèle à partir de données fournies
- Stocker les données de référence avec métadonnées
- Récupérer le golden set pour comparaison (data drift)
- Calculer et stocker les statistiques du dataset
"""

import json
import math
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


def _data_dir() -> Path:
    d = Path(__file__).resolve().parents[1] / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_model_id(model_id: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in model_id)


def _reference_file(model_id: str) -> Path:
    return _data_dir() / f"reference_{_safe_model_id(model_id)}.json"


def _compute_feature_stats(values: List[float]) -> Dict[str, float]:
    """Calcule les statistiques descriptives d'une feature."""
    clean = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not clean:
        return {"count": 0, "min": 0, "max": 0, "mean": 0, "std": 0, "median": 0}

    n = len(clean)
    mean_val = sum(clean) / n
    variance = sum((x - mean_val) ** 2 for x in clean) / n if n > 1 else 0.0

    return {
        "count": n,
        "min": float(min(clean)),
        "max": float(max(clean)),
        "mean": round(mean_val, 6),
        "std": round(math.sqrt(variance), 6),
        "median": round(statistics.median(clean), 6),
    }


def create_reference_dataset(
    model_id: str,
    features: Dict[str, List[float]],
    description: str = "",
    version: str = "1.0",
) -> Dict[str, Any]:
    """
    Crée ou remplace le dataset de référence (golden set) d'un modèle.

    Args:
        model_id: Identifiant du modèle
        features: Dictionnaire {nom_feature: [valeurs]}
        description: Description textuelle du dataset
        version: Version du golden set

    Returns:
        Métadonnées du golden set créé
    """
    if not features:
        raise ValueError("Le dictionnaire de features ne peut pas être vide")

    for feat_name, vals in features.items():
        if not vals or len(vals) < 5:
            raise ValueError(
                f"La feature '{feat_name}' doit contenir au moins 5 valeurs (reçu {len(vals) if vals else 0})"
            )

    # Calcul des statistiques par feature
    feat_statistics: Dict[str, Any] = {}
    total_samples = 0
    for feat_name, vals in features.items():
        feat_statistics[feat_name] = _compute_feature_stats(vals)
        total_samples = max(total_samples, len(vals))

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    golden_set = {
        "model_id": model_id,
        "created_at": now,
        "updated_at": now,
        "version": version,
        "description": description or f"Dataset de référence pour {model_id}",
        "features": {k: [float(v) for v in vals] for k, vals in features.items()},
        "statistics": feat_statistics,
        "n_samples": total_samples,
        "n_features": len(features),
    }

    path = _reference_file(model_id)
    with path.open("w", encoding="utf-8") as f:
        json.dump(golden_set, f, ensure_ascii=False, indent=2)

    return {
        "model_id": model_id,
        "version": version,
        "n_samples": total_samples,
        "n_features": len(features),
        "features": list(features.keys()),
        "statistics": feat_statistics,
        "created_at": now,
        "file": str(path),
    }


def get_reference_dataset(model_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère le golden set d'un modèle.

    Returns:
        Le golden set complet ou None si inexistant
    """
    path = _reference_file(model_id)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_reference_features(model_id: str) -> Optional[Dict[str, List[float]]]:
    """
    Récupère uniquement les features du golden set (pour data drift).

    Returns:
        Dictionnaire {feature: [valeurs]} ou None
    """
    dataset = get_reference_dataset(model_id)
    if dataset is None:
        return None
    return dataset.get("features", None)


def delete_reference_dataset(model_id: str) -> bool:
    """
    Supprime le golden set d'un modèle.

    Returns:
        True si supprimé, False si inexistant
    """
    path = _reference_file(model_id)
    if path.exists():
        path.unlink()
        return True
    return False


def list_reference_datasets() -> List[Dict[str, Any]]:
    """
    Liste tous les golden sets disponibles.

    Returns:
        Liste de métadonnées des golden sets
    """
    data_dir = _data_dir()
    datasets = []

    for file_path in data_dir.glob("reference_*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                datasets.append({
                    "model_id": data.get("model_id", file_path.stem.replace("reference_", "")),
                    "version": data.get("version", "?"),
                    "n_samples": data.get("n_samples", 0),
                    "n_features": data.get("n_features", 0),
                    "created_at": data.get("created_at"),
                    "description": data.get("description", ""),
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return datasets
