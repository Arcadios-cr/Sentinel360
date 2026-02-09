"""
F3-UC1 : Tests pour la détection de dérive de performance (Performance Drift).

Ce module teste :
- Détection de dérive selon les seuils (low, medium, high)
- Calcul du ratio RMSE
- Gestion des cas limites (baseline manquant, invalide)
"""

import pytest
from app.services.drift import detect_performance_drift


class TestPerformanceDriftDetection:
    """Tests de détection de dérive de performance."""

    # ==================== CAS SANS DÉRIVE ====================

    def test_no_drift_when_rmse_equals_baseline(self):
        """Pas de drift si RMSE == baseline."""
        result = detect_performance_drift(current_rmse=0.20, baseline_rmse=0.20)
        
        assert result["drift_detected"] == False
        assert result["severity"] == "low"
        assert result["ratio"] == pytest.approx(1.0, abs=1e-9)
        assert result["reason"] == "performance stable"

    def test_no_drift_when_rmse_below_baseline(self):
        """Pas de drift si RMSE < baseline (amélioration)."""
        result = detect_performance_drift(current_rmse=0.15, baseline_rmse=0.20)
        
        assert result["drift_detected"] == False
        assert result["severity"] == "low"
        assert result["ratio"] == pytest.approx(0.75, abs=1e-9)

    def test_no_drift_when_rmse_slightly_above_baseline(self):
        """Pas de drift si RMSE < 10% au-dessus du baseline."""
        result = detect_performance_drift(current_rmse=0.21, baseline_rmse=0.20)
        
        assert result["drift_detected"] == False
        assert result["severity"] == "low"
        assert result["ratio"] == pytest.approx(1.05, abs=1e-9)

    # ==================== DÉRIVE MEDIUM (10-25%) ====================

    def test_medium_drift_at_10_percent(self):
        """Drift medium exactement à +10%."""
        result = detect_performance_drift(current_rmse=0.22, baseline_rmse=0.20)
        
        assert result["drift_detected"] == True
        assert result["severity"] == "medium"
        assert result["ratio"] == pytest.approx(1.10, abs=1e-9)
        assert result["reason"] == "dégradation modérée de performance"

    def test_medium_drift_at_15_percent(self):
        """Drift medium à +15%."""
        result = detect_performance_drift(current_rmse=0.23, baseline_rmse=0.20)
        
        assert result["drift_detected"] == True
        assert result["severity"] == "medium"
        assert result["ratio"] == pytest.approx(1.15, abs=1e-9)

    def test_medium_drift_just_below_high_threshold(self):
        """Drift medium juste sous le seuil high (24%)."""
        result = detect_performance_drift(current_rmse=0.248, baseline_rmse=0.20)
        
        assert result["drift_detected"] == True
        assert result["severity"] == "medium"

    # ==================== DÉRIVE HIGH (>=25%) ====================

    def test_high_drift_at_25_percent(self):
        """Drift high exactement à +25%."""
        result = detect_performance_drift(current_rmse=0.25, baseline_rmse=0.20)
        
        assert result["drift_detected"] == True
        assert result["severity"] == "high"
        assert result["ratio"] == pytest.approx(1.25, abs=1e-9)
        assert result["reason"] == "dégradation forte de performance"

    def test_high_drift_at_50_percent(self):
        """Drift high à +50%."""
        result = detect_performance_drift(current_rmse=0.30, baseline_rmse=0.20)
        
        assert result["drift_detected"] == True
        assert result["severity"] == "high"
        assert result["ratio"] == pytest.approx(1.50, abs=1e-9)

    def test_high_drift_at_100_percent(self):
        """Drift high à +100% (RMSE doublé)."""
        result = detect_performance_drift(current_rmse=0.40, baseline_rmse=0.20)
        
        assert result["drift_detected"] == True
        assert result["severity"] == "high"
        assert result["ratio"] == pytest.approx(2.0, abs=1e-9)

    # ==================== CALCULS DELTA ====================

    def test_delta_calculation_positive(self):
        """Vérifie le calcul du delta (augmentation)."""
        result = detect_performance_drift(current_rmse=0.25, baseline_rmse=0.20)
        
        assert result["delta"] == pytest.approx(0.05, abs=1e-9)

    def test_delta_calculation_negative(self):
        """Vérifie le calcul du delta (amélioration)."""
        result = detect_performance_drift(current_rmse=0.15, baseline_rmse=0.20)
        
        assert result["delta"] == pytest.approx(-0.05, abs=1e-9)

    # ==================== CAS LIMITES ====================

    def test_baseline_none(self):
        """Gestion du baseline manquant (None)."""
        result = detect_performance_drift(current_rmse=0.25, baseline_rmse=None)
        
        assert result["drift_detected"] == False
        assert result["severity"] == "unknown"
        assert result["ratio"] is None
        assert result["delta"] is None
        assert "baseline_rmse manquant" in result["reason"]

    def test_baseline_zero(self):
        """Gestion du baseline à zéro."""
        result = detect_performance_drift(current_rmse=0.25, baseline_rmse=0.0)
        
        assert result["drift_detected"] == False
        assert result["severity"] == "unknown"
        assert result["ratio"] is None

    def test_baseline_negative(self):
        """Gestion du baseline négatif (invalide)."""
        result = detect_performance_drift(current_rmse=0.25, baseline_rmse=-0.5)
        
        assert result["drift_detected"] == False
        assert result["severity"] == "unknown"

    def test_current_rmse_zero(self):
        """RMSE actuel à zéro (prédiction parfaite)."""
        result = detect_performance_drift(current_rmse=0.0, baseline_rmse=0.20)
        
        assert result["drift_detected"] == False
        assert result["severity"] == "low"
        assert result["ratio"] == pytest.approx(0.0, abs=1e-9)

    # ==================== SEUILS PERSONNALISÉS ====================

    def test_custom_warn_ratio(self):
        """Test avec seuil warn personnalisé."""
        result = detect_performance_drift(
            current_rmse=0.21, 
            baseline_rmse=0.20, 
            warn_ratio=1.05  # 5% au lieu de 10%
        )
        
        assert result["drift_detected"] == True
        assert result["severity"] == "medium"

    def test_custom_alert_ratio(self):
        """Test avec seuil alert personnalisé."""
        result = detect_performance_drift(
            current_rmse=0.24, 
            baseline_rmse=0.20, 
            alert_ratio=1.20  # 20% au lieu de 25%
        )
        
        assert result["drift_detected"] == True
        assert result["severity"] == "high"

    # ==================== RETOUR COMPLET ====================

    def test_return_structure(self):
        """Vérifie la structure complète du retour."""
        result = detect_performance_drift(current_rmse=0.25, baseline_rmse=0.20)
        
        assert "baseline_rmse" in result
        assert "current_rmse" in result
        assert "ratio" in result
        assert "delta" in result
        assert "severity" in result
        assert "drift_detected" in result
        assert "reason" in result
        
        assert isinstance(result["baseline_rmse"], float)
        assert isinstance(result["current_rmse"], float)
        assert isinstance(result["ratio"], float)
        assert isinstance(result["delta"], float)
        assert isinstance(result["severity"], str)
        assert isinstance(result["drift_detected"], bool)
        assert isinstance(result["reason"], str)

    def test_severity_values(self):
        """Vérifie que severity est dans les valeurs attendues."""
        valid_severities = {"low", "medium", "high", "unknown"}
        
        # Test plusieurs cas
        result1 = detect_performance_drift(current_rmse=0.20, baseline_rmse=0.20)
        result2 = detect_performance_drift(current_rmse=0.22, baseline_rmse=0.20)
        result3 = detect_performance_drift(current_rmse=0.30, baseline_rmse=0.20)
        result4 = detect_performance_drift(current_rmse=0.20, baseline_rmse=None)
        
        assert result1["severity"] in valid_severities
        assert result2["severity"] in valid_severities
        assert result3["severity"] in valid_severities
        assert result4["severity"] in valid_severities


class TestPerformanceDriftEdgeCases:
    """Tests des cas limites et valeurs extrêmes."""

    def test_very_small_values(self):
        """Test avec de très petites valeurs."""
        result = detect_performance_drift(current_rmse=0.0001, baseline_rmse=0.0001)
        
        assert result["ratio"] == pytest.approx(1.0, abs=1e-6)
        assert result["drift_detected"] == False

    def test_very_large_values(self):
        """Test avec de très grandes valeurs."""
        result = detect_performance_drift(current_rmse=1000.0, baseline_rmse=500.0)
        
        assert result["ratio"] == pytest.approx(2.0, abs=1e-9)
        assert result["drift_detected"] == True
        assert result["severity"] == "high"

    def test_same_rmse_different_scales(self):
        """Test avec des échelles différentes."""
        # Petite échelle
        result1 = detect_performance_drift(current_rmse=0.02, baseline_rmse=0.01)
        
        # Grande échelle
        result2 = detect_performance_drift(current_rmse=200, baseline_rmse=100)
        
        # Les ratios doivent être identiques
        assert result1["ratio"] == pytest.approx(result2["ratio"], abs=1e-9)
