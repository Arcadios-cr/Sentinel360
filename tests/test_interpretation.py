"""
F2-UC5 : Tests pour l'interprétation des résultats.
F4-UC3 : Tests pour la catégorisation des risques.
F4-UC4 : Tests pour la justification du score.
F4-UC5 : Tests pour les recommandations de maintenance.

Ce module teste :
- Interprétation textuelle des métriques et du drift
- Catégorisation par niveau de risque
- Décomposition et justification du score
- Génération de recommandations
"""

import pytest
from app.services.interpretation import (
    interpret_evaluation,
    interpret_score,
    interpret_metric,
    interpret_drift,
    justify_score,
    categorize_risk,
    generate_recommendations,
    RISK_CATEGORIES,
)


# =============================================================================
# F4-UC3 : Tests de catégorisation du risque
# =============================================================================

class TestRiskCategorization:
    """Tests de la catégorisation par niveau de risque."""

    def test_excellent_score(self):
        """Score >= 90 → catégorie EXCELLENT."""
        risk = categorize_risk(95, "low")
        assert risk["category"] == "EXCELLENT"
        assert risk["label"] == "Excellent"
        assert risk["icon"] == "🟢"

    def test_bon_score(self):
        """Score 75-89 → catégorie BON."""
        risk = categorize_risk(82, "low")
        assert risk["category"] == "BON"
        assert risk["label"] == "Bon"

    def test_acceptable_score(self):
        """Score 60-74 → catégorie ACCEPTABLE."""
        risk = categorize_risk(65, "low")
        assert risk["category"] == "ACCEPTABLE"

    def test_degrade_score(self):
        """Score 40-59 → catégorie DEGRADE."""
        risk = categorize_risk(50, "low")
        assert risk["category"] == "DEGRADE"

    def test_critique_score(self):
        """Score < 40 → catégorie CRITIQUE."""
        risk = categorize_risk(25, "low")
        assert risk["category"] == "CRITIQUE"
        assert risk["icon"] == "🔴"

    def test_high_drift_downgrades_excellent(self):
        """Drift HIGH reclasse un EXCELLENT en ACCEPTABLE."""
        risk = categorize_risk(95, "high")
        assert risk["category"] == "ACCEPTABLE"
        assert risk["risk_note"] is not None

    def test_medium_drift_downgrades_excellent(self):
        """Drift MEDIUM reclasse un EXCELLENT en BON."""
        risk = categorize_risk(92, "medium")
        assert risk["category"] == "BON"

    def test_high_drift_downgrades_bon(self):
        """Drift HIGH reclasse un BON en ACCEPTABLE."""
        risk = categorize_risk(80, "high")
        assert risk["category"] == "ACCEPTABLE"

    def test_low_drift_no_downgrade(self):
        """Drift LOW ne change pas la catégorie."""
        risk = categorize_risk(82, "low")
        assert risk["category"] == "BON"

    def test_boundary_score_90(self):
        """Score exactement 90 → EXCELLENT."""
        risk = categorize_risk(90, "low")
        assert risk["category"] == "EXCELLENT"

    def test_boundary_score_75(self):
        """Score exactement 75 → BON."""
        risk = categorize_risk(75, "low")
        assert risk["category"] == "BON"


# =============================================================================
# F4-UC4 : Tests de justification du score
# =============================================================================

class TestScoreJustification:
    """Tests de la justification détaillée du score."""

    def test_justification_structure(self):
        """Vérifier la structure complète de la justification."""
        metrics = {"mae": 0.15, "mse": 0.025, "rmse": 0.158, "r2": 0.985}
        drift = {"severity": "low", "baseline_rmse": 0.20, "ratio": 0.79, "drift_detected": False}

        result = justify_score(92, metrics, drift, "model_A")

        assert "score_global" in result
        assert "decomposition" in result
        assert "penalites" in result
        assert "analyse" in result
        assert "explication_textuelle" in result
        assert result["score_global"] == 92

    def test_decomposition_has_all_metrics(self):
        """La décomposition contient toutes les métriques."""
        metrics = {"mae": 0.15, "mse": 0.025, "rmse": 0.158, "r2": 0.985}
        drift = {"severity": "low", "baseline_rmse": 0.20}

        result = justify_score(92, metrics, drift)

        metric_names = {c["metrique"] for c in result["decomposition"]}
        assert metric_names == {"mae", "mse", "rmse", "r2"}

    def test_decomposition_contributions_sum_up(self):
        """Les contributions des métriques sont cohérentes."""
        metrics = {"mae": 0.15, "mse": 0.025, "rmse": 0.158, "r2": 0.985}
        drift = {"severity": "low", "baseline_rmse": 0.20}

        result = justify_score(92, metrics, drift)

        total = sum(c["contribution"] for c in result["decomposition"])
        assert total == pytest.approx(result["score_avant_penalites"], abs=0.01)

    def test_weights_sum_to_one(self):
        """Les poids des métriques totalisent 1.0."""
        metrics = {"mae": 0.15, "mse": 0.025, "rmse": 0.158, "r2": 0.985}
        drift = {"severity": "low", "baseline_rmse": 0.20}

        result = justify_score(92, metrics, drift)

        total_weights = sum(c["poids"] for c in result["decomposition"])
        assert total_weights == pytest.approx(1.0, abs=0.01)

    def test_penalty_for_high_drift(self):
        """Drift HIGH entraîne des pénalités."""
        metrics = {"mae": 0.5, "mse": 0.3, "rmse": 0.55, "r2": 0.8}
        drift = {
            "severity": "high",
            "baseline_rmse": 0.20,
            "drift_detected": True,
            "reason": "dégradation forte",
        }

        result = justify_score(45, metrics, drift)

        assert len(result["penalites"]) > 0
        assert result["penalites"][0]["niveau"] == "HIGH"
        assert result["total_penalites"] < 0

    def test_no_penalty_for_low_drift(self):
        """Drift LOW → pas de pénalité."""
        metrics = {"mae": 0.1, "mse": 0.01, "rmse": 0.1, "r2": 0.99}
        drift = {"severity": "low", "baseline_rmse": 0.20, "drift_detected": False}

        result = justify_score(95, metrics, drift)

        assert len(result["penalites"]) == 0
        assert result["total_penalites"] == 0

    def test_analyse_identifies_best_and_worst(self):
        """L'analyse identifie le point fort et faible."""
        metrics = {"mae": 0.01, "mse": 0.001, "rmse": 0.03, "r2": 0.50}
        drift = {"severity": "low", "baseline_rmse": 0.20}

        result = justify_score(70, metrics, drift)

        assert "point_fort" in result["analyse"]
        assert "point_faible" in result["analyse"]
        # r2 = 0.50 devrait être le point faible
        assert result["analyse"]["point_faible"]["metrique"] == "r2"

    def test_text_explanation_includes_model_id(self):
        """L'explication textuelle mentionne le modèle."""
        metrics = {"mae": 0.15, "mse": 0.025, "rmse": 0.158, "r2": 0.985}
        drift = {"severity": "low", "baseline_rmse": 0.20}

        result = justify_score(92, metrics, drift, model_id="test_model")

        assert "test_model" in result["explication_textuelle"]


# =============================================================================
# F2-UC5 : Tests d'interprétation des résultats
# =============================================================================

class TestInterpretation:
    """Tests de l'interprétation textuelle."""

    def test_interpret_score_excellent(self):
        """Score >= 90 → interprétation Excellent."""
        text = interpret_score(95)
        assert "Excellent" in text or "optimale" in text

    def test_interpret_score_critique(self):
        """Score < 50 → interprétation Critique."""
        text = interpret_score(30)
        assert "Critique" in text or "urgente" in text

    def test_interpret_metric_mae_low(self):
        """MAE faible → bonne interprétation."""
        text = interpret_metric("mae", 0.05)
        assert "faible" in text.lower() or "excellente" in text.lower()

    def test_interpret_metric_r2_high(self):
        """R² élevé → bonne interprétation."""
        text = interpret_metric("r2", 0.97)
        assert "excellent" in text.lower()

    def test_interpret_metric_r2_low(self):
        """R² faible → mauvaise interprétation."""
        text = interpret_metric("r2", 0.50)
        assert "faible" in text.lower()

    def test_interpret_drift_stable(self):
        """Pas de drift → stable."""
        drift = {"severity": "low", "drift_detected": False, "ratio": 0.9}
        text = interpret_drift(drift)
        assert "stable" in text.lower()

    def test_interpret_drift_high(self):
        """Drift HIGH → dégradation."""
        drift = {"severity": "high", "drift_detected": True, "ratio": 1.50}
        text = interpret_drift(drift)
        assert "forte" in text.lower() or "significative" in text.lower()

    def test_full_interpretation_structure(self):
        """Interprétation complète contient toutes les sections."""
        metrics = {"mae": 0.15, "mse": 0.025, "rmse": 0.158, "r2": 0.985}
        drift = {"severity": "low", "baseline_rmse": 0.20, "ratio": 0.79, "drift_detected": False}

        result = interpret_evaluation(metrics, drift, 92, "model_A")

        assert "summary" in result
        assert "details" in result
        assert "metrics_analysis" in result
        assert "drift_explanation" in result
        assert "recommendations" in result

    def test_interpretation_has_metric_analysis(self):
        """L'interprétation contient l'analyse de chaque métrique."""
        metrics = {"mae": 0.15, "mse": 0.025, "rmse": 0.158, "r2": 0.985}
        drift = {"severity": "low", "baseline_rmse": 0.20, "ratio": 0.79, "drift_detected": False}

        result = interpret_evaluation(metrics, drift, 92)

        assert "mae" in result["metrics_analysis"]
        assert "rmse" in result["metrics_analysis"]
        assert "r2" in result["metrics_analysis"]


# =============================================================================
# F4-UC5 : Tests des recommandations de maintenance
# =============================================================================

class TestMaintenanceRecommendations:
    """Tests des recommandations automatiques."""

    def test_recommendations_for_critical_score(self):
        """Score critique → recommandation urgente."""
        metrics = {"mae": 2.0, "mse": 4.0, "rmse": 2.0, "r2": 0.3}
        drift = {"severity": "high", "drift_detected": True}

        recs = generate_recommendations(25, metrics, drift)

        assert any("URGENT" in r.upper() for r in recs)

    def test_recommendations_for_high_drift(self):
        """Drift HIGH → recommandation de réentraînement."""
        metrics = {"mae": 0.5, "mse": 0.3, "rmse": 0.55, "r2": 0.8}
        drift = {"severity": "high", "drift_detected": True}

        recs = generate_recommendations(50, metrics, drift)

        assert any("réentraînement" in r.lower() or "reentraînement" in r.lower() for r in recs)

    def test_recommendations_for_low_r2(self):
        """R² faible → recommandation spécifique."""
        metrics = {"mae": 0.3, "mse": 0.1, "rmse": 0.32, "r2": 0.60}
        drift = {"severity": "low", "drift_detected": False}

        recs = generate_recommendations(65, metrics, drift)

        assert any("R²" in r for r in recs)

    def test_recommendations_for_good_model(self):
        """Modèle performant → pas d'action corrective."""
        metrics = {"mae": 0.05, "mse": 0.003, "rmse": 0.05, "r2": 0.99}
        drift = {"severity": "low", "drift_detected": False}

        recs = generate_recommendations(95, metrics, drift)

        assert any("aucune action" in r.lower() or "✅" in r for r in recs)

    def test_recommendations_for_declining_trend(self):
        """Tendance à la baisse → recommandation d'investigation."""
        metrics = {"mae": 0.3, "mse": 0.1, "rmse": 0.32, "r2": 0.85}
        drift = {"severity": "medium", "drift_detected": True}
        history = [92, 88, 85, 80, 75]

        recs = generate_recommendations(75, metrics, drift, history_scores=history)

        assert any("baisse" in r.lower() or "tendance" in r.lower() for r in recs)

    def test_recommendations_outlier_pattern(self):
        """RMSE >> MAE → détection de pattern d'outliers."""
        metrics = {"mae": 0.1, "mse": 1.0, "rmse": 1.0, "r2": 0.85}
        drift = {"severity": "low", "drift_detected": False}

        recs = generate_recommendations(80, metrics, drift)

        assert any("outlier" in r.lower() or "écart" in r.lower() for r in recs)
