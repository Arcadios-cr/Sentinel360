"""
F2-UC2 : Tester la validité des résultats via des cas de référence connus.

Ce module contient les tests unitaires pour valider le calcul des métriques
de performance (MAE, MSE, RMSE, R²) en utilisant des cas de référence
dont les résultats attendus sont calculés manuellement.
"""

import pytest
import math
from app.services.metrics import compute_metrics


class TestMetricsValidation:
    """
    Tests de validation des métriques avec des cas de référence connus.
    Les valeurs attendues sont calculées manuellement pour garantir la précision.
    """

    # ==================== CAS DE RÉFÉRENCE 1 ====================
    # Cas simple avec des valeurs entières faciles à vérifier
    # y_true = [1, 2, 3, 4, 5]
    # y_pred = [1, 2, 3, 4, 5]
    # Prédiction parfaite → toutes les erreurs = 0

    def test_perfect_prediction(self):
        """Test avec prédiction parfaite : erreurs nulles."""
        y_true = [1.0, 2.0, 3.0, 4.0, 5.0]
        y_pred = [1.0, 2.0, 3.0, 4.0, 5.0]

        result = compute_metrics(y_true, y_pred)

        # Calculs manuels :
        # Erreurs = [0, 0, 0, 0, 0]
        # MAE = 0, MSE = 0, RMSE = 0, R² = 1
        assert result["mae"] == pytest.approx(0.0, abs=1e-9)
        assert result["mse"] == pytest.approx(0.0, abs=1e-9)
        assert result["rmse"] == pytest.approx(0.0, abs=1e-9)
        assert result["r2"] == pytest.approx(1.0, abs=1e-9)

    # ==================== CAS DE RÉFÉRENCE 2 ====================
    # Cas avec erreur constante
    # y_true = [10, 20, 30, 40, 50]
    # y_pred = [11, 21, 31, 41, 51]
    # Chaque prédiction est surestimée de 1

    def test_constant_error(self):
        """Test avec erreur constante de +1 sur chaque prédiction."""
        y_true = [10.0, 20.0, 30.0, 40.0, 50.0]
        y_pred = [11.0, 21.0, 31.0, 41.0, 51.0]

        result = compute_metrics(y_true, y_pred)

        # Calculs manuels :
        # Erreurs = [-1, -1, -1, -1, -1]
        # MAE = (1+1+1+1+1)/5 = 1.0
        # MSE = (1+1+1+1+1)/5 = 1.0
        # RMSE = sqrt(1.0) = 1.0
        # mean_y = 30, ss_tot = 1000, ss_res = 5, R² = 1 - 5/1000 = 0.995
        assert result["mae"] == pytest.approx(1.0, abs=1e-9)
        assert result["mse"] == pytest.approx(1.0, abs=1e-9)
        assert result["rmse"] == pytest.approx(1.0, abs=1e-9)
        assert result["r2"] == pytest.approx(0.995, abs=1e-9)

    # ==================== CAS DE RÉFÉRENCE 3 ====================
    # Cas avec erreurs mixtes (positives et négatives)
    # y_true = [3, 5, 2, 7]
    # y_pred = [2, 6, 3, 8]
    # Erreurs = [1, -1, -1, -1]

    def test_mixed_errors(self):
        """Test avec erreurs mixtes positives et négatives."""
        y_true = [3.0, 5.0, 2.0, 7.0]
        y_pred = [2.0, 6.0, 3.0, 8.0]

        result = compute_metrics(y_true, y_pred)

        # Calculs manuels :
        # Erreurs = [3-2, 5-6, 2-3, 7-8] = [1, -1, -1, -1]
        # MAE = (|1|+|-1|+|-1|+|-1|)/4 = 4/4 = 1.0
        # MSE = (1+1+1+1)/4 = 1.0
        # RMSE = sqrt(1.0) = 1.0
        # mean_y = (3+5+2+7)/4 = 4.25
        # ss_tot = (3-4.25)² + (5-4.25)² + (2-4.25)² + (7-4.25)²
        #        = 1.5625 + 0.5625 + 5.0625 + 7.5625 = 14.75
        # ss_res = 1 + 1 + 1 + 1 = 4
        # R² = 1 - 4/14.75 = 1 - 0.2712 = 0.7288...
        expected_r2 = 1 - (4 / 14.75)

        assert result["mae"] == pytest.approx(1.0, abs=1e-9)
        assert result["mse"] == pytest.approx(1.0, abs=1e-9)
        assert result["rmse"] == pytest.approx(1.0, abs=1e-9)
        assert result["r2"] == pytest.approx(expected_r2, abs=1e-9)

    # ==================== CAS DE RÉFÉRENCE 4 ====================
    # Cas avec valeurs décimales
    # y_true = [2.5, 3.5, 4.5]
    # y_pred = [2.0, 4.0, 4.0]

    def test_decimal_values(self):
        """Test avec des valeurs décimales."""
        y_true = [2.5, 3.5, 4.5]
        y_pred = [2.0, 4.0, 4.0]

        result = compute_metrics(y_true, y_pred)

        # Calculs manuels :
        # Erreurs = [2.5-2.0, 3.5-4.0, 4.5-4.0] = [0.5, -0.5, 0.5]
        # MAE = (0.5+0.5+0.5)/3 = 0.5
        # MSE = (0.25+0.25+0.25)/3 = 0.25
        # RMSE = sqrt(0.25) = 0.5
        # mean_y = 3.5
        # ss_tot = (2.5-3.5)² + (3.5-3.5)² + (4.5-3.5)² = 1 + 0 + 1 = 2
        # ss_res = 0.25 + 0.25 + 0.25 = 0.75
        # R² = 1 - 0.75/2 = 0.625
        assert result["mae"] == pytest.approx(0.5, abs=1e-9)
        assert result["mse"] == pytest.approx(0.25, abs=1e-9)
        assert result["rmse"] == pytest.approx(0.5, abs=1e-9)
        assert result["r2"] == pytest.approx(0.625, abs=1e-9)

    # ==================== CAS DE RÉFÉRENCE 5 ====================
    # Cas avec grandes erreurs
    # y_true = [100, 200, 300]
    # y_pred = [110, 180, 330]

    def test_large_values_and_errors(self):
        """Test avec des valeurs et erreurs importantes."""
        y_true = [100.0, 200.0, 300.0]
        y_pred = [110.0, 180.0, 330.0]

        result = compute_metrics(y_true, y_pred)

        # Calculs manuels :
        # Erreurs = [100-110, 200-180, 300-330] = [-10, 20, -30]
        # MAE = (10+20+30)/3 = 20.0
        # MSE = (100+400+900)/3 = 1400/3 ≈ 466.6667
        # RMSE = sqrt(466.6667) ≈ 21.6025
        # mean_y = 200
        # ss_tot = (100-200)² + (200-200)² + (300-200)² = 10000 + 0 + 10000 = 20000
        # ss_res = 100 + 400 + 900 = 1400
        # R² = 1 - 1400/20000 = 0.93
        expected_mse = 1400 / 3
        expected_rmse = math.sqrt(expected_mse)

        assert result["mae"] == pytest.approx(20.0, abs=1e-9)
        assert result["mse"] == pytest.approx(expected_mse, abs=1e-9)
        assert result["rmse"] == pytest.approx(expected_rmse, abs=1e-6)
        assert result["r2"] == pytest.approx(0.93, abs=1e-9)

    # ==================== CAS DE RÉFÉRENCE 6 ====================
    # Cas R² négatif (prédictions pires que la moyenne)
    # y_true = [1, 2, 3]
    # y_pred = [3, 2, 1] (inversé)

    def test_negative_r2(self):
        """Test avec R² négatif - prédictions inversées."""
        y_true = [1.0, 2.0, 3.0]
        y_pred = [3.0, 2.0, 1.0]

        result = compute_metrics(y_true, y_pred)

        # Calculs manuels :
        # Erreurs = [1-3, 2-2, 3-1] = [-2, 0, 2]
        # MAE = (2+0+2)/3 = 4/3 ≈ 1.3333
        # MSE = (4+0+4)/3 = 8/3 ≈ 2.6667
        # RMSE = sqrt(8/3) ≈ 1.6330
        # mean_y = 2
        # ss_tot = (1-2)² + (2-2)² + (3-2)² = 1 + 0 + 1 = 2
        # ss_res = 4 + 0 + 4 = 8
        # R² = 1 - 8/2 = -3.0
        expected_mae = 4 / 3
        expected_mse = 8 / 3
        expected_rmse = math.sqrt(expected_mse)

        assert result["mae"] == pytest.approx(expected_mae, abs=1e-9)
        assert result["mse"] == pytest.approx(expected_mse, abs=1e-9)
        assert result["rmse"] == pytest.approx(expected_rmse, abs=1e-6)
        assert result["r2"] == pytest.approx(-3.0, abs=1e-9)

    # ==================== CAS DE RÉFÉRENCE 7 ====================
    # Cas avec deux valeurs seulement

    def test_minimal_data(self):
        """Test avec le minimum de données (2 points)."""
        y_true = [0.0, 10.0]
        y_pred = [1.0, 9.0]

        result = compute_metrics(y_true, y_pred)

        # Calculs manuels :
        # Erreurs = [0-1, 10-9] = [-1, 1]
        # MAE = (1+1)/2 = 1.0
        # MSE = (1+1)/2 = 1.0
        # RMSE = 1.0
        # mean_y = 5
        # ss_tot = (0-5)² + (10-5)² = 25 + 25 = 50
        # ss_res = 1 + 1 = 2
        # R² = 1 - 2/50 = 0.96
        assert result["mae"] == pytest.approx(1.0, abs=1e-9)
        assert result["mse"] == pytest.approx(1.0, abs=1e-9)
        assert result["rmse"] == pytest.approx(1.0, abs=1e-9)
        assert result["r2"] == pytest.approx(0.96, abs=1e-9)


class TestMetricsEdgeCases:
    """Tests des cas limites et gestion des erreurs."""

    def test_empty_lists_raises_error(self):
        """Test que des listes vides lèvent une exception."""
        with pytest.raises(ValueError, match="vides"):
            compute_metrics([], [])

    def test_different_lengths_raises_error(self):
        """Test que des listes de tailles différentes lèvent une exception."""
        with pytest.raises(ValueError, match="même taille"):
            compute_metrics([1, 2, 3], [1, 2])

    def test_single_value_with_zero_variance(self):
        """Test avec une seule valeur (ss_tot = 0)."""
        # Ce cas produit un ss_tot = 0, donc R² devrait être 0 par convention
        y_true = [5.0]
        y_pred = [5.0]
        
        # Vérifie que le code gère ce cas limite
        result = compute_metrics(y_true, y_pred)
        assert result["mae"] == pytest.approx(0.0, abs=1e-9)
        assert result["mse"] == pytest.approx(0.0, abs=1e-9)
        assert result["rmse"] == pytest.approx(0.0, abs=1e-9)
        # R² = 0 quand ss_tot = 0 (selon l'implémentation)
        assert result["r2"] == pytest.approx(0.0, abs=1e-9)

    def test_constant_y_true_values(self):
        """Test avec y_true constant (variance nulle)."""
        y_true = [5.0, 5.0, 5.0, 5.0]
        y_pred = [4.0, 5.0, 6.0, 5.0]

        result = compute_metrics(y_true, y_pred)

        # Erreurs = [1, 0, -1, 0]
        # MAE = 2/4 = 0.5
        # MSE = 2/4 = 0.5
        # RMSE = sqrt(0.5)
        # ss_tot = 0 → R² = 0 par convention
        assert result["mae"] == pytest.approx(0.5, abs=1e-9)
        assert result["mse"] == pytest.approx(0.5, abs=1e-9)
        assert result["rmse"] == pytest.approx(math.sqrt(0.5), abs=1e-9)
        assert result["r2"] == pytest.approx(0.0, abs=1e-9)


class TestMetricsProperties:
    """Tests des propriétés mathématiques des métriques."""

    def test_mae_is_non_negative(self):
        """MAE doit toujours être >= 0."""
        y_true = [1.0, -2.0, 3.0, -4.0, 5.0]
        y_pred = [2.0, -1.0, 4.0, -3.0, 6.0]

        result = compute_metrics(y_true, y_pred)
        assert result["mae"] >= 0

    def test_mse_is_non_negative(self):
        """MSE doit toujours être >= 0."""
        y_true = [1.0, -2.0, 3.0, -4.0, 5.0]
        y_pred = [2.0, -1.0, 4.0, -3.0, 6.0]

        result = compute_metrics(y_true, y_pred)
        assert result["mse"] >= 0

    def test_rmse_is_non_negative(self):
        """RMSE doit toujours être >= 0."""
        y_true = [1.0, -2.0, 3.0, -4.0, 5.0]
        y_pred = [2.0, -1.0, 4.0, -3.0, 6.0]

        result = compute_metrics(y_true, y_pred)
        assert result["rmse"] >= 0

    def test_rmse_equals_sqrt_mse(self):
        """RMSE doit être égal à sqrt(MSE)."""
        y_true = [10.0, 20.0, 30.0, 40.0]
        y_pred = [12.0, 18.0, 33.0, 38.0]

        result = compute_metrics(y_true, y_pred)
        assert result["rmse"] == pytest.approx(math.sqrt(result["mse"]), abs=1e-9)

    def test_mae_less_than_or_equal_rmse(self):
        """MAE doit être <= RMSE (propriété mathématique)."""
        y_true = [1.0, 5.0, 10.0, 15.0, 20.0]
        y_pred = [2.0, 4.0, 12.0, 14.0, 22.0]

        result = compute_metrics(y_true, y_pred)
        assert result["mae"] <= result["rmse"]

    def test_r2_bounded_above_by_one(self):
        """R² doit être <= 1."""
        y_true = [1.0, 2.0, 3.0, 4.0, 5.0]
        y_pred = [1.1, 2.2, 2.9, 4.1, 4.8]

        result = compute_metrics(y_true, y_pred)
        assert result["r2"] <= 1.0


# ==================== TESTS COMPARATIFS ====================
# Ces tests comparent avec des calculs sklearn (commentés comme référence)

class TestMetricsComparisonReference:
    """
    Tests de comparaison avec les valeurs de référence.
    Les valeurs attendues correspondent aux résultats sklearn.
    """

    def test_sklearn_reference_case_1(self):
        """
        Cas de référence calculé avec sklearn :
        >>> from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        >>> y_true = [3, -0.5, 2, 7]
        >>> y_pred = [2.5, 0.0, 2, 8]
        >>> mean_absolute_error(y_true, y_pred)  # 0.5
        >>> mean_squared_error(y_true, y_pred)   # 0.375
        >>> r2_score(y_true, y_pred)             # 0.9486...
        """
        y_true = [3.0, -0.5, 2.0, 7.0]
        y_pred = [2.5, 0.0, 2.0, 8.0]

        result = compute_metrics(y_true, y_pred)

        # Valeurs sklearn de référence
        assert result["mae"] == pytest.approx(0.5, abs=1e-6)
        assert result["mse"] == pytest.approx(0.375, abs=1e-6)
        assert result["rmse"] == pytest.approx(math.sqrt(0.375), abs=1e-6)
        # R² calculé : 1 - 1.5/29.1875 ≈ 0.9486
        expected_r2 = 1 - (1.5 / 29.1875)
        assert result["r2"] == pytest.approx(expected_r2, abs=1e-4)

    def test_sklearn_reference_case_2(self):
        """
        Autre cas de référence sklearn :
        >>> y_true = [1, 2, 3, 4, 5]
        >>> y_pred = [1.2, 1.8, 3.1, 3.9, 5.2]
        """
        y_true = [1.0, 2.0, 3.0, 4.0, 5.0]
        y_pred = [1.2, 1.8, 3.1, 3.9, 5.2]

        result = compute_metrics(y_true, y_pred)

        # Erreurs = [-0.2, 0.2, -0.1, 0.1, -0.2]
        # MAE = 0.16
        # MSE = 0.028
        # mean_y = 3, ss_tot = 10, ss_res = 0.14
        # R² = 1 - 0.14/10 = 0.986
        expected_mae = (0.2 + 0.2 + 0.1 + 0.1 + 0.2) / 5
        expected_mse = (0.04 + 0.04 + 0.01 + 0.01 + 0.04) / 5
        expected_r2 = 1 - (0.14 / 10)

        assert result["mae"] == pytest.approx(expected_mae, abs=1e-6)
        assert result["mse"] == pytest.approx(expected_mse, abs=1e-6)
        assert result["rmse"] == pytest.approx(math.sqrt(expected_mse), abs=1e-6)
        assert result["r2"] == pytest.approx(expected_r2, abs=1e-6)
