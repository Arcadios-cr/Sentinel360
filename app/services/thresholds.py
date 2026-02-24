"""
F3-UC3 : Définition des seuils de tolérance par modèle.

Ce module permet de :
- Stocker des seuils personnalisés par modèle (performance drift, data drift, score)
- Charger automatiquement les seuils lors de l'évaluation
- Fallback vers les valeurs par défaut si pas de config
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone


# Valeurs par défaut globales
DEFAULT_THRESHOLDS = {
    "performance_drift": {
        "baseline_rmse": None,
        "warn_ratio": 1.10,
        "alert_ratio": 1.25,
    },
    "data_drift": {
        "alpha": 0.05,
    },
    "score": {
        "warning_threshold": 70,
        "critical_threshold": 50,
    },
}


def _data_dir() -> Path:
    d = Path(__file__).resolve().parents[1] / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_model_id(model_id: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in model_id)


def _config_file(model_id: str) -> Path:
    return _data_dir() / f"config_{_safe_model_id(model_id)}.json"


def get_model_config(model_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère la configuration complète d'un modèle.

    Returns:
        Configuration du modèle ou None si inexistante
    """
    path = _config_file(model_id)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def set_model_config(
    model_id: str,
    thresholds: Dict[str, Any],
    description: str = "",
) -> Dict[str, Any]:
    """
    Crée ou met à jour la configuration de seuils d'un modèle.

    Args:
        model_id: Identifiant du modèle
        thresholds: Dictionnaire de seuils (performance_drift, data_drift, score)
        description: Description optionnelle

    Returns:
        Configuration sauvegardée
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    existing = get_model_config(model_id)

    if existing:
        # Merge : conserver les valeurs existantes, écraser avec les nouvelles
        merged = existing.get("thresholds", {})
        for category, values in thresholds.items():
            if category not in merged:
                merged[category] = {}
            merged[category].update(values)
        config = {
            "model_id": model_id,
            "created_at": existing.get("created_at", now),
            "updated_at": now,
            "thresholds": merged,
            "description": description or existing.get("description", ""),
        }
    else:
        config = {
            "model_id": model_id,
            "created_at": now,
            "updated_at": now,
            "thresholds": thresholds,
            "description": description or f"Configuration des seuils pour {model_id}",
        }

    path = _config_file(model_id)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    return config


def delete_model_config(model_id: str) -> bool:
    """
    Supprime la configuration d'un modèle (retour aux valeurs par défaut).

    Returns:
        True si supprimé, False si inexistant
    """
    path = _config_file(model_id)
    if path.exists():
        path.unlink()
        return True
    return False


def get_thresholds(model_id: str, override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Résout les seuils effectifs pour un modèle.

    Priorité : override > config modèle > valeurs par défaut

    Args:
        model_id: Identifiant du modèle
        override: Seuils à forcer (prioritaires)

    Returns:
        Seuils effectifs fusionnés
    """
    import copy
    result = copy.deepcopy(DEFAULT_THRESHOLDS)

    # Merge config modèle
    model_config = get_model_config(model_id)
    if model_config and "thresholds" in model_config:
        for category, values in model_config["thresholds"].items():
            if category in result:
                result[category].update(values)
            else:
                result[category] = values

    # Merge override
    if override:
        for category, values in override.items():
            if isinstance(values, dict):
                if category in result:
                    result[category].update(values)
                else:
                    result[category] = values
            else:
                # Valeur simple au premier niveau
                result[category] = values

    return result


def list_model_configs() -> list:
    """
    Liste toutes les configurations de modèles.

    Returns:
        Liste des configurations avec métadonnées
    """
    data_dir = _data_dir()
    configs = []

    for file_path in data_dir.glob("config_*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                configs.append({
                    "model_id": data.get("model_id", ""),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "description": data.get("description", ""),
                    "thresholds": data.get("thresholds", {}),
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return configs
