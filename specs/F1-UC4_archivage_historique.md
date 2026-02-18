# F1-UC4 : Archivage de l'Historique des Évaluations

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 8 mars 2026

---

## 1. Description

Ce module archive de manière persistante l'historique des évaluations de chaque modèle IA. Il permet l'analyse rétrospective, la comparaison temporelle et l'audit complet des performances.

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `app/services/history.py` | Fonctions de stockage et récupération |
| `app/data/evals_*.json` | Fichiers d'archive par modèle |
| `app/main.py` | Endpoints API |

### Structure de stockage

```
app/data/
├── evals_model_A.json              # Historique modèle A
├── evals_model_B.json              # Historique modèle B
├── evals_climatrack_humidex_v1.json # Historique ClimaTrack
└── schedules.json                  # Planifications
```

---

## 3. Format des Données

### 3.1 Structure d'une Évaluation

```json
{
  "timestamp": "2026-03-08T14:30:00Z",
  "metrics": {
    "mae": 0.15,
    "mse": 0.025,
    "rmse": 0.158,
    "r2": 0.985
  },
  "score": 92,
  "performance_drift": {
    "baseline_rmse": 0.20,
    "current_rmse": 0.158,
    "ratio": 0.79,
    "severity": "low",
    "drift_detected": false,
    "reason": "performance stable"
  }
}
```

### 3.2 Fichier Complet

```json
[
  {"timestamp": "2026-03-01T10:00:00Z", "score": 95, ...},
  {"timestamp": "2026-03-02T10:00:00Z", "score": 93, ...},
  {"timestamp": "2026-03-03T10:00:00Z", "score": 91, ...}
]
```

---

## 4. API

### 4.1 Stocker une évaluation

```http
POST /models/{model_id}/evaluate
Content-Type: application/json

{
  "y_true": [1.0, 2.0, 3.0],
  "y_pred": [1.1, 2.1, 3.1],
  "baseline_rmse": 0.2
}
```

**Réponse :**
```json
{
  "message": "Évaluation enregistrée",
  "model_id": "model_A",
  "result": {
    "timestamp": "2026-03-08T14:30:00Z",
    "score": 92,
    "metrics": {...},
    "performance_drift": {...}
  }
}
```

### 4.2 Consulter l'historique

```http
GET /models/{model_id}/history
```

**Paramètres optionnels :**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `from_ts` | ISO 8601 | Date de début |
| `to_ts` | ISO 8601 | Date de fin |
| `limit` | int | Nombre max de résultats (défaut: 200) |

**Exemple :**
```http
GET /models/model_A/history?from_ts=2026-03-01T00:00:00Z&limit=50
```

**Réponse :**
```json
{
  "model_id": "model_A",
  "evaluations": [
    {"timestamp": "2026-03-01T10:00:00Z", "score": 95, ...},
    {"timestamp": "2026-03-02T10:00:00Z", "score": 93, ...}
  ],
  "count": 2
}
```

### 4.3 Lister tous les modèles

```http
GET /models
```

**Réponse :**
```json
{
  "models": [
    {
      "model_id": "model_A",
      "evaluation_count": 42,
      "last_score": 92,
      "last_evaluation": "2026-03-08T14:30:00Z"
    },
    {
      "model_id": "model_B",
      "evaluation_count": 38,
      "last_score": 88,
      "last_evaluation": "2026-03-08T12:00:00Z"
    }
  ],
  "count": 2
}
```

---

## 5. Fonctions Python

### 5.1 store_evaluation

```python
from app.services.history import store_evaluation

evaluation = {
    "metrics": {"mae": 0.15, "rmse": 0.20},
    "score": 85,
    "performance_drift": {"severity": "low"}
}

# Stocke et retourne l'évaluation avec timestamp
result = store_evaluation("model_A", evaluation)
# result["timestamp"] = "2026-03-08T14:30:00Z"
```

### 5.2 list_evaluations

```python
from app.services.history import list_evaluations

# Toutes les évaluations
evals = list_evaluations("model_A")

# Filtré par période
evals = list_evaluations(
    "model_A",
    from_ts="2026-03-01T00:00:00Z",
    to_ts="2026-03-08T00:00:00Z",
    limit=100
)
```

### 5.3 list_models

```python
from app.services.history import list_models

models = list_models()
# [
#   {"model_id": "model_A", "evaluation_count": 42, "last_score": 92},
#   {"model_id": "model_B", "evaluation_count": 38, "last_score": 88}
# ]
```

---

## 6. Exemples cURL

```bash
# Stocker une évaluation
curl -X POST http://localhost:8000/models/my_model/evaluate \
  -H "Content-Type: application/json" \
  -d '{"y_true": [1,2,3], "y_pred": [1.1,2.1,3.1], "baseline_rmse": 0.2}'

# Consulter l'historique
curl http://localhost:8000/models/my_model/history

# Historique filtré
curl "http://localhost:8000/models/my_model/history?from_ts=2026-03-01T00:00:00Z&limit=10"

# Lister tous les modèles
curl http://localhost:8000/models
```

---

## 7. Intégration Dashboard

L'historique est affiché dans :
- **Analyse Détaillée** : Tableau et graphiques d'évolution
- **Vue d'ensemble** : Dernière évaluation par modèle
- **Comparaison** : Historique des deux modèles comparés

---

## 8. Tests

**Fichier** : `tests/test_compare_models.py`

```bash
python -m pytest tests/test_compare_models.py -v
```

Les tests vérifient :
- Stockage correct des évaluations
- Filtrage par période
- Liste des modèles triée par score
