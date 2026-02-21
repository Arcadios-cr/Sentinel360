# 🔌 API Reference - Sentinel360

Documentation complète de l'API REST.

## Base URL

| Environnement | URL |
|---------------|-----|
| Local | `http://localhost:8000` |
| Docker | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |

---

## Authentification

Actuellement, l'API ne requiert pas d'authentification (MVP).

> **Note** : L'authentification JWT sera ajoutée dans le Lot 2.

---

## Endpoints

### 🏥 Health Check

#### GET /health

Vérifie que le service est opérationnel.

**Request**
```bash
curl http://localhost:8000/health
```

**Response** `200 OK`
```json
{
  "status": "ok"
}
```

---

### 📊 Évaluation

#### POST /evaluate

Évalue un modèle avec les données fournies.

**Request**
```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "air_quality_v1",
    "y_true": [1.0, 2.0, 3.0, 4.0, 5.0],
    "y_pred": [1.1, 2.2, 2.9, 4.1, 4.8],
    "baseline_rmse": 0.2
  }'
```

**Request Body**

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `model_id` | string | Oui | Identifiant unique du modèle |
| `y_true` | array[float] | Oui | Valeurs réelles |
| `y_pred` | array[float] | Oui | Valeurs prédites |
| `baseline_rmse` | float | Non | RMSE de référence pour le drift |

**Response** `200 OK`
```json
{
  "model_id": "air_quality_v1",
  "timestamp": "2026-02-01T15:30:00Z",
  "metrics": {
    "mae": 0.14,
    "mse": 0.026,
    "rmse": 0.161,
    "r2": 0.987
  },
  "performance_drift": {
    "detected": false,
    "rmse_change_pct": -19.5,
    "severity": "none"
  },
  "score": 92.5
}
```

**Errors**

| Code | Description |
|------|-------------|
| `400` | Données invalides (longueurs différentes, arrays vides) |
| `422` | Erreur de validation Pydantic |

---

#### POST /drift-data

Analyse la dérive des données entre deux distributions.

**Request**
```bash
curl -X POST http://localhost:8000/drift-data \
  -H "Content-Type: application/json" \
  -d '{
    "reference": {"temperature": [20, 21, 22, 23, 24, 25]},
    "current": {"temperature": [25, 26, 27, 28, 29, 30]},
    "alpha": 0.05
  }'
```

**Request Body**

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `reference` | object | Oui | Données de référence (dict de features) |
| `current` | object | Oui | Données actuelles (dict de features) |
| `alpha` | float | Non | Seuil de significativité (défaut: 0.05) |

**Response** `200 OK`
```json
{
  "drift_detected": true,
  "features": {
    "temperature": {
      "ks_statistic": 0.6,
      "p_value": 0.023,
      "drift_detected": true
    }
  },
  "summary": {
    "total_features": 1,
    "drifted_features": 1,
    "drift_percentage": 100.0
  }
}
```

---

### 📋 Modèles

#### GET /models

Liste tous les modèles enregistrés.

**Request**
```bash
curl http://localhost:8000/models
```

**Response** `200 OK`
```json
{
  "models": [
    {
      "model_id": "air_quality_v1",
      "evaluation_count": 15,
      "latest_score": 87.5,
      "latest_evaluation": "2026-02-01T14:00:00Z"
    },
    {
      "model_id": "air_quality_v2",
      "evaluation_count": 10,
      "latest_score": 95.2,
      "latest_evaluation": "2026-02-01T15:00:00Z"
    }
  ],
  "total_count": 2
}
```

---

#### GET /models/ranking

Classement des modèles par métrique.

**Request**
```bash
curl "http://localhost:8000/models/ranking?metric=score&limit=10"
```

**Query Parameters**

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `metric` | string | Non | Métrique de tri: `score`, `rmse`, `mae`, `r2` (défaut: `score`) |
| `limit` | int | Non | Nombre max de résultats (défaut: 10) |

**Response** `200 OK`
```json
{
  "ranking": [
    {
      "rank": 1,
      "model_id": "air_quality_v2",
      "score": 95.2,
      "metrics": {
        "mae": 0.08,
        "rmse": 0.12,
        "r2": 0.995
      }
    },
    {
      "rank": 2,
      "model_id": "air_quality_v1",
      "score": 87.5,
      "metrics": {
        "mae": 0.15,
        "rmse": 0.18,
        "r2": 0.982
      }
    }
  ],
  "metric_used": "score",
  "total_models": 2
}
```

---

#### POST /compare

Compare plusieurs modèles.

**Request**
```bash
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"model_ids": ["air_quality_v1", "air_quality_v2"]}'
```

**Request Body**

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `model_ids` | array[string] | Oui | Liste des IDs de modèles à comparer (min: 2) |

**Response** `200 OK`
```json
{
  "comparison": [
    {
      "model_id": "air_quality_v1",
      "latest_score": 87.5,
      "avg_score": 85.2,
      "evaluation_count": 15,
      "latest_metrics": {
        "mae": 0.15,
        "rmse": 0.18,
        "r2": 0.982
      }
    },
    {
      "model_id": "air_quality_v2",
      "latest_score": 95.2,
      "avg_score": 93.8,
      "evaluation_count": 10,
      "latest_metrics": {
        "mae": 0.08,
        "rmse": 0.12,
        "r2": 0.995
      }
    }
  ],
  "best_model": {
    "by_score": "air_quality_v2",
    "by_rmse": "air_quality_v2",
    "by_r2": "air_quality_v2"
  }
}
```

---

### ⏰ Planificateur

#### GET /scheduler/schedules

Liste toutes les planifications.

**Request**
```bash
curl http://localhost:8000/scheduler/schedules
```

**Response** `200 OK`
```json
{
  "schedules": [
    {
      "id": "20260201153000123456",
      "model_id": "air_quality_v1",
      "interval_seconds": 3600,
      "baseline_rmse": 0.2,
      "enabled": true,
      "created_at": "2026-02-01T15:30:00Z",
      "last_run": "2026-02-01T16:30:00Z",
      "next_run": "2026-02-01T17:30:00Z",
      "run_count": 1
    }
  ],
  "total_count": 1
}
```

---

#### POST /scheduler/schedules

Crée une nouvelle planification.

**Request**
```bash
curl -X POST http://localhost:8000/scheduler/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "air_quality_v1",
    "interval_seconds": 3600,
    "baseline_rmse": 0.2
  }'
```

**Request Body**

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `model_id` | string | Oui | Identifiant du modèle |
| `interval_seconds` | int | Oui | Intervalle entre les exécutions (secondes) |
| `baseline_rmse` | float | Non | RMSE de référence |

**Response** `201 Created`
```json
{
  "id": "20260201153000123456",
  "model_id": "air_quality_v1",
  "interval_seconds": 3600,
  "baseline_rmse": 0.2,
  "enabled": true,
  "created_at": "2026-02-01T15:30:00Z",
  "message": "Schedule created successfully"
}
```

---

#### GET /scheduler/schedules/{id}

Détail d'une planification.

**Request**
```bash
curl http://localhost:8000/scheduler/schedules/20260201153000123456
```

**Response** `200 OK`
```json
{
  "id": "20260201153000123456",
  "model_id": "air_quality_v1",
  "interval_seconds": 3600,
  "baseline_rmse": 0.2,
  "enabled": true,
  "created_at": "2026-02-01T15:30:00Z",
  "last_run": "2026-02-01T16:30:00Z",
  "next_run": "2026-02-01T17:30:00Z",
  "run_count": 1
}
```

**Errors**

| Code | Description |
|------|-------------|
| `404` | Planification non trouvée |

---

#### DELETE /scheduler/schedules/{id}

Supprime une planification.

**Request**
```bash
curl -X DELETE http://localhost:8000/scheduler/schedules/20260201153000123456
```

**Response** `200 OK`
```json
{
  "message": "Schedule deleted successfully",
  "id": "20260201153000123456"
}
```

---

#### POST /scheduler/schedules/{id}/pause

Met une planification en pause.

**Request**
```bash
curl -X POST http://localhost:8000/scheduler/schedules/20260201153000123456/pause
```

**Response** `200 OK`
```json
{
  "message": "Schedule paused",
  "id": "20260201153000123456",
  "enabled": false
}
```

---

#### POST /scheduler/schedules/{id}/resume

Reprend une planification en pause.

**Request**
```bash
curl -X POST http://localhost:8000/scheduler/schedules/20260201153000123456/resume
```

**Response** `200 OK`
```json
{
  "message": "Schedule resumed",
  "id": "20260201153000123456",
  "enabled": true
}
```

---

#### POST /scheduler/schedules/{id}/trigger

Déclenche immédiatement une évaluation.

**Request**
```bash
curl -X POST http://localhost:8000/scheduler/schedules/20260201153000123456/trigger
```

**Response** `200 OK`
```json
{
  "message": "Evaluation triggered",
  "id": "20260201153000123456",
  "result": {
    "model_id": "air_quality_v1",
    "score": 87.5,
    "metrics": {...}
  }
}
```

---

#### GET /scheduler/status

Statut global du planificateur.

**Request**
```bash
curl http://localhost:8000/scheduler/status
```

**Response** `200 OK`
```json
{
  "running": true,
  "total_schedules": 3,
  "active_schedules": 2,
  "paused_schedules": 1,
  "total_executions": 45
}
```

---

## Codes d'Erreur

| Code | Signification |
|------|---------------|
| `200` | Succès |
| `201` | Ressource créée |
| `400` | Requête invalide |
| `404` | Ressource non trouvée |
| `422` | Erreur de validation |
| `500` | Erreur serveur |

## Format des Erreurs

```json
{
  "detail": "Description de l'erreur"
}
```

---

## Rate Limiting

Pas de rate limiting dans le MVP. Sera ajouté dans le Lot 2.

---

## Exemples PowerShell

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/health"

# Évaluer un modèle
$body = @{
    model_id = "test_model"
    y_true = @(1.0, 2.0, 3.0, 4.0, 5.0)
    y_pred = @(1.1, 2.2, 2.9, 4.1, 4.8)
    baseline_rmse = 0.2
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/evaluate" -Method Post -Body $body -ContentType "application/json"

# Lister les modèles
Invoke-RestMethod -Uri "http://localhost:8000/models"
```

---

*Dernière mise à jour : 1er février 2026*
