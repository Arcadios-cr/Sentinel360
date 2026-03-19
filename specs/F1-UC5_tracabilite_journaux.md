# F1-UC5 : Traçabilité via Versionnage et Journaux d'Exécution

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 21 février 2026

---

## 1. Description

Ce service assure la traçabilité complète des évaluations de modèles via un système de journalisation et de versionnage des résultats.

---

## 2. Architecture

### Module
- **Fichier** : `app/services/history.py`

### Stockage
- **Format** : Fichiers JSON par modèle
- **Emplacement** : `app/data/evals_{model_id}.json`
- **Nommage** : `evals_<model_id>.json` (caractères spéciaux normalisés)

---

## 3. Structure des Données

### Format d'une évaluation

```json
{
  "timestamp": "2026-02-21T14:30:00Z",
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
  "score": 92
}
```

### Métadonnées automatiques

| Champ | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | Horodatage UTC de l'évaluation |
| `metrics` | object | Métriques de performance calculées |
| `performance_drift` | object | Analyse de la dérive |
| `score` | int | Score global (0-100) |

---

## 4. API Endpoints

### Enregistrer une évaluation

```http
POST /models/{model_id}/evaluate
```

L'évaluation est automatiquement horodatée et ajoutée à l'historique du modèle.

### Consulter l'historique

```http
GET /models/{model_id}/evaluations?from_ts=2026-02-01T00:00:00Z&to_ts=2026-02-21T23:59:59Z&limit=200
```

| Paramètre | Type | Description |
|-----------|------|-------------|
| `from_ts` | string | Début de la période (ISO 8601) |
| `to_ts` | string | Fin de la période (ISO 8601) |
| `limit` | int | Nombre max de résultats (défaut: 200) |

### Lister tous les modèles

```http
GET /models
```

**Réponse :**
```json
{
  "total": 2,
  "models": [
    {
      "model_id": "model_A",
      "evaluation_count": 15,
      "last_score": 87,
      "last_evaluation": "2026-02-21T14:00:00Z"
    },
    {
      "model_id": "model_B",
      "evaluation_count": 10,
      "last_score": 82,
      "last_evaluation": "2026-02-20T18:30:00Z"
    }
  ]
}
```

---

## 5. Fonctions du Module

### `store_evaluation(model_id, evaluation)`

Enregistre une évaluation dans l'historique.

```python
from app.services.history import store_evaluation

result = store_evaluation("air_quality_v1", {
    "metrics": {"mae": 0.1, "rmse": 0.15, "r2": 0.95},
    "performance_drift": {"severity": "low", "drift_detected": False},
    "score": 88
})
# timestamp ajouté automatiquement si absent
```

### `list_evaluations(model_id, from_ts, to_ts, limit)`

Récupère l'historique filtré d'un modèle.

```python
from app.services.history import list_evaluations

history = list_evaluations(
    model_id="air_quality_v1",
    from_ts="2026-02-01T00:00:00Z",
    limit=50
)
# Retourne les 50 dernières évaluations depuis le 1er février
```

### `list_models()`

Liste tous les modèles avec leurs statistiques.

```python
from app.services.history import list_models

models = list_models()
# Triés par score décroissant
```

---

## 6. Persistance

### Organisation des fichiers

```
app/data/
├── evals_model_A.json       # Historique modèle A
├── evals_model_B.json       # Historique modèle B
├── evals_air_quality_v1.json
└── schedules.json           # Configuration planificateur
```

### Garanties

| Aspect | Implémentation |
|--------|----------------|
| **Atomicité** | Écriture complète du fichier JSON |
| **Horodatage** | UTC ISO 8601 automatique |
| **Normalisation** | IDs de modèles nettoyés (alphanumériques) |
| **Tri** | Chronologique croissant pour les requêtes |

---

## 7. Exemple d'historique

**Fichier** : `app/data/evals_model_A.json`

```json
[
  {
    "timestamp": "2026-02-20T10:00:00Z",
    "metrics": {"mae": 0.12, "mse": 0.02, "rmse": 0.14, "r2": 0.98},
    "performance_drift": {"severity": "low", "drift_detected": false},
    "score": 90
  },
  {
    "timestamp": "2026-02-20T11:00:00Z",
    "metrics": {"mae": 0.15, "mse": 0.03, "rmse": 0.17, "r2": 0.96},
    "performance_drift": {"severity": "medium", "drift_detected": true},
    "score": 82
  },
  {
    "timestamp": "2026-02-20T12:00:00Z",
    "metrics": {"mae": 0.11, "mse": 0.018, "rmse": 0.13, "r2": 0.985},
    "performance_drift": {"severity": "low", "drift_detected": false},
    "score": 92
  }
]
```

---

## 8. Tests

**Fichier** : `tests/test_compare_models.py`  
**Couverture** : Stockage, listage, filtrage temporel

Exécution :
```bash
python -m pytest tests/test_compare_models.py -v
```
