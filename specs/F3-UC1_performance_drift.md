# F3-UC1 : Détection des Baisses de Performance (Performance Drift)

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 8 mars 2026

---

## 1. Description

Cette feature détecte automatiquement toute dégradation anormale des performances d'un modèle prédictif en comparant le RMSE actuel au RMSE de référence (baseline).

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `app/services/drift.py` | Algorithme de détection du performance drift |
| `app/main.py` | Intégration dans les endpoints `/evaluate` |
| `tests/test_drift.py` | Tests unitaires (~25 tests) |

---

## 3. Algorithme

### 3.1 Calcul du Ratio

```
Ratio = RMSE_actuel / RMSE_baseline
```

### 3.2 Seuils de Sévérité

| Seuil | Ratio | Sévérité | Drift Détecté |
|-------|-------|----------|---------------|
| Normal | < 1.10 | `low` | ❌ Non |
| Warning | ≥ 1.10 et < 1.25 | `medium` | ✅ Oui |
| Alert | ≥ 1.25 | `high` | ✅ Oui |
| Unknown | Baseline invalide | `unknown` | ❌ Non |

---

## 4. API

### Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `current_rmse` | float | - | RMSE des prédictions actuelles |
| `baseline_rmse` | float | None | RMSE de référence |
| `warn_ratio` | float | 1.10 | Seuil pour sévérité medium |
| `alert_ratio` | float | 1.25 | Seuil pour sévérité high |

### Structure de Sortie

```json
{
  "baseline_rmse": 0.20,
  "current_rmse": 0.26,
  "ratio": 1.30,
  "delta": 0.06,
  "severity": "high",
  "drift_detected": true,
  "reason": "dégradation forte de performance"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `baseline_rmse` | float | RMSE de référence |
| `current_rmse` | float | RMSE actuel |
| `ratio` | float | Rapport actuel/baseline |
| `delta` | float | Différence absolue |
| `severity` | string | Niveau: low/medium/high/unknown |
| `drift_detected` | bool | Drift significatif détecté |
| `reason` | string | Explication textuelle |

---

## 5. Exemples d'utilisation

### Python

```python
from app.services.drift import detect_performance_drift

# Cas 1: Pas de drift
result = detect_performance_drift(current_rmse=0.18, baseline_rmse=0.20)
# result["severity"] = "low", result["drift_detected"] = False

# Cas 2: Drift medium
result = detect_performance_drift(current_rmse=0.23, baseline_rmse=0.20)
# result["severity"] = "medium", result["drift_detected"] = True

# Cas 3: Drift high
result = detect_performance_drift(current_rmse=0.30, baseline_rmse=0.20)
# result["severity"] = "high", result["drift_detected"] = True
```

### Via API

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "y_true": [1.0, 2.0, 3.0],
    "y_pred": [1.1, 2.2, 3.3],
    "baseline_rmse": 0.10
  }'
```

La réponse inclut automatiquement `performance_drift`.

---

## 6. Diagramme de Flux

```
┌─────────────────┐
│  Évaluation     │
│  (y_true/pred)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Calcul RMSE     │
│ actuel          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Baseline        │────►│ Ratio =         │
│ disponible?     │ Oui │ RMSE/Baseline   │
└────────┬────────┘     └────────┬────────┘
         │ Non                   │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ severity =      │     │ Évaluation      │
│ "unknown"       │     │ des seuils      │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
              ┌─────────┐  ┌─────────┐  ┌─────────┐
              │  LOW    │  │ MEDIUM  │  │  HIGH   │
              │ <1.10   │  │ 1.10-   │  │ >=1.25  │
              │         │  │ 1.25    │  │         │
              └─────────┘  └─────────┘  └─────────┘
```

---

## 7. Tests

**Fichier** : `tests/test_drift.py`

```bash
python -m pytest tests/test_drift.py -v
```

### Couverture des tests

| Catégorie | Tests |
|-----------|-------|
| Pas de drift (low) | 3 tests |
| Drift medium | 3 tests |
| Drift high | 3 tests |
| Cas limites | 5 tests |
| Seuils personnalisés | 3 tests |
| Structure de sortie | 2 tests |
| Cohérence | 2 tests |
| **Total** | **~21 tests** |

---

## 8. Intégration

Le performance drift est automatiquement calculé lors de :
- `POST /evaluate` → champ `performance_drift`
- `POST /models/{id}/evaluate` → stocké dans l'historique
- Dashboard → affiché dans les résultats d'évaluation
