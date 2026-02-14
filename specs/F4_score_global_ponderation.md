# F4-UC1 & F4-UC2 : Score Global et Pondération

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 21 février 2026

---

## 1. Description

Ce module définit et calcule le **score global de fiabilité** (0-100) d'un modèle prédictif en combinant la performance pure et la stabilité (absence de drift).

---

## 2. Architecture

### Module
- **Fichier** : `app/services/scoring.py`
- **Fonction** : `compute_score(metrics, drift)`

### Endpoint API
```http
POST /evaluate
```

Le score est calculé automatiquement lors de chaque évaluation.

---

## 3. Algorithme de Scoring

### Formule Principale

```
Score = 0.7 × Score_Perf + 0.3 × (100 - Pénalité)
```

| Composant | Poids | Description |
|-----------|-------|-------------|
| **Score_Perf** | 70% | Performance basée sur le ratio RMSE/Baseline |
| **Stabilité** | 30% | Absence de drift (100 - pénalité) |

---

## 4. Calcul du Score Performance

### Avec Baseline (cas nominal)

```python
ratio = current_rmse / baseline_rmse
score_perf = max(0, min(100, 100 × (2.0 - ratio)))
```

| Ratio RMSE | Interprétation | Score_Perf |
|------------|----------------|------------|
| ≤ 1.0 | Aussi bon ou meilleur | 100 |
| 1.0 | Égal au baseline | 100 |
| 1.5 | 50% pire | 50 |
| ≥ 2.0 | 2× pire ou plus | 0 |

**Courbe du Score Performance :**
```
Score_Perf
    100 ┤━━━━━━━━┓
        │        ┃
     50 ┤        ┃━━━━━━━
        │              ┃
      0 ┤──────────────┻━━━━━
        0    1.0    1.5    2.0   Ratio
```

### Sans Baseline (fallback)

```python
score_perf = max(0, min(100, 100 × (1.0 - rmse)))
```

Utilisé quand `baseline_rmse` n'est pas fourni ou invalide.

---

## 5. Pénalités de Drift

### Tableau des Pénalités

| Sévérité | Pénalité | Description |
|----------|----------|-------------|
| `low` | 0 points | Performance stable |
| `medium` | 20 points | Dégradation modérée (+10% à +25%) |
| `high` | 40 points | Dégradation forte (≥+25%) |
| `unknown` | 10 points | Baseline non disponible |

### Impact sur le Score Final

```
Stabilité = 100 - Pénalité
```

| Sévérité | Stabilité | Contribution (×0.3) |
|----------|-----------|---------------------|
| `low` | 100 | +30 points |
| `medium` | 80 | +24 points |
| `high` | 60 | +18 points |
| `unknown` | 90 | +27 points |

---

## 6. Exemples de Calcul

### Exemple 1 : Modèle Excellent
```
RMSE actuel = 0.18
Baseline RMSE = 0.20
Sévérité = low

ratio = 0.18 / 0.20 = 0.9
score_perf = 100 × (2.0 - 0.9) = 110 → 100 (clamp)
pénalité = 0

Score = 0.7 × 100 + 0.3 × (100 - 0) = 70 + 30 = 100
```

### Exemple 2 : Modèle Dégradé
```
RMSE actuel = 0.30
Baseline RMSE = 0.20
Sévérité = high

ratio = 0.30 / 0.20 = 1.5
score_perf = 100 × (2.0 - 1.5) = 50
pénalité = 40

Score = 0.7 × 50 + 0.3 × (100 - 40) = 35 + 18 = 53
```

### Exemple 3 : Modèle Sans Baseline
```
RMSE actuel = 0.25
Baseline RMSE = None
Sévérité = unknown

score_perf = 100 × (1.0 - 0.25) = 75
pénalité = 10

Score = 0.7 × 75 + 0.3 × (100 - 10) = 52.5 + 27 = 79 → 79
```

---

## 7. Implémentation

```python
def compute_score(metrics: Dict, drift: Dict) -> int:
    rmse = float(metrics.get("rmse", 0.0))
    baseline = drift.get("baseline_rmse", None)

    # 1) Score performance (0..100)
    if baseline is not None and isinstance(baseline, (int, float)) and baseline > 0:
        ratio = rmse / baseline
        score_perf = int(max(0, min(100, 100 * (2.0 - ratio))))
    else:
        score_perf = int(max(0, min(100, 100 * (1.0 - rmse))))

    # 2) Pénalité drift
    severity = drift.get("severity", "unknown")
    if severity == "high":
        penalty = 40
    elif severity == "medium":
        penalty = 20
    elif severity == "low":
        penalty = 0
    else:
        penalty = 10

    # 3) Score final
    score = int(0.7 * score_perf + 0.3 * (100 - penalty))
    return max(0, min(100, score))
```

---

## 8. Interprétation des Scores

| Score | Catégorie | Action Recommandée |
|-------|-----------|-------------------|
| 90-100 | 🟢 Excellent | Aucune action requise |
| 75-89 | 🟡 Bon | Surveillance normale |
| 50-74 | 🟠 Moyen | Investigation recommandée |
| 25-49 | 🔴 Faible | Réentraînement conseillé |
| 0-24 | ⚫ Critique | Arrêt et révision du modèle |

---

## 9. API Usage

### Requête
```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "y_true": [1.0, 2.0, 3.0, 4.0, 5.0],
    "y_pred": [1.1, 2.2, 2.9, 4.1, 4.8],
    "baseline_rmse": 0.2
  }'
```

### Réponse
```json
{
  "metrics": {
    "mae": 0.14,
    "mse": 0.026,
    "rmse": 0.161,
    "r2": 0.987
  },
  "performance_drift": {
    "baseline_rmse": 0.2,
    "current_rmse": 0.161,
    "ratio": 0.805,
    "severity": "low",
    "drift_detected": false
  },
  "score": 100
}
```

---

## 10. Tests

**Fichier** : `tests/test_metrics.py` (inclut les tests de scoring)

Exécution :
```bash
python -m pytest tests/test_metrics.py -v -k "score"
```
