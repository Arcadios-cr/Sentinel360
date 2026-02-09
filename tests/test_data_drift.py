"""
F3-UC2 : Tests pour la détection de dérive des données (Data Drift).

Ce module teste :
- Détection de drift via le test de Kolmogorov-Smirnov
- Analyse multi-features
- Gestion des cas limites (peu de données, features manquantes)
"""

import pytest
from app.services.data_drift import detect_data_drift


class TestDataDriftDetection:
    """Tests de détection de dérive des données."""

    # ==================== CAS SANS DÉRIVE ====================

    def test_no_drift_identical_distributions(self):
        """Pas de drift si distributions identiques."""
        reference = {"temperature": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0]}
        current = {"temperature": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0]}
        
        result = detect_data_drift(reference, current)
        
        assert result["global_drift"] == False
        assert result["features_drifted"] == 0
        assert result["feature_results"]["temperature"]["drift_detected"] == False

    def test_no_drift_similar_distributions(self):
        """Pas de drift si distributions similaires."""
        reference = {"humidity": [50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0]}
        current = {"humidity": [50.5, 51.5, 52.5, 53.5, 54.5, 55.5, 56.5, 57.5, 58.5, 59.5]}
        
        result = detect_data_drift(reference, current)
        
        assert result["global_drift"] == False

    # ==================== CAS AVEC DÉRIVE ====================

    def test_drift_completely_different_distributions(self):
        """Drift détecté si distributions complètement différentes."""
        reference = {"temperature": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0]}
        current = {"temperature": [40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0]}
        
        result = detect_data_drift(reference, current)
        
        assert result["global_drift"] == True
        assert result["features_drifted"] == 1
        assert result["feature_results"]["temperature"]["drift_detected"] == True

    def test_drift_shifted_distribution(self):
        """Drift détecté si distribution décalée significativement."""
        reference = {"co2": [400, 410, 420, 430, 440, 450, 460, 470, 480, 490]}
        current = {"co2": [600, 610, 620, 630, 640, 650, 660, 670, 680, 690]}
        
        result = detect_data_drift(reference, current)
        
        assert result["global_drift"] == True
        assert result["feature_results"]["co2"]["drift_detected"] == True

    # ==================== MULTI-FEATURES ====================

    def test_multiple_features_no_drift(self):
        """Test avec plusieurs features, aucun drift."""
        reference = {
            "temperature": [20.0, 21.0, 22.0, 23.0, 24.0],
            "humidity": [50.0, 51.0, 52.0, 53.0, 54.0],
            "co2": [400, 410, 420, 430, 440]
        }
        current = {
            "temperature": [20.0, 21.0, 22.0, 23.0, 24.0],
            "humidity": [50.0, 51.0, 52.0, 53.0, 54.0],
            "co2": [400, 410, 420, 430, 440]
        }
        
        result = detect_data_drift(reference, current)
        
        assert result["global_drift"] == False
        assert result["features_compared"] == 3
        assert result["features_drifted"] == 0

    def test_multiple_features_partial_drift(self):
        """Test avec plusieurs features, drift partiel."""
        reference = {
            "temperature": [20.0, 21.0, 22.0, 23.0, 24.0],
            "humidity": [50.0, 51.0, 52.0, 53.0, 54.0]
        }
        current = {
            "temperature": [20.0, 21.0, 22.0, 23.0, 24.0],  # Pas de drift
            "humidity": [80.0, 81.0, 82.0, 83.0, 84.0]      # Drift
        }
        
        result = detect_data_drift(reference, current)
        
        assert result["global_drift"] == True
        assert result["features_compared"] == 2
        assert result["features_drifted"] == 1
        assert result["feature_results"]["temperature"]["drift_detected"] == False
        assert result["feature_results"]["humidity"]["drift_detected"] == True

    def test_multiple_features_all_drift(self):
        """Test avec plusieurs features, tous en drift."""
        reference = {
            "temperature": [20.0, 21.0, 22.0, 23.0, 24.0],
            "humidity": [50.0, 51.0, 52.0, 53.0, 54.0]
        }
        current = {
            "temperature": [40.0, 41.0, 42.0, 43.0, 44.0],  # Drift
            "humidity": [80.0, 81.0, 82.0, 83.0, 84.0]      # Drift
        }
        
        result = detect_data_drift(reference, current)
        
        assert result["global_drift"] == True
        assert result["features_drifted"] == 2

    # ==================== STATISTIQUE KS ====================

    def test_ks_statistic_returned(self):
        """Vérifie que la statistique KS est retournée."""
        reference = {"temp": [20.0, 21.0, 22.0, 23.0, 24.0]}
        current = {"temp": [25.0, 26.0, 27.0, 28.0, 29.0]}
        
        result = detect_data_drift(reference, current)
        
        assert "ks_stat" in result["feature_results"]["temp"]
        assert "ks_crit" in result["feature_results"]["temp"]
        assert 0 <= result["feature_results"]["temp"]["ks_stat"] <= 1

    def test_ks_statistic_zero_for_identical(self):
        """KS statistic = 0 pour distributions identiques."""
        reference = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0]}
        current = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0]}
        
        result = detect_data_drift(reference, current)
        
        assert result["feature_results"]["temp"]["ks_stat"] == pytest.approx(0.0, abs=1e-9)

    def test_ks_statistic_one_for_completely_separated(self):
        """KS statistic = 1 pour distributions complètement séparées."""
        reference = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0]}
        current = {"temp": [10.0, 11.0, 12.0, 13.0, 14.0]}
        
        result = detect_data_drift(reference, current)
        
        assert result["feature_results"]["temp"]["ks_stat"] == pytest.approx(1.0, abs=1e-9)

    # ==================== SEUIL ALPHA ====================

    def test_default_alpha(self):
        """Test avec alpha par défaut (0.05)."""
        reference = {"temp": [20.0, 21.0, 22.0, 23.0, 24.0]}
        current = {"temp": [20.0, 21.0, 22.0, 23.0, 24.0]}
        
        result = detect_data_drift(reference, current)
        
        assert result["alpha"] == 0.05

    def test_custom_alpha_strict(self):
        """Test avec alpha strict (0.01)."""
        reference = {"temp": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0]}
        current = {"temp": [22.0, 23.0, 24.0, 25.0, 26.0, 27.0]}
        
        result = detect_data_drift(reference, current, alpha=0.01)
        
        assert result["alpha"] == 0.01

    def test_invalid_alpha_zero(self):
        """Alpha = 0 doit lever une erreur."""
        reference = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0]}
        current = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0]}
        
        with pytest.raises(ValueError, match="alpha doit être entre 0 et 1"):
            detect_data_drift(reference, current, alpha=0)

    def test_invalid_alpha_one(self):
        """Alpha = 1 doit lever une erreur."""
        reference = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0]}
        current = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0]}
        
        with pytest.raises(ValueError, match="alpha doit être entre 0 et 1"):
            detect_data_drift(reference, current, alpha=1)

    def test_invalid_alpha_negative(self):
        """Alpha négatif doit lever une erreur."""
        reference = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0]}
        current = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0]}
        
        with pytest.raises(ValueError, match="alpha doit être entre 0 et 1"):
            detect_data_drift(reference, current, alpha=-0.1)

    # ==================== CAS LIMITES ====================

    def test_insufficient_data_skipped(self):
        """Feature ignorée si moins de 5 valeurs."""
        reference = {"temp": [1.0, 2.0, 3.0]}  # Seulement 3 valeurs
        current = {"temp": [1.0, 2.0, 3.0]}
        
        result = detect_data_drift(reference, current)
        
        assert result["feature_results"]["temp"]["status"] == "skipped"
        assert "pas assez de données" in result["feature_results"]["temp"]["reason"]
        assert result["features_compared"] == 0

    def test_only_common_features_compared(self):
        """Seules les features communes sont comparées."""
        reference = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0], "humidity": [50, 51, 52, 53, 54]}
        current = {"temp": [1.0, 2.0, 3.0, 4.0, 5.0], "co2": [400, 410, 420, 430, 440]}
        
        result = detect_data_drift(reference, current)
        
        # Seule "temp" est commune
        assert "temp" in result["feature_results"]
        assert "humidity" not in result["feature_results"]
        assert "co2" not in result["feature_results"]

    def test_empty_features(self):
        """Test avec features vides."""
        reference = {}
        current = {}
        
        result = detect_data_drift(reference, current)
        
        assert result["features_compared"] == 0
        assert result["features_drifted"] == 0
        assert result["global_drift"] == False

    # ==================== STRUCTURE DU RETOUR ====================

    def test_return_structure(self):
        """Vérifie la structure complète du retour."""
        reference = {"temp": [20.0, 21.0, 22.0, 23.0, 24.0]}
        current = {"temp": [25.0, 26.0, 27.0, 28.0, 29.0]}
        
        result = detect_data_drift(reference, current)
        
        assert "alpha" in result
        assert "features_compared" in result
        assert "features_drifted" in result
        assert "global_drift" in result
        assert "feature_results" in result
        
        assert isinstance(result["alpha"], float)
        assert isinstance(result["features_compared"], int)
        assert isinstance(result["features_drifted"], int)
        assert isinstance(result["global_drift"], bool)
        assert isinstance(result["feature_results"], dict)

    def test_feature_result_structure(self):
        """Vérifie la structure du résultat par feature."""
        reference = {"temp": [20.0, 21.0, 22.0, 23.0, 24.0]}
        current = {"temp": [25.0, 26.0, 27.0, 28.0, 29.0]}
        
        result = detect_data_drift(reference, current)
        feature_result = result["feature_results"]["temp"]
        
        assert "status" in feature_result
        assert "n_ref" in feature_result
        assert "n_cur" in feature_result
        assert "ks_stat" in feature_result
        assert "ks_crit" in feature_result
        assert "drift_detected" in feature_result


class TestDataDriftEdgeCases:
    """Tests des cas limites et valeurs extrêmes."""

    def test_large_datasets(self):
        """Test avec de grands ensembles de données."""
        import random
        random.seed(42)
        
        reference = {"temp": [random.gauss(20, 5) for _ in range(1000)]}
        current = {"temp": [random.gauss(20, 5) for _ in range(1000)]}
        
        result = detect_data_drift(reference, current)
        
        # Même distribution, pas de drift attendu
        assert result["feature_results"]["temp"]["status"] == "ok"

    def test_different_sample_sizes(self):
        """Test avec tailles d'échantillons différentes."""
        reference = {"temp": [20.0, 21.0, 22.0, 23.0, 24.0]}
        current = {"temp": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0]}
        
        result = detect_data_drift(reference, current)
        
        assert result["feature_results"]["temp"]["n_ref"] == 5
        assert result["feature_results"]["temp"]["n_cur"] == 10

    def test_negative_values(self):
        """Test avec des valeurs négatives."""
        reference = {"temp": [-10.0, -5.0, 0.0, 5.0, 10.0]}
        current = {"temp": [-10.0, -5.0, 0.0, 5.0, 10.0]}
        
        result = detect_data_drift(reference, current)
        
        assert result["global_drift"] == False

    def test_mixed_positive_negative(self):
        """Test avec mélange de valeurs positives et négatives."""
        reference = {"delta": [-5.0, -2.0, 0.0, 2.0, 5.0]}
        current = {"delta": [10.0, 12.0, 15.0, 18.0, 20.0]}
        
        result = detect_data_drift(reference, current)
        
        assert result["global_drift"] == True
