"""
F5-UC2 : Tests pour la comparaison entre modèles.

Ce module teste les fonctionnalités de :
- Listage des modèles disponibles
- Comparaison entre deux modèles
- Ranking multi-modèles
"""

import pytest
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

from app.services.history import (
    store_evaluation,
    list_models,
    compare_models,
    rank_models,
    _data_dir
)


@pytest.fixture(autouse=True)
def clean_test_data():
    """Nettoie les données de test avant et après chaque test."""
    data_dir = _data_dir()
    
    # Sauvegarde des fichiers existants
    backup_files = {}
    for f in data_dir.glob("evals_test_*.json"):
        backup_files[f.name] = f.read_text()
        f.unlink()
    
    yield
    
    # Nettoyage après test
    for f in data_dir.glob("evals_test_*.json"):
        f.unlink()


class TestListModels:
    """Tests pour la fonction list_models."""

    def test_list_models_empty(self):
        """Test avec aucun modèle enregistré."""
        # Filtrer uniquement les modèles de test
        models = [m for m in list_models() if m["model_id"].startswith("test_")]
        assert models == []

    def test_list_models_single(self):
        """Test avec un seul modèle."""
        eval_data = {
            "score": 85.0,
            "metrics": {"rmse": 0.15},
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        store_evaluation("test_model_A", eval_data)
        
        models = [m for m in list_models() if m["model_id"].startswith("test_")]
        
        assert len(models) == 1
        assert models[0]["model_id"] == "test_model_A"
        assert models[0]["evaluation_count"] == 1
        assert models[0]["last_score"] == 85.0

    def test_list_models_multiple_sorted_by_score(self):
        """Test que les modèles sont triés par score décroissant."""
        # Modèle avec score bas
        store_evaluation("test_model_low", {
            "score": 50.0,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        })
        
        # Modèle avec score haut
        store_evaluation("test_model_high", {
            "score": 95.0,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        })
        
        # Modèle avec score moyen
        store_evaluation("test_model_mid", {
            "score": 75.0,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        })
        
        models = [m for m in list_models() if m["model_id"].startswith("test_")]
        
        assert len(models) == 3
        # Vérifie l'ordre décroissant par score
        assert models[0]["model_id"] == "test_model_high"
        assert models[1]["model_id"] == "test_model_mid"
        assert models[2]["model_id"] == "test_model_low"


class TestCompareModels:
    """Tests pour la fonction compare_models."""

    def test_compare_models_basic(self):
        """Test de comparaison basique entre deux modèles."""
        # Créer des évaluations pour deux modèles
        now = datetime.now(timezone.utc)
        
        store_evaluation("test_compare_A", {
            "score": 90.0,
            "metrics": {"rmse": 0.10},
            "timestamp": now.isoformat().replace("+00:00", "Z")
        })
        
        store_evaluation("test_compare_B", {
            "score": 70.0,
            "metrics": {"rmse": 0.25},
            "timestamp": now.isoformat().replace("+00:00", "Z")
        })
        
        result = compare_models("test_compare_A", "test_compare_B", window_days=7)
        
        assert result["window_days"] == 7
        assert result["model_a"]["id"] == "test_compare_A"
        assert result["model_b"]["id"] == "test_compare_B"
        assert result["model_a"]["avg_score"] == 90.0
        assert result["model_b"]["avg_score"] == 70.0
        assert result["winner"] == "test_compare_A"

    def test_compare_models_with_multiple_evaluations(self):
        """Test avec plusieurs évaluations par modèle."""
        now = datetime.now(timezone.utc)
        
        # Modèle A : scores [80, 90, 85] -> moyenne = 85
        for score in [80.0, 90.0, 85.0]:
            store_evaluation("test_multi_A", {
                "score": score,
                "metrics": {"rmse": 0.15},
                "timestamp": now.isoformat().replace("+00:00", "Z")
            })
        
        # Modèle B : scores [75, 85, 80] -> moyenne = 80
        for score in [75.0, 85.0, 80.0]:
            store_evaluation("test_multi_B", {
                "score": score,
                "metrics": {"rmse": 0.18},
                "timestamp": now.isoformat().replace("+00:00", "Z")
            })
        
        result = compare_models("test_multi_A", "test_multi_B", window_days=7)
        
        assert result["model_a"]["n"] == 3
        assert result["model_b"]["n"] == 3
        assert result["model_a"]["avg_score"] == 85.0
        assert result["model_b"]["avg_score"] == 80.0
        assert result["winner"] == "test_multi_A"

    def test_compare_nonexistent_model(self):
        """Test de comparaison avec un modèle inexistant."""
        store_evaluation("test_existing", {
            "score": 85.0,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        })
        
        result = compare_models("test_existing", "test_nonexistent", window_days=7)
        
        assert result["model_a"]["n"] == 1
        assert result["model_b"]["n"] == 0
        assert result["model_b"]["avg_score"] is None


class TestRankModels:
    """Tests pour la fonction rank_models."""

    def test_rank_models_empty(self):
        """Test du ranking sans modèles."""
        result = rank_models(window_days=7)
        
        # Filtrer les modèles de test uniquement
        test_rankings = [r for r in result["ranking"] if r["model_id"].startswith("test_")]
        assert test_rankings == []

    def test_rank_models_multiple(self):
        """Test du ranking avec plusieurs modèles."""
        now = datetime.now(timezone.utc)
        
        # Créer 3 modèles avec différents scores
        models_data = [
            ("test_rank_gold", 95.0),
            ("test_rank_silver", 85.0),
            ("test_rank_bronze", 75.0)
        ]
        
        for model_id, score in models_data:
            store_evaluation(model_id, {
                "score": score,
                "metrics": {"rmse": 0.1},
                "performance_drift": {"severity": "low"},
                "timestamp": now.isoformat().replace("+00:00", "Z")
            })
        
        result = rank_models(window_days=7)
        
        # Filtrer les modèles de test
        test_rankings = [r for r in result["ranking"] if r["model_id"].startswith("test_rank_")]
        
        assert len(test_rankings) == 3
        assert test_rankings[0]["model_id"] == "test_rank_gold"
        assert test_rankings[0]["rank"] <= test_rankings[1]["rank"]
        assert test_rankings[1]["rank"] <= test_rankings[2]["rank"]

    def test_rank_models_includes_drift_summary(self):
        """Test que le ranking inclut le résumé des drifts."""
        now = datetime.now(timezone.utc)
        
        # Créer un modèle avec plusieurs évaluations et différents niveaux de drift
        store_evaluation("test_drift_summary", {
            "score": 80.0,
            "performance_drift": {"severity": "low"},
            "timestamp": now.isoformat().replace("+00:00", "Z")
        })
        store_evaluation("test_drift_summary", {
            "score": 70.0,
            "performance_drift": {"severity": "medium"},
            "timestamp": now.isoformat().replace("+00:00", "Z")
        })
        store_evaluation("test_drift_summary", {
            "score": 60.0,
            "performance_drift": {"severity": "high"},
            "timestamp": now.isoformat().replace("+00:00", "Z")
        })
        
        result = rank_models(window_days=7)
        
        model_rank = next(
            (r for r in result["ranking"] if r["model_id"] == "test_drift_summary"),
            None
        )
        
        assert model_rank is not None
        assert "drift_summary" in model_rank
        assert model_rank["drift_summary"]["low"] == 1
        assert model_rank["drift_summary"]["medium"] == 1
        assert model_rank["drift_summary"]["high"] == 1

    def test_rank_models_statistics(self):
        """Test des statistiques min/max/avg dans le ranking."""
        now = datetime.now(timezone.utc)
        
        scores = [70.0, 80.0, 90.0]
        for score in scores:
            store_evaluation("test_stats_model", {
                "score": score,
                "metrics": {"rmse": 0.15},
                "timestamp": now.isoformat().replace("+00:00", "Z")
            })
        
        result = rank_models(window_days=7)
        
        model_rank = next(
            (r for r in result["ranking"] if r["model_id"] == "test_stats_model"),
            None
        )
        
        assert model_rank is not None
        assert model_rank["avg_score"] == 80.0
        assert model_rank["min_score"] == 70.0
        assert model_rank["max_score"] == 90.0
        assert model_rank["evaluation_count"] == 3
