# F4-UC3 : Catégorisation des Modèles par Niveau de Risque

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 12 mars 2026

---

## 1. Description

Classe automatiquement chaque modèle dans une **catégorie de risque** (EXCELLENT → CRITIQUE) en fonction de son score global et de la sévérité du drift, avec un système de **rétrogradation** si le drift est élevé malgré un bon score.

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `app/services/interpretation.py` | Fonction `categorize_risk()` + constantes `RISK_CATEGORIES` |
| `app/main.py` | Endpoints `GET /models/{id}/risk` et `GET /risk/overview` |
| `dashboard/app.py` | Onglet « Vue des Risques » dans la page Interprétation |
| `tests/test_interpretation.py` | 11 tests de catégorisation |

---

## 3. Catégories de Risque

| Catégorie | Score | Icône | Couleur | Description |
|-----------|-------|-------|---------|-------------|
| **EXCELLENT** | 90-100 | 🟢 | `#10b981` | Modèle optimal, aucune action requise |
| **BON** | 75-89 | 🔵 | `#3b82f6` | Performances satisfaisantes |
| **ACCEPTABLE** | 60-74 | 🟡 | `#f59e0b` | Points d'attention à surveiller |
| **DÉGRADÉ** | 40-59 | 🟠 | `#f97316` | Actions correctives recommandées |
| **CRITIQUE** | 0-39 | 🔴 | `#ef4444` | Intervention urgente nécessaire |

---

## 4. Rétrogradation par Drift

Le drift peut **rétrograder** la catégorie même si le score est bon :

| Score initial | Drift HIGH | Drift MEDIUM |
|---------------|------------|--------------|
| EXCELLENT | → ACCEPTABLE | → BON |
| BON | → ACCEPTABLE | (pas de changement) |
| ACCEPTABLE | (pas de changement) | (pas de changement) |
| DÉGRADÉ | (pas de changement) | (pas de changement) |
| CRITIQUE | (pas de changement) | (pas de changement) |

**Exemple :** Un modèle avec un score de 92 (EXCELLENT) mais un drift HIGH sera reclassé en ACCEPTABLE avec la note : « Score bon mais drift élevé détecté — risque reclassé ».

---

## 5. Structure de Sortie

```json
{
  "category": "BON",
  "label": "Bon",
  "icon": "🔵",
  "color": "#3b82f6",
  "score": 82,
  "drift_severity": "low",
  "risk_note": null
}
```

Avec rétrogradation :

```json
{
  "category": "ACCEPTABLE",
  "label": "Acceptable",
  "icon": "🟡",
  "color": "#f59e0b",
  "score": 92,
  "drift_severity": "high",
  "risk_note": "Score bon mais drift élevé détecté — risque reclassé"
}
```

---

## 6. API Endpoints

### GET `/models/{model_id}/risk`

Retourne la catégorie de risque du modèle.

```bash
curl http://localhost:8000/models/climatrack/risk
```

### GET `/risk/overview`

Vue d'ensemble de tous les modèles par catégorie.

```bash
curl http://localhost:8000/risk/overview
```

**Response 200 :**
```json
{
  "total_models": 5,
  "summary": {"EXCELLENT": 2, "BON": 1, "ACCEPTABLE": 1, "DEGRADE": 1, "CRITIQUE": 0},
  "by_category": {
    "EXCELLENT": [{"model_id": "model_A", "score": 95, "category": "EXCELLENT"}],
    "BON": [{"model_id": "model_B", "score": 80, "category": "BON"}]
  }
}
```

---

## 7. Dashboard

### Onglet « Vue des Risques »

- **Diagramme circulaire** (Plotly pie chart) : répartition des modèles par catégorie
- **KPIs par catégorie** : nombre de modèles et couleur associée
- **Détail par modèle** : score, catégorie, note de risque

---

## 8. Tests

**Fichier** : `tests/test_interpretation.py` — Classe `TestRiskCategorization` — **11 tests**

| Test | Description |
|------|-------------|
| `test_excellent_score` | Score 95 → EXCELLENT |
| `test_bon_score` | Score 82 → BON |
| `test_acceptable_score` | Score 65 → ACCEPTABLE |
| `test_degrade_score` | Score 45 → DEGRADE |
| `test_critique_score` | Score 30 → CRITIQUE |
| `test_high_drift_downgrades_excellent` | 95 + HIGH → ACCEPTABLE |
| `test_medium_drift_downgrades_excellent` | 95 + MEDIUM → BON |
| `test_high_drift_downgrades_bon` | 82 + HIGH → ACCEPTABLE |
| `test_low_drift_no_downgrade` | Pas de rétrogradation si LOW |
| `test_boundary_score_90` | Score 90 → EXCELLENT |
| `test_boundary_score_75` | Score 75 → BON |

```bash
python -m pytest tests/test_interpretation.py::TestRiskCategorization -v
```
