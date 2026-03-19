"""
F1-UC3 : Tests pour la construction et gestion du dataset de référence (Golden Set).

Ce module teste :
- Création d'un golden set
- Récupération du golden set
- Suppression du golden set
- Calcul des statistiques
- Validation des entrées
- Liste des golden sets
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch

from app.services.reference_dataset import (
    create_reference_dataset,
    get_reference_dataset,
    get_reference_features,
    delete_reference_dataset,
    list_reference_datasets,
    _compute_feature_stats,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Crée un répertoire temporaire pour les données de test."""
    with patch('app.services.reference_dataset._data_dir', return_value=tmp_path):
        yield tmp_path


class TestReferenceDataset:
    """Tests de création et gestion des golden sets."""

    def test_create_reference_dataset(self, temp_data_dir):
        """Créer un golden set avec des données valides."""
        features = {
            "temperature": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0],
            "humidity": [45.0, 46.0, 47.0, 48.0, 49.0, 50.0],
        }

        result = create_reference_dataset(
            model_id="test_model",
            features=features,
            description="Test golden set",
            version="1.0",
        )

        assert result["model_id"] == "test_model"
        assert result["n_samples"] == 6
        assert result["n_features"] == 2
        assert "temperature" in result["features"]
        assert "humidity" in result["features"]
        assert result["statistics"]["temperature"]["count"] == 6

    def test_get_reference_dataset(self, temp_data_dir):
        """Récupérer un golden set existant."""
        features = {"temperature": [20.0, 21.0, 22.0, 23.0, 24.0]}
        create_reference_dataset("test_model", features)

        dataset = get_reference_dataset("test_model")

        assert dataset is not None
        assert dataset["model_id"] == "test_model"
        assert "features" in dataset
        assert "statistics" in dataset

    def test_get_reference_dataset_not_found(self, temp_data_dir):
        """Récupérer un golden set inexistant retourne None."""
        dataset = get_reference_dataset("inexistant")
        assert dataset is None

    def test_get_reference_features(self, temp_data_dir):
        """Récupérer uniquement les features du golden set."""
        features = {
            "temperature": [20.0, 21.0, 22.0, 23.0, 24.0],
            "humidity": [45.0, 46.0, 47.0, 48.0, 49.0],
        }
        create_reference_dataset("test_model", features)

        result = get_reference_features("test_model")

        assert result is not None
        assert set(result.keys()) == {"temperature", "humidity"}
        assert len(result["temperature"]) == 5

    def test_delete_reference_dataset(self, temp_data_dir):
        """Supprimer un golden set existant."""
        features = {"temperature": [20.0, 21.0, 22.0, 23.0, 24.0]}
        create_reference_dataset("test_model", features)

        assert delete_reference_dataset("test_model") is True
        assert get_reference_dataset("test_model") is None

    def test_delete_reference_dataset_not_found(self, temp_data_dir):
        """Supprimer un golden set inexistant retourne False."""
        assert delete_reference_dataset("inexistant") is False

    def test_list_reference_datasets(self, temp_data_dir):
        """Lister tous les golden sets."""
        create_reference_dataset("model_A", {"temp": [1, 2, 3, 4, 5]})
        create_reference_dataset("model_B", {"hum": [10, 20, 30, 40, 50]})

        datasets = list_reference_datasets()

        assert len(datasets) == 2
        model_ids = {d["model_id"] for d in datasets}
        assert "model_A" in model_ids
        assert "model_B" in model_ids

    def test_create_overwrites_existing(self, temp_data_dir):
        """Créer un golden set écrase l'existant."""
        create_reference_dataset("model_A", {"temp": [1, 2, 3, 4, 5]}, version="1.0")
        create_reference_dataset("model_A", {"temp": [10, 20, 30, 40, 50]}, version="2.0")

        dataset = get_reference_dataset("model_A")
        assert dataset["version"] == "2.0"
        assert dataset["features"]["temp"][0] == 10.0

    def test_create_rejects_empty_features(self, temp_data_dir):
        """Rejeter un golden set avec features vides."""
        with pytest.raises(ValueError, match="ne peut pas être vide"):
            create_reference_dataset("model_A", {})

    def test_create_rejects_too_few_values(self, temp_data_dir):
        """Rejeter une feature avec moins de 5 valeurs."""
        with pytest.raises(ValueError, match="au moins 5 valeurs"):
            create_reference_dataset("model_A", {"temp": [1, 2, 3]})


class TestFeatureStatistics:
    """Tests du calcul des statistiques."""

    def test_basic_stats(self):
        """Statistiques basiques correctes."""
        stats = _compute_feature_stats([10.0, 20.0, 30.0, 40.0, 50.0])

        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["mean"] == 30.0
        assert stats["median"] == 30.0

    def test_empty_list(self):
        """Statistiques d'une liste vide."""
        stats = _compute_feature_stats([])
        assert stats["count"] == 0

    def test_single_value(self):
        """Statistiques d'une seule valeur."""
        stats = _compute_feature_stats([42.0])
        assert stats["count"] == 1
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0
        assert stats["mean"] == 42.0
