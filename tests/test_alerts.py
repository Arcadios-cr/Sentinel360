"""
F3-UC4 : Tests pour la génération et récupération des alertes automatiques.

Ce module teste :
- Récupération des alertes actives
- Filtrage par sévérité
- Historique des alertes par modèle
- Résumé des alertes
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.services.history import (
    get_active_alerts,
    get_model_alert_history,
    get_alerts_summary,
    store_evaluation,
    list_models,
    _data_dir
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Crée un répertoire temporaire pour les données de test."""
    with patch('app.services.history._data_dir', return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def sample_evaluations_with_alerts(temp_data_dir):
    """Crée des évaluations de test avec différents niveaux d'alerte."""
    
    # Modèle avec drift high
    eval_high = {
        "timestamp": "2026-03-08T10:00:00Z",
        "metrics": {"mae": 0.5, "mse": 0.3, "rmse": 0.55, "r2": 0.8},
        "performance_drift": {
            "baseline_rmse": 0.2,
            "current_rmse": 0.55,
            "ratio": 2.75,
            "delta": 0.35,
            "severity": "high",
            "drift_detected": True,
            "reason": "dégradation forte de performance"
        },
        "score": 45
    }
    
    # Modèle avec drift medium
    eval_medium = {
        "timestamp": "2026-03-08T11:00:00Z",
        "metrics": {"mae": 0.2, "mse": 0.05, "rmse": 0.22, "r2": 0.92},
        "performance_drift": {
            "baseline_rmse": 0.2,
            "current_rmse": 0.22,
            "ratio": 1.1,
            "delta": 0.02,
            "severity": "medium",
            "drift_detected": True,
            "reason": "dégradation modérée de performance"
        },
        "score": 75
    }
    
    # Modèle sans drift (stable)
    eval_stable = {
        "timestamp": "2026-03-08T12:00:00Z",
        "metrics": {"mae": 0.1, "mse": 0.02, "rmse": 0.14, "r2": 0.98},
        "performance_drift": {
            "baseline_rmse": 0.2,
            "current_rmse": 0.14,
            "ratio": 0.7,
            "delta": -0.06,
            "severity": "low",
            "drift_detected": False,
            "reason": "performance stable"
        },
        "score": 95
    }
    
    # Sauvegarder les évaluations
    model_high_file = temp_data_dir / "evals_model_high.json"
    model_medium_file = temp_data_dir / "evals_model_medium.json"
    model_stable_file = temp_data_dir / "evals_model_stable.json"
    
    with model_high_file.open("w") as f:
        json.dump([eval_high], f)
    
    with model_medium_file.open("w") as f:
        json.dump([eval_medium], f)
    
    with model_stable_file.open("w") as f:
        json.dump([eval_stable], f)
    
    return temp_data_dir


class TestGetActiveAlerts:
    """Tests pour get_active_alerts()."""

    def test_returns_alerts_for_models_with_drift(self, sample_evaluations_with_alerts):
        """Retourne uniquement les modèles avec drift détecté."""
        with patch('app.services.history._data_dir', return_value=sample_evaluations_with_alerts):
            alerts = get_active_alerts()
        
        # Doit retourner 2 alertes (high et medium), pas le stable
        assert len(alerts) == 2
        model_ids = [a["model_id"] for a in alerts]
        assert "model_high" in model_ids
        assert "model_medium" in model_ids
        assert "model_stable" not in model_ids

    def test_filter_by_severity_high(self, sample_evaluations_with_alerts):
        """Filtre les alertes par sévérité high."""
        with patch('app.services.history._data_dir', return_value=sample_evaluations_with_alerts):
            alerts = get_active_alerts(severity="high")
        
        assert len(alerts) == 1
        assert alerts[0]["model_id"] == "model_high"
        assert alerts[0]["severity"] == "high"

    def test_filter_by_severity_medium(self, sample_evaluations_with_alerts):
        """Filtre les alertes par sévérité medium."""
        with patch('app.services.history._data_dir', return_value=sample_evaluations_with_alerts):
            alerts = get_active_alerts(severity="medium")
        
        assert len(alerts) == 1
        assert alerts[0]["model_id"] == "model_medium"
        assert alerts[0]["severity"] == "medium"

    def test_sorted_by_severity(self, sample_evaluations_with_alerts):
        """Les alertes sont triées par sévérité (high en premier)."""
        with patch('app.services.history._data_dir', return_value=sample_evaluations_with_alerts):
            alerts = get_active_alerts()
        
        if len(alerts) >= 2:
            assert alerts[0]["severity"] == "high"
            assert alerts[1]["severity"] == "medium"

    def test_limit_parameter(self, sample_evaluations_with_alerts):
        """Le paramètre limit fonctionne."""
        with patch('app.services.history._data_dir', return_value=sample_evaluations_with_alerts):
            alerts = get_active_alerts(limit=1)
        
        assert len(alerts) <= 1

    def test_alert_structure(self, sample_evaluations_with_alerts):
        """Vérifie la structure d'une alerte."""
        with patch('app.services.history._data_dir', return_value=sample_evaluations_with_alerts):
            alerts = get_active_alerts()
        
        if alerts:
            alert = alerts[0]
            assert "model_id" in alert
            assert "severity" in alert
            assert "timestamp" in alert
            assert "score" in alert
            assert "current_rmse" in alert
            assert "baseline_rmse" in alert
            assert "ratio" in alert
            assert "reason" in alert
            assert "metrics" in alert

    def test_no_alerts_when_all_stable(self, temp_data_dir):
        """Retourne liste vide si aucun modèle n'a de drift."""
        eval_stable = {
            "timestamp": "2026-03-08T12:00:00Z",
            "metrics": {"rmse": 0.14},
            "performance_drift": {
                "severity": "low",
                "drift_detected": False
            },
            "score": 95
        }
        
        model_file = temp_data_dir / "evals_stable_model.json"
        with model_file.open("w") as f:
            json.dump([eval_stable], f)
        
        with patch('app.services.history._data_dir', return_value=temp_data_dir):
            alerts = get_active_alerts()
        
        assert len(alerts) == 0


class TestGetModelAlertHistory:
    """Tests pour get_model_alert_history()."""

    def test_returns_only_drift_evaluations(self, temp_data_dir):
        """Retourne uniquement les évaluations avec drift."""
        evaluations = [
            {
                "timestamp": "2026-03-01T10:00:00Z",
                "performance_drift": {"drift_detected": True, "severity": "high"},
                "score": 50
            },
            {
                "timestamp": "2026-03-02T10:00:00Z",
                "performance_drift": {"drift_detected": False, "severity": "low"},
                "score": 90
            },
            {
                "timestamp": "2026-03-03T10:00:00Z",
                "performance_drift": {"drift_detected": True, "severity": "medium"},
                "score": 70
            }
        ]
        
        model_file = temp_data_dir / "evals_test_model.json"
        with model_file.open("w") as f:
            json.dump(evaluations, f)
        
        with patch('app.services.history._data_dir', return_value=temp_data_dir):
            alerts = get_model_alert_history("test_model")
        
        # 2 évaluations avec drift
        assert len(alerts) == 2

    def test_sorted_by_timestamp_descending(self, temp_data_dir):
        """Les alertes sont triées par date décroissante."""
        evaluations = [
            {
                "timestamp": "2026-03-01T10:00:00Z",
                "performance_drift": {"drift_detected": True, "severity": "high"},
                "score": 50
            },
            {
                "timestamp": "2026-03-05T10:00:00Z",
                "performance_drift": {"drift_detected": True, "severity": "medium"},
                "score": 70
            }
        ]
        
        model_file = temp_data_dir / "evals_test_model.json"
        with model_file.open("w") as f:
            json.dump(evaluations, f)
        
        with patch('app.services.history._data_dir', return_value=temp_data_dir):
            alerts = get_model_alert_history("test_model")
        
        # Plus récent en premier
        assert alerts[0]["timestamp"] == "2026-03-05T10:00:00Z"
        assert alerts[1]["timestamp"] == "2026-03-01T10:00:00Z"

    def test_limit_parameter(self, temp_data_dir):
        """Le paramètre limit fonctionne."""
        evaluations = [
            {"timestamp": f"2026-03-0{i}T10:00:00Z", 
             "performance_drift": {"drift_detected": True, "severity": "high"},
             "score": 50}
            for i in range(1, 6)
        ]
        
        model_file = temp_data_dir / "evals_test_model.json"
        with model_file.open("w") as f:
            json.dump(evaluations, f)
        
        with patch('app.services.history._data_dir', return_value=temp_data_dir):
            alerts = get_model_alert_history("test_model", limit=2)
        
        assert len(alerts) == 2

    def test_empty_for_nonexistent_model(self, temp_data_dir):
        """Retourne liste vide pour un modèle inexistant."""
        with patch('app.services.history._data_dir', return_value=temp_data_dir):
            alerts = get_model_alert_history("nonexistent_model")
        
        assert len(alerts) == 0


class TestGetAlertsSummary:
    """Tests pour get_alerts_summary()."""

    def test_summary_structure(self, sample_evaluations_with_alerts):
        """Vérifie la structure du résumé."""
        with patch('app.services.history._data_dir', return_value=sample_evaluations_with_alerts):
            summary = get_alerts_summary()
        
        assert "total" in summary
        assert "by_severity" in summary
        assert "models_with_alerts" in summary
        
        assert "high" in summary["by_severity"]
        assert "medium" in summary["by_severity"]
        assert "low" in summary["by_severity"]

    def test_counts_by_severity(self, sample_evaluations_with_alerts):
        """Compte correctement les alertes par sévérité."""
        with patch('app.services.history._data_dir', return_value=sample_evaluations_with_alerts):
            summary = get_alerts_summary()
        
        assert summary["by_severity"]["high"] == 1
        assert summary["by_severity"]["medium"] == 1
        assert summary["total"] == 2

    def test_models_with_alerts_list(self, sample_evaluations_with_alerts):
        """Liste les modèles avec alertes."""
        with patch('app.services.history._data_dir', return_value=sample_evaluations_with_alerts):
            summary = get_alerts_summary()
        
        assert "model_high" in summary["models_with_alerts"]
        assert "model_medium" in summary["models_with_alerts"]
        assert "model_stable" not in summary["models_with_alerts"]

    def test_empty_summary_when_no_alerts(self, temp_data_dir):
        """Résumé vide quand aucune alerte."""
        eval_stable = {
            "timestamp": "2026-03-08T12:00:00Z",
            "performance_drift": {"drift_detected": False, "severity": "low"},
            "score": 95
        }
        
        model_file = temp_data_dir / "evals_stable.json"
        with model_file.open("w") as f:
            json.dump([eval_stable], f)
        
        with patch('app.services.history._data_dir', return_value=temp_data_dir):
            summary = get_alerts_summary()
        
        assert summary["total"] == 0
        assert summary["by_severity"]["high"] == 0
        assert summary["by_severity"]["medium"] == 0
        assert len(summary["models_with_alerts"]) == 0
