"""
Tests unitaires pour le service de nettoyage des données (F1-UC2)
"""

import pytest
import json
import tempfile
from pathlib import Path
from app.services.data_cleaning import DataCleaningService


@pytest.fixture
def temp_data_dir():
    """Crée un répertoire temporaire pour les tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cleaning_service(temp_data_dir):
    """Crée une instance du service avec un répertoire temporaire."""
    return DataCleaningService(data_dir=str(temp_data_dir))


@pytest.fixture
def sample_ndjson_file(temp_data_dir):
    """Crée un fichier NDJSON de test."""
    data = [
        {"timestamp": "2026-01-05T10:00:00", "ID": "1", "temperature": "20.5", "humidity": "45.0", "CO2": "500"},
        {"timestamp": "2026-01-05T10:05:00", "ID": "2", "temperature": "21.0", "humidity": "nan", "CO2": "520"},
        {"timestamp": "2026-01-05T10:10:00", "ID": "3", "temperature": "nan", "humidity": "50.0", "CO2": "510"},
        {"timestamp": "2026-01-05T10:15:00", "ID": "4", "temperature": "22.5", "humidity": "48.0", "CO2": "530"},
        {"timestamp": "2026-01-05T10:00:00", "ID": "1", "temperature": "20.5", "humidity": "45.0", "CO2": "500"},  # Doublon
    ]
    
    filepath = temp_data_dir / "test_data.json"
    with open(filepath, "w") as f:
        for record in data:
            f.write(json.dumps(record) + "\n")
    
    return "test_data.json"


class TestDataCleaningService:
    """Tests pour DataCleaningService."""
    
    # ===========================================
    # Tests de chargement des données
    # ===========================================
    
    def test_load_ndjson(self, cleaning_service, sample_ndjson_file):
        """Test du chargement d'un fichier NDJSON."""
        data = cleaning_service.load_ndjson(sample_ndjson_file)
        assert len(data) == 5
        assert data[0]["temperature"] == "20.5"
    
    def test_load_ndjson_file_not_found(self, cleaning_service):
        """Test d'erreur si fichier non trouvé."""
        with pytest.raises(FileNotFoundError):
            cleaning_service.load_ndjson("inexistant.json")
    
    def test_load_data_auto_detect(self, cleaning_service, sample_ndjson_file):
        """Test de la détection automatique du format."""
        data = cleaning_service.load_data(sample_ndjson_file)
        assert len(data) == 5
    
    # ===========================================
    # Tests de conversion des types
    # ===========================================
    
    def test_convert_types_float(self, cleaning_service):
        """Test de conversion vers float."""
        data = [{"value": "123.45"}]
        schema = {"value": "float"}
        result = cleaning_service.convert_types(data, schema)
        assert result[0]["value"] == 123.45
    
    def test_convert_types_int(self, cleaning_service):
        """Test de conversion vers int."""
        data = [{"value": "123.9"}]
        schema = {"value": "int"}
        result = cleaning_service.convert_types(data, schema)
        assert result[0]["value"] == 123
    
    def test_convert_types_nan_to_none(self, cleaning_service):
        """Test de conversion de NaN vers None."""
        data = [{"value": "nan"}]
        schema = {"value": "float"}
        result = cleaning_service.convert_types(data, schema)
        assert result[0]["value"] is None
    
    def test_convert_types_empty_to_none(self, cleaning_service):
        """Test de conversion de chaîne vide vers None."""
        data = [{"value": ""}]
        schema = {"value": "float"}
        result = cleaning_service.convert_types(data, schema)
        assert result[0]["value"] is None
    
    # ===========================================
    # Tests de suppression des doublons
    # ===========================================
    
    def test_remove_duplicates_with_keys(self, cleaning_service):
        """Test de suppression des doublons avec clés spécifiées."""
        data = [
            {"id": "1", "value": 10},
            {"id": "2", "value": 20},
            {"id": "1", "value": 10},  # Doublon
        ]
        result, count = cleaning_service.remove_duplicates(data, keys=["id"])
        assert len(result) == 2
        assert count == 1
    
    def test_remove_duplicates_all_columns(self, cleaning_service):
        """Test de suppression des doublons sur toutes les colonnes."""
        data = [
            {"id": "1", "value": 10},
            {"id": "2", "value": 20},
            {"id": "1", "value": 10},  # Doublon exact
            {"id": "1", "value": 15},  # Pas un doublon (value différente)
        ]
        result, count = cleaning_service.remove_duplicates(data, keys=None)
        assert len(result) == 3
        assert count == 1
    
    def test_remove_duplicates_empty_list(self, cleaning_service):
        """Test avec liste vide."""
        result, count = cleaning_service.remove_duplicates([])
        assert result == []
        assert count == 0
    
    # ===========================================
    # Tests de gestion des valeurs manquantes
    # ===========================================
    
    def test_handle_missing_remove_strategy(self, cleaning_service):
        """Test de suppression des lignes avec valeurs manquantes."""
        data = [
            {"a": 1, "b": 2},
            {"a": None, "b": 3},
            {"a": 4, "b": 5},
        ]
        result, stats = cleaning_service.handle_missing_values(
            data, strategy="remove", columns=["a", "b"]
        )
        assert len(result) == 2
        assert stats["removed"] == 1
    
    def test_handle_missing_fill_mean(self, cleaning_service):
        """Test de remplissage par la moyenne."""
        data = [
            {"value": 10.0},
            {"value": None},
            {"value": 20.0},
        ]
        result, stats = cleaning_service.handle_missing_values(
            data, strategy="fill", columns=["value"], numeric_strategy="mean"
        )
        assert result[1]["value"] == 15.0  # Moyenne de 10 et 20
        assert stats["filled"] == 1
    
    def test_handle_missing_fill_median(self, cleaning_service):
        """Test de remplissage par la médiane."""
        data = [
            {"value": 10.0},
            {"value": None},
            {"value": 20.0},
            {"value": 100.0},  # Outlier pour différencier mean/median
        ]
        result, stats = cleaning_service.handle_missing_values(
            data, strategy="fill", columns=["value"], numeric_strategy="median"
        )
        # Médiane de [10, 20, 100] = 20
        assert result[1]["value"] == 20.0
    
    def test_handle_missing_fill_zero(self, cleaning_service):
        """Test de remplissage par zéro."""
        data = [
            {"value": 10.0},
            {"value": None},
        ]
        result, stats = cleaning_service.handle_missing_values(
            data, strategy="fill", columns=["value"], numeric_strategy="zero"
        )
        assert result[1]["value"] == 0.0
    
    # ===========================================
    # Tests de suppression des outliers
    # ===========================================
    
    def test_remove_outliers_iqr(self, cleaning_service):
        """Test de suppression des outliers avec méthode IQR."""
        data = [
            {"value": 10},
            {"value": 12},
            {"value": 11},
            {"value": 13},
            {"value": 100},  # Outlier
            {"value": 14},
            {"value": 9},
            {"value": 15},
        ]
        result, stats = cleaning_service.remove_outliers(
            data, columns=["value"], method="iqr", threshold=1.5
        )
        assert stats["removed"] >= 1
        assert all(r["value"] < 50 for r in result)
    
    def test_remove_outliers_zscore(self, cleaning_service):
        """Test de suppression des outliers avec z-score."""
        data = [
            {"value": 10},
            {"value": 12},
            {"value": 11},
            {"value": 13},
            {"value": 1000},  # Outlier extrême
            {"value": 14},
            {"value": 9},
            {"value": 15},
        ]
        result, stats = cleaning_service.remove_outliers(
            data, columns=["value"], method="zscore", threshold=2.0
        )
        assert stats["removed"] >= 1
    
    def test_remove_outliers_empty_columns(self, cleaning_service):
        """Test avec liste de colonnes vide."""
        data = [{"value": 10}, {"value": 100}]
        result, stats = cleaning_service.remove_outliers(data, columns=[])
        assert len(result) == 2
        assert stats["removed"] == 0
    
    # ===========================================
    # Tests de validation des plages
    # ===========================================
    
    def test_validate_ranges_valid_data(self, cleaning_service):
        """Test de validation avec données valides."""
        data = [
            {"temperature": 20.0, "humidity": 50.0},
            {"temperature": 25.0, "humidity": 60.0},
        ]
        rules = {"temperature": (0, 50), "humidity": (0, 100)}
        valid, invalid, stats = cleaning_service.validate_ranges(data, rules)
        assert len(valid) == 2
        assert len(invalid) == 0
    
    def test_validate_ranges_invalid_data(self, cleaning_service):
        """Test de validation avec données hors plage."""
        data = [
            {"temperature": 20.0},
            {"temperature": 100.0},  # Hors plage
        ]
        rules = {"temperature": (0, 50)}
        valid, invalid, stats = cleaning_service.validate_ranges(data, rules)
        assert len(valid) == 1
        assert len(invalid) == 1
        assert stats["invalid"] == 1
    
    # ===========================================
    # Tests de calcul de statistiques
    # ===========================================
    
    def test_get_statistics(self, cleaning_service):
        """Test du calcul des statistiques descriptives."""
        data = [
            {"value": 10.0},
            {"value": 20.0},
            {"value": 30.0},
            {"value": 40.0},
        ]
        stats = cleaning_service.get_statistics(data, columns=["value"])
        
        assert "value" in stats
        assert stats["value"]["count"] == 4
        assert stats["value"]["min"] == 10.0
        assert stats["value"]["max"] == 40.0
        assert stats["value"]["mean"] == 25.0
    
    def test_get_statistics_with_missing(self, cleaning_service):
        """Test des statistiques avec valeurs manquantes."""
        data = [
            {"value": 10.0},
            {"value": None},
            {"value": 30.0},
        ]
        stats = cleaning_service.get_statistics(data, columns=["value"])
        
        assert stats["value"]["count"] == 2
        assert stats["value"]["missing"] == 1
    
    # ===========================================
    # Tests du pipeline complet
    # ===========================================
    
    def test_clean_dataset_full_pipeline(self, cleaning_service, sample_ndjson_file):
        """Test du pipeline complet de nettoyage."""
        config = {
            "schema": {
                "temperature": "float",
                "humidity": "float",
                "CO2": "float"
            },
            "remove_duplicates": True,
            "duplicate_keys": ["timestamp", "ID"],
            "missing_strategy": "fill",
            "missing_columns": ["temperature", "humidity"],
            "numeric_strategy": "median",
            "validate_ranges": True,
            "validation_rules": {
                "temperature": (-40, 60),
                "humidity": (0, 100)
            }
        }
        
        report = cleaning_service.clean_dataset(sample_ndjson_file, config)
        
        assert report["original_count"] == 5
        assert report["final_count"] <= 5  # Des doublons ont été supprimés
        assert "steps" in report
        assert "statistics" in report
        assert "output_file" in report
    
    def test_clean_dataset_default_config(self, cleaning_service, sample_ndjson_file):
        """Test du pipeline avec configuration par défaut."""
        report = cleaning_service.clean_dataset(sample_ndjson_file)
        
        assert report["original_count"] == 5
        assert "steps" in report
        assert len(report["steps"]) >= 3  # Au moins 3 étapes
    
    # ===========================================
    # Tests de sauvegarde
    # ===========================================
    
    def test_save_cleaned_data_ndjson(self, cleaning_service, temp_data_dir):
        """Test de sauvegarde en format NDJSON."""
        data = [{"a": 1}, {"a": 2}]
        filepath = cleaning_service.save_cleaned_data(data, "output.json", format="ndjson")
        
        assert Path(filepath).exists()
        
        # Vérifier le contenu
        with open(filepath) as f:
            lines = f.readlines()
            assert len(lines) == 2
    
    def test_save_cleaned_data_json(self, cleaning_service, temp_data_dir):
        """Test de sauvegarde en format JSON standard."""
        data = [{"a": 1}, {"a": 2}]
        filepath = cleaning_service.save_cleaned_data(data, "output.json", format="json")
        
        assert Path(filepath).exists()
        
        # Vérifier le contenu
        with open(filepath) as f:
            loaded = json.load(f)
            assert len(loaded) == 2


class TestIsNan:
    """Tests pour la détection des valeurs NaN."""
    
    def test_is_nan_none(self, cleaning_service):
        assert cleaning_service._is_nan(None) is True
    
    def test_is_nan_string_nan(self, cleaning_service):
        assert cleaning_service._is_nan("nan") is True
        assert cleaning_service._is_nan("NaN") is True
        assert cleaning_service._is_nan("NAN") is True
    
    def test_is_nan_string_null(self, cleaning_service):
        assert cleaning_service._is_nan("null") is True
        assert cleaning_service._is_nan("NULL") is True
    
    def test_is_nan_empty_string(self, cleaning_service):
        assert cleaning_service._is_nan("") is True
    
    def test_is_nan_valid_value(self, cleaning_service):
        assert cleaning_service._is_nan(123) is False
        assert cleaning_service._is_nan("hello") is False
        assert cleaning_service._is_nan(0) is False


class TestConvertValue:
    """Tests pour la conversion de valeurs."""
    
    def test_convert_to_float(self, cleaning_service):
        assert cleaning_service._convert_value("123.45", "float") == 123.45
    
    def test_convert_to_int(self, cleaning_service):
        assert cleaning_service._convert_value("123.9", "int") == 123
    
    def test_convert_to_bool_true(self, cleaning_service):
        assert cleaning_service._convert_value("true", "bool") is True
        assert cleaning_service._convert_value("1", "bool") is True
        assert cleaning_service._convert_value("yes", "bool") is True
    
    def test_convert_to_bool_false(self, cleaning_service):
        assert cleaning_service._convert_value("false", "bool") is False
        assert cleaning_service._convert_value("0", "bool") is False
    
    def test_convert_invalid_returns_none(self, cleaning_service):
        assert cleaning_service._convert_value("abc", "float") is None
        assert cleaning_service._convert_value("xyz", "int") is None
