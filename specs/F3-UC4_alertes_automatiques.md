# F3-UC4 : Génération d'Alertes Automatiques

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 8 mars 2026

---

## 1. Description

Ce module génère automatiquement des alertes lors de la détection d'événements critiques (drift de performance, drift de données, score faible) et les expose via l'API REST.

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `app/services/history.py` | Fonctions d'alertes (get_active_alerts, get_alerts_summary) |
| `app/main.py` | Endpoints `/alerts`, `/alerts/summary`, `/models/{id}/alerts` |
| `tests/test_alerts.py` | Tests unitaires (~15 tests) |

---

## 3. Types d'Alertes

| Sévérité | Condition | Description |
|----------|-----------|-------------|
| 🟢 `low` | Ratio < 1.10 | Pas de drift, performances normales |
| 🟠 `medium` | Ratio 1.10-1.25 | Drift détecté, dégradation légère |
| 🔴 `high` | Ratio ≥ 1.25 | Drift critique, dégradation forte |

---

## 4. API

### 4.1 Liste des alertes actives

```http
GET /alerts
GET /alerts?severity=high
GET /alerts?limit=10
```

**Réponse :**
```json
{
  "alerts": [
    {
      "model_id": "air_quality_v1",
      "severity": "high",
      "drift_detected": true,
      "ratio": 1.35,
      "timestamp": "2026-03-08T14:30:00Z",
      "message": "dégradation forte de performance"
    }
  ],
  "total": 1
}
```

### 4.2 Résumé des alertes

```http
GET /alerts/summary
```

**Réponse :**
```json
{
  "total_models": 5,
  "by_severity": {
    "low": 3,
    "medium": 1,
    "high": 1
  },
  "models_with_drift": 2
}
```

### 4.3 Historique des alertes d'un modèle

```http
GET /models/{model_id}/alerts
GET /models/{model_id}/alerts?limit=20
```

**Réponse :**
```json
{
  "model_id": "air_quality_v1",
  "alerts": [
    {
      "timestamp": "2026-03-08T14:30:00Z",
      "severity": "high",
      "drift_detected": true,
      "ratio": 1.35,
      "reason": "dégradation forte de performance"
    },
    {
      "timestamp": "2026-03-07T10:00:00Z",
      "severity": "low",
      "drift_detected": false,
      "ratio": 0.95,
      "reason": "performance stable"
    }
  ],
  "total": 2
}
```

---

## 5. Exemples d'utilisation

### Via cURL

```bash
# Toutes les alertes
curl http://localhost:8000/alerts

# Alertes critiques uniquement
curl "http://localhost:8000/alerts?severity=high"

# Résumé
curl http://localhost:8000/alerts/summary

# Historique d'un modèle
curl http://localhost:8000/models/air_quality_v1/alerts
```

### Python

```python
from app.services.history import get_active_alerts, get_alerts_summary

# Alertes actives (high seulement)
alerts = get_active_alerts(severity="high", limit=10)

# Résumé global
summary = get_alerts_summary()
print(f"Modèles avec drift: {summary['models_with_drift']}")
```

---

## 6. Intégration Dashboard

Les alertes sont affichées dans le dashboard :
- **Vue d'ensemble** : Nombre d'alertes par sévérité
- **Analyse détaillée** : Historique des alertes par modèle
- **Badge visuel** : 🟢 LOW / 🟠 MEDIUM / 🔴 HIGH

---

## 7. Génération Automatique

Les alertes sont générées automatiquement lors de :

1. **Évaluation manuelle** (`POST /evaluate`)
2. **Évaluation avec sauvegarde** (`POST /models/{id}/evaluate`)
3. **Évaluation planifiée** (Scheduler)

À chaque évaluation, le système :
1. Calcule les métriques (MAE, RMSE, R²)
2. Détecte le drift de performance
3. Stocke le résultat avec la sévérité
4. L'alerte est accessible via les endpoints

---

## 8. Tests

**Fichier** : `tests/test_alerts.py`

```bash
python -m pytest tests/test_alerts.py -v
```

### Couverture des tests

| Catégorie | Tests |
|-----------|-------|
| Liste des alertes | 3 tests |
| Filtrage par sévérité | 3 tests |
| Résumé des alertes | 2 tests |
| Historique par modèle | 3 tests |
| Cas limites | 2 tests |
| **Total** | **~13 tests** |

---

## 9. Structure des données

Les alertes sont stockées dans l'historique des évaluations :

```json
{
  "model_A": {
    "evaluations": [
      {
        "timestamp": "2026-03-08T14:30:00Z",
        "metrics": {"mae": 0.15, "rmse": 0.27},
        "score": 65,
        "performance_drift": {
          "severity": "high",
          "drift_detected": true,
          "ratio": 1.35,
          "reason": "dégradation forte de performance"
        }
      }
    ]
  }
}
```

L'API d'alertes extrait ces informations et les agrège pour une consultation facile.
