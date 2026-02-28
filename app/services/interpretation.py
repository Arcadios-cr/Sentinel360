"""
F2-UC5 : Interprétation des résultats.
F4-UC3 : Catégorisation des modèles selon leur niveau de risque.
F4-UC4 : Justification du score obtenu.
F4-UC5 : Proposition d'actions de maintenance.

Ce module fournit :
- Interprétation textuelle des métriques et du drift
- Décomposition et justification du score global
- Catégorisation par niveau de risque
- Recommandations de maintenance automatiques
"""

from typing import Any, Dict, List, Optional


# =============================================================================
# F4-UC3 : CATÉGORISATION DU RISQUE
# =============================================================================

RISK_CATEGORIES = {
    "EXCELLENT": {"min_score": 90, "max_score": 100, "label": "Excellent", "color": "#10b981", "icon": "🟢"},
    "BON":       {"min_score": 75, "max_score": 89,  "label": "Bon",       "color": "#3b82f6", "icon": "🔵"},
    "ACCEPTABLE":{"min_score": 60, "max_score": 74,  "label": "Acceptable","color": "#f59e0b", "icon": "🟡"},
    "DEGRADE":   {"min_score": 40, "max_score": 59,  "label": "Dégradé",   "color": "#f97316", "icon": "🟠"},
    "CRITIQUE":  {"min_score": 0,  "max_score": 39,  "label": "Critique",  "color": "#ef4444", "icon": "🔴"},
}


def categorize_risk(score: float, drift_severity: str = "low") -> Dict[str, Any]:
    """
    Catégorise un modèle selon son niveau de risque (F4-UC3).

    Args:
        score: Score global du modèle (0-100)
        drift_severity: Sévérité du drift ("low", "medium", "high")

    Returns:
        Catégorie de risque avec label, niveau et couleur
    """
    # Déterminer la catégorie par score
    category = "CRITIQUE"
    for cat_name, cat_info in RISK_CATEGORIES.items():
        if cat_info["min_score"] <= score <= cat_info["max_score"]:
            category = cat_name
            break

    cat_info = RISK_CATEGORIES[category]

    # Ajustement en fonction du drift
    risk_level = category
    if drift_severity == "high" and category in ("EXCELLENT", "BON"):
        risk_level = "ACCEPTABLE"
        risk_note = "Score bon mais drift élevé détecté — risque reclassé"
    elif drift_severity == "medium" and category == "EXCELLENT":
        risk_level = "BON"
        risk_note = "Score excellent mais drift modéré — surveillance requise"
    else:
        risk_note = None

    effective_cat = RISK_CATEGORIES.get(risk_level, cat_info)

    return {
        "category": risk_level,
        "label": effective_cat["label"],
        "icon": effective_cat["icon"],
        "color": effective_cat["color"],
        "score": score,
        "drift_severity": drift_severity,
        "risk_note": risk_note,
    }


# =============================================================================
# F4-UC4 : JUSTIFICATION DU SCORE
# =============================================================================

def _score_for_metric(name: str, value: float, baseline_rmse: Optional[float] = None) -> Dict[str, Any]:
    """Calcule un score individuel par métrique et donne une évaluation textuelle."""
    if name == "mae":
        if value < 0.1:
            s, label = 95, "EXCELLENT"
        elif value < 0.3:
            s, label = 80, "BON"
        elif value < 0.7:
            s, label = 65, "ACCEPTABLE"
        elif value < 1.5:
            s, label = 45, "DEGRADE"
        else:
            s, label = 20, "CRITIQUE"
    elif name == "rmse":
        if baseline_rmse and baseline_rmse > 0:
            ratio = value / baseline_rmse
            if ratio <= 0.8:
                s, label = 98, "EXCELLENT"
            elif ratio <= 1.0:
                s, label = 90, "EXCELLENT"
            elif ratio <= 1.1:
                s, label = 75, "BON"
            elif ratio <= 1.25:
                s, label = 55, "DEGRADE"
            else:
                s, label = max(0, int(100 * (2.0 - ratio))), "CRITIQUE"
        else:
            if value < 0.15:
                s, label = 95, "EXCELLENT"
            elif value < 0.3:
                s, label = 80, "BON"
            elif value < 0.8:
                s, label = 60, "ACCEPTABLE"
            else:
                s, label = 30, "DEGRADE"
    elif name == "r2":
        if value >= 0.95:
            s, label = 97, "EXCELLENT"
        elif value >= 0.85:
            s, label = 82, "BON"
        elif value >= 0.70:
            s, label = 65, "ACCEPTABLE"
        elif value >= 0.50:
            s, label = 45, "DEGRADE"
        else:
            s, label = 20, "CRITIQUE"
    elif name == "mse":
        if value < 0.01:
            s, label = 95, "EXCELLENT"
        elif value < 0.05:
            s, label = 80, "BON"
        elif value < 0.2:
            s, label = 60, "ACCEPTABLE"
        else:
            s, label = 30, "DEGRADE"
    else:
        s, label = 50, "INCONNU"

    return {"score": max(0, min(100, s)), "evaluation": label}


# Poids par défaut des métriques pour le score décomposé
DEFAULT_WEIGHTS = {
    "rmse": 0.35,
    "mae": 0.25,
    "r2": 0.25,
    "mse": 0.15,
}


def justify_score(
    score: int,
    metrics: Dict[str, float],
    drift: Dict[str, Any],
    model_id: str = "",
) -> Dict[str, Any]:
    """
    Génère la justification détaillée du score (F4-UC4).

    Args:
        score: Score global calculé
        metrics: Métriques (mae, mse, rmse, r2)
        drift: Informations de drift
        model_id: Identifiant du modèle (optionnel)

    Returns:
        Justification complète avec décomposition
    """
    baseline_rmse = drift.get("baseline_rmse")
    severity = drift.get("severity", "unknown")

    # Décomposition par métrique
    composants = []
    for metric_name, weight in DEFAULT_WEIGHTS.items():
        value = metrics.get(metric_name)
        if value is None:
            continue
        metric_score_info = _score_for_metric(metric_name, value, baseline_rmse)
        contribution = round(weight * metric_score_info["score"], 2)
        composants.append({
            "metrique": metric_name,
            "valeur": round(value, 6),
            "poids": weight,
            "score_metrique": metric_score_info["score"],
            "contribution": contribution,
            "evaluation": metric_score_info["evaluation"],
        })

    # Score avant pénalités
    score_avant_penalites = round(sum(c["contribution"] for c in composants), 2)

    # Pénalités drift
    penalites = []
    penalty_map = {"high": 40, "medium": 20, "low": 0, "unknown": 10}
    drift_penalty = penalty_map.get(severity, 10)

    if drift_penalty > 0:
        penalty_impact = round(0.3 * drift_penalty, 2)
        penalites.append({
            "type": "performance_drift",
            "niveau": severity.upper(),
            "impact": -penalty_impact,
            "raison": drift.get("reason", f"Drift de sévérité {severity}"),
        })
    else:
        penalty_impact = 0

    # Points forts / faibles
    if composants:
        best = max(composants, key=lambda c: c["score_metrique"])
        worst = min(composants, key=lambda c: c["score_metrique"])
    else:
        best = worst = None

    analyse = {}
    if best:
        analyse["point_fort"] = {"metrique": best["metrique"], "score": best["score_metrique"]}
    if worst:
        analyse["point_faible"] = {"metrique": worst["metrique"], "score": worst["score_metrique"]}

    # Explication textuelle
    text = _generate_text_explanation(score, composants, penalites, analyse, model_id)

    return {
        "score_global": score,
        "decomposition": composants,
        "penalites": penalites,
        "score_avant_penalites": score_avant_penalites,
        "total_penalites": round(-penalty_impact, 2),
        "analyse": analyse,
        "explication_textuelle": text,
    }


def _generate_text_explanation(
    score: int,
    composants: list,
    penalites: list,
    analyse: dict,
    model_id: str,
) -> str:
    """Génère une explication textuelle complète."""
    model_label = f'"{model_id}"' if model_id else "évalué"
    lines = [f"Le modèle {model_label} obtient un score de {score}/100."]

    # Décomposition
    if composants:
        lines.append("\nDécomposition :")
        for c in composants:
            pct = int(c["poids"] * 100)
            lines.append(
                f"  • {c['metrique'].upper()} ({pct}%) : {c['score_metrique']}/100 "
                f"→ contribue {c['contribution']} points ({c['evaluation']})"
            )

    # Pénalités
    if penalites:
        lines.append("\nPénalités appliquées :")
        for p in penalites:
            lines.append(f"  • {p['type']} ({p['niveau']}) : {p['impact']} points — {p['raison']}")

    # Analyse
    pf = analyse.get("point_fort")
    pw = analyse.get("point_faible")
    if pf and pw and pf["metrique"] != pw["metrique"]:
        lines.append(f"\nPoint fort : {pf['metrique'].upper()} (score {pf['score']})")
        lines.append(f"Point faible : {pw['metrique'].upper()} (score {pw['score']})")

    return "\n".join(lines)


# =============================================================================
# F2-UC5 : INTERPRÉTATION DES RÉSULTATS
# =============================================================================

def interpret_score(score: float) -> str:
    """Interprétation textuelle du score."""
    if score >= 90:
        return "Excellent — Le modèle fonctionne de manière optimale."
    elif score >= 80:
        return "Bon — Performances satisfaisantes, surveillance recommandée."
    elif score >= 70:
        return "Acceptable — Quelques points d'attention à surveiller."
    elif score >= 50:
        return "Dégradé — Actions correctives recommandées."
    else:
        return "Critique — Intervention urgente nécessaire."


def interpret_metric(name: str, value: float) -> str:
    """Interprétation textuelle d'une métrique."""
    if name == "mae":
        if value < 0.1:
            return f"L'erreur absolue moyenne ({value:.4f}) est très faible — excellente précision."
        elif value < 0.3:
            return f"L'erreur absolue moyenne ({value:.4f}) est acceptable."
        else:
            return f"L'erreur absolue moyenne ({value:.4f}) est élevée — les prédictions s'écartent significativement."
    elif name == "rmse":
        if value < 0.15:
            return f"Le RMSE ({value:.4f}) est très faible — modèle très précis."
        elif value < 0.5:
            return f"Le RMSE ({value:.4f}) est correct."
        else:
            return f"Le RMSE ({value:.4f}) est élevé — erreurs importantes sur certaines prédictions."
    elif name == "r2":
        pct = value * 100
        if value >= 0.95:
            return f"Le R² ({value:.4f}) est excellent — le modèle explique {pct:.1f}% de la variance."
        elif value >= 0.85:
            return f"Le R² ({value:.4f}) est bon — {pct:.1f}% de la variance expliquée."
        elif value >= 0.70:
            return f"Le R² ({value:.4f}) est acceptable — {pct:.1f}% de la variance expliquée."
        else:
            return f"Le R² ({value:.4f}) est faible — le modèle n'explique que {pct:.1f}% de la variance."
    elif name == "mse":
        if value < 0.01:
            return f"Le MSE ({value:.6f}) est très faible."
        elif value < 0.1:
            return f"Le MSE ({value:.6f}) est acceptable."
        else:
            return f"Le MSE ({value:.6f}) est élevé."
    return f"{name} = {value}"


def interpret_drift(drift: Dict[str, Any]) -> str:
    """Interprétation textuelle du drift."""
    severity = drift.get("severity", "unknown")
    ratio = drift.get("ratio")
    detected = drift.get("drift_detected", False)

    if not detected:
        if ratio and ratio < 1.0:
            return "Le modèle est stable, voire en amélioration par rapport au baseline."
        return "Aucune dérive de performance détectée — le modèle est stable."

    if severity == "high":
        ratio_str = f"{ratio:.2f}x" if ratio else ""
        return (
            f"Dérive forte détectée ({ratio_str} le baseline). "
            "Le modèle montre une dégradation significative des performances."
        )
    elif severity == "medium":
        ratio_str = f"{ratio:.2f}x" if ratio else ""
        return (
            f"Dérive modérée détectée ({ratio_str} le baseline). "
            "Surveillance renforcée recommandée."
        )
    return "Dérive de sévérité inconnue."


def interpret_evaluation(
    metrics: Dict[str, float],
    drift: Dict[str, Any],
    score: int,
    model_id: str = "",
) -> Dict[str, Any]:
    """
    Génère une interprétation complète d'une évaluation (F2-UC5).

    Args:
        metrics: Métriques calculées
        drift: Résultat du drift
        score: Score global
        model_id: Identifiant du modèle

    Returns:
        Interprétation structurée
    """
    severity = drift.get("severity", "unknown")

    # Résumé
    summary = interpret_score(score)

    # Détails
    details = []
    details.append(f"Score global : {score}/100")
    if drift.get("ratio"):
        details.append(f"Ratio RMSE/baseline : {drift['ratio']:.2f}x")
    if severity in ("medium", "high"):
        details.append(f"Drift de sévérité {severity.upper()} détecté")

    # Analyse par métrique
    metrics_analysis = {}
    for name in ("mae", "mse", "rmse", "r2"):
        val = metrics.get(name)
        if val is not None:
            metrics_analysis[name] = interpret_metric(name, val)

    # Interprétation du drift
    drift_explanation = interpret_drift(drift)

    # Recommandations
    recommendations = generate_recommendations(score, metrics, drift)

    return {
        "summary": summary,
        "details": details,
        "metrics_analysis": metrics_analysis,
        "drift_explanation": drift_explanation,
        "severity_explanation": (
            f"{severity.upper()} : ratio RMSE/baseline de {drift.get('ratio', 0):.2f} "
            f"(seuil warn=1.10, alert=1.25)"
            if drift.get("ratio")
            else f"Sévérité : {severity}"
        ),
        "recommendations": recommendations,
    }


# =============================================================================
# F4-UC5 : RECOMMANDATIONS DE MAINTENANCE
# =============================================================================

def generate_recommendations(
    score: int,
    metrics: Dict[str, float],
    drift: Dict[str, Any],
    history_scores: Optional[List[float]] = None,
) -> List[str]:
    """
    Génère des recommandations de maintenance automatiques (F4-UC5).

    Args:
        score: Score global
        metrics: Métriques calculées
        drift: Résultat du drift
        history_scores: Historique des scores (optionnel)

    Returns:
        Liste de recommandations textuelles
    """
    recommendations = []
    severity = drift.get("severity", "unknown")

    # Recommandations basées sur le score
    if score < 40:
        recommendations.append(
            "🔴 ACTION URGENTE : Auditer le modèle et les données d'entrée immédiatement."
        )
        recommendations.append(
            "Envisager un remplacement ou un réentraînement complet du modèle."
        )
    elif score < 60:
        recommendations.append(
            "🟠 Planifier un réentraînement du modèle dans les prochains jours."
        )
        recommendations.append(
            "Vérifier la qualité et la représentativité des données d'entrée récentes."
        )
    elif score < 75:
        recommendations.append(
            "🟡 Surveiller l'évolution du score sur les prochaines évaluations."
        )

    # Recommandations basées sur le drift
    if severity == "high":
        recommendations.append(
            "Réentraînement recommandé — la performance s'est fortement dégradée."
        )
        recommendations.append(
            "Comparer les données actuelles avec le dataset de référence (data drift)."
        )
    elif severity == "medium":
        recommendations.append(
            "Surveillance renforcée — analyser les données pour identifier la cause du drift."
        )

    # Recommandations basées sur les métriques
    r2 = metrics.get("r2", 1.0)
    if r2 < 0.70:
        recommendations.append(
            "Le R² est faible — vérifier la représentativité des données d'entraînement."
        )
    elif r2 < 0.85:
        recommendations.append(
            "Le R² est en dessous des attentes — envisager l'ajout de features."
        )

    rmse = metrics.get("rmse", 0)
    mae = metrics.get("mae", 0)
    if rmse > 0 and mae > 0 and rmse > 2 * mae:
        recommendations.append(
            "Écart important entre RMSE et MAE — le modèle commet quelques erreurs très grandes (outliers)."
        )

    # Recommandations basées sur l'historique
    if history_scores and len(history_scores) >= 3:
        recent = history_scores[-3:]
        if all(recent[i] < recent[i - 1] for i in range(1, len(recent))):
            recommendations.append(
                "Tendance à la baisse détectée sur les dernières évaluations — investiguer rapidement."
            )

    # Si tout va bien
    if not recommendations:
        recommendations.append(
            "✅ Aucune action corrective nécessaire — continuer la surveillance régulière."
        )

    return recommendations
