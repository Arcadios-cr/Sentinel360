"""
F3-UC3 : Tests pour la définition des seuils de tolérance par modèle.

Ce module teste :
- Création et mise à jour des seuils personnalisés
- Résolution des seuils avec fallback (override > config > défaut)
- Suppression de la configuration
- Liste des configurations
"""

import pytest
from unittest.mock import patch

from app.services.thresholds import (
    get_model_config,
    set_model_config,
    delete_model_config,
    get_thresholds,
    list_model_configs,
    DEFAULT_THRESHOLDS,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Crée un répertoire temporaire pour les données de test."""
    with patch('app.services.thresholds._data_dir', return_value=tmp_path):
        yield tmp_path


class TestThresholdsPersistence:
    """Tests de persistance des seuils."""

    def test_set_and_get_config(self, temp_data_dir):
        """Créer et récupérer une configuration."""
        thresholds = {
            "performance_drift": {"warn_ratio": 1.15, "alert_ratio": 1.30},
            "data_drift": {"alpha": 0.01},
        }
        set_model_config("model_A", thresholds, description="Test config")

        config = get_model_config("model_A")

        assert config is not None
        assert config["model_id"] == "model_A"
        assert config["thresholds"]["performance_drift"]["warn_ratio"] == 1.15
        assert config["thresholds"]["performance_drift"]["alert_ratio"] == 1.30
        assert config["thresholds"]["data_drift"]["alpha"] == 0.01

    def test_get_config_not_found(self, temp_data_dir):
        """Récupérer une config inexistante retourne None."""
        assert get_model_config("inexistant") is None

    def test_update_config_merges(self, temp_data_dir):
        """Mettre à jour une config fusionne les valeurs."""
        set_model_config("model_A", {"performance_drift": {"warn_ratio": 1.15}})
        set_model_config("model_A", {"performance_drift": {"alert_ratio": 1.40}})

        config = get_model_config("model_A")

        # Les deux valeurs doivent être présentes
        assert config["thresholds"]["performance_drift"]["warn_ratio"] == 1.15
        assert config["thresholds"]["performance_drift"]["alert_ratio"] == 1.40

    def test_delete_config(self, temp_data_dir):
        """Supprimer une configuration."""
        set_model_config("model_A", {"performance_drift": {"warn_ratio": 1.15}})

        assert delete_model_config("model_A") is True
        assert get_model_config("model_A") is None

    def test_delete_config_not_found(self, temp_data_dir):
        """Supprimer une config inexistante retourne False."""
        assert delete_model_config("inexistant") is False

    def test_list_configs(self, temp_data_dir):
        """Lister toutes les configurations."""
        set_model_config("model_A", {"performance_drift": {"warn_ratio": 1.15}})
        set_model_config("model_B", {"data_drift": {"alpha": 0.01}})

        configs = list_model_configs()

        assert len(configs) == 2
        model_ids = {c["model_id"] for c in configs}
        assert "model_A" in model_ids
        assert "model_B" in model_ids


class TestThresholdsResolution:
    """Tests de résolution des seuils avec fallback."""

    def test_default_thresholds_when_no_config(self, temp_data_dir):
        """Retourne les valeurs par défaut si pas de config."""
        thresholds = get_thresholds("inexistant")

        assert thresholds["performance_drift"]["warn_ratio"] == DEFAULT_THRESHOLDS["performance_drift"]["warn_ratio"]
        assert thresholds["performance_drift"]["alert_ratio"] == DEFAULT_THRESHOLDS["performance_drift"]["alert_ratio"]
        assert thresholds["data_drift"]["alpha"] == DEFAULT_THRESHOLDS["data_drift"]["alpha"]

    def test_model_config_overrides_defaults(self, temp_data_dir):
        """La config modèle surcharge les valeurs par défaut."""
        set_model_config("model_A", {"performance_drift": {"warn_ratio": 1.20}})

        thresholds = get_thresholds("model_A")

        # warn_ratio surchargé
        assert thresholds["performance_drift"]["warn_ratio"] == 1.20
        # alert_ratio reste par défaut
        assert thresholds["performance_drift"]["alert_ratio"] == 1.25

    def test_override_has_highest_priority(self, temp_data_dir):
        """Les overrides ont la priorité la plus haute."""
        set_model_config("model_A", {"performance_drift": {"warn_ratio": 1.20}})

        thresholds = get_thresholds(
            "model_A",
            override={"performance_drift": {"warn_ratio": 1.50}}
        )

        assert thresholds["performance_drift"]["warn_ratio"] == 1.50

    def test_full_fallback_chain(self, temp_data_dir):
        """Vérifier la chaîne complète : défaut < config < override."""
        set_model_config("model_A", {
            "performance_drift": {"warn_ratio": 1.15},
            "score": {"warning_threshold": 65},
        })

        thresholds = get_thresholds(
            "model_A",
            override={"score": {"critical_threshold": 30}}
        )

        # Défaut
        assert thresholds["performance_drift"]["alert_ratio"] == 1.25
        # Config modèle
        assert thresholds["performance_drift"]["warn_ratio"] == 1.15
        # Config modèle
        assert thresholds["score"]["warning_threshold"] == 65
        # Override
        assert thresholds["score"]["critical_threshold"] == 30
