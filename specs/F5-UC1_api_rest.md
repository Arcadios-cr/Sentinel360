# F5-UC1 : Transmission des Métriques, Dérive et Score via API REST

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 21 février 2026

---

## 1. Description

L'API REST Sentinel360 expose tous les résultats d'évaluation, de détection de drift et de scoring via des endpoints HTTP standardisés.

---

## 2. Architecture

### Framework
- **Technologie** : FastAPI 0.128
- **Validation** : Pydantic 2.x
- **Documentation** : OpenAPI/Swagger automatique

### URLs
| Environnement | URL |
|---------------|-----|
| Local | `http://localhost:8000` |
| Docker | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |

---

## 3. Endpoints Disponibles

### Santé et Status

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/health` | Vérification de l'état du service |

### Évaluation

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/evaluate` | Évaluer sans persistance |
| `POST` | `/models/{model_id}/evaluate` | Évaluer et sauvegarder |
| `GET` | `/models/{model_id}/evaluations` | Historique d'un modèle |

### Modèles

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/models` | Liste de tous les modèles |
| `GET` | `/models/ranking` | Classement par score |
| `GET` | `/compare` | Comparer deux modèles |

### Drift de Données

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/drift-data` | Analyser le data drift |

### Nettoyage des Données

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/data/files` | Lister les fichiers |
| `POST` | `/data/preview` | Prévisualiser un fichier |
| `POST` | `/data/clean` | Nettoyer un fichier |
| `POST` | `/data/clean-all` | Nettoyer tous les fichiers |

### Planificateur

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/scheduler/status` | Statut global |
| `GET` | `/scheduler/schedules` | Lister les tâches |
| `POST` | `/scheduler/schedules` | Créer une tâche |
| `GET` | `/scheduler/schedules/{id}` | Détail d'une tâche |
| `DELETE` | `/scheduler/schedules/{id}` | Supprimer une tâche |
| `POST` | `/scheduler/schedules/{id}/pause` | Mettre en pause |
| `POST` | `/scheduler/schedules/{id}/resume` | Reprendre |
| `POST` | `/scheduler/schedules/{id}/trigger` | Déclencher maintenant |

---

## 4. Détail des Endpoints Principaux

### 4.1 Health Check

```http
GET /health
```

**Response 200:**
```json
{
  "status": "ok"
}
```

---

### 4.2 Évaluation Complète

```http
POST /evaluate
Content-Type: application/json
```

**Request Body:**
```json
{
  "y_true": [1.0, 2.0, 3.0, 4.0, 5.0],
  "y_pred": [1.1, 2.2, 2.9, 4.1, 4.8],
  "baseline_rmse": 0.2
}
```

**Response 200:**
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
    "delta": -0.039,
    "severity": "low",
    "drift_detected": false,
    "reason": "performance stable"
  },
  "score": 100
}
```

---

### 4.3 Analyse Data Drift

```http
POST /drift-data
Content-Type: application/json
```

**Request Body:**
```json
{
  "reference": {
    "temperature": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
  },
  "current": {
    "temperature": [25, 26, 27, 28, 29, 30, 31, 32, 33, 34]
  },
  "alpha": 0.05
}
```

**Response 200:**
```json
{
  "alpha": 0.05,
  "features_compared": 1,
  "features_drifted": 1,
  "global_drift": true,
  "feature_results": {
    "temperature": {
      "status": "ok",
      "n_ref": 10,
      "n_cur": 10,
      "ks_stat": 0.6,
      "ks_crit": 0.608,
      "drift_detected": false
    }
  }
}
```

---

### 4.4 Liste des Modèles

```http
GET /models
```

**Response 200:**
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

### 4.5 Classement des Modèles

```http
GET /models/ranking?window_days=7
```

**Response 200:**
```json
{
  "window_days": 7,
  "ranking": [
    {
      "rank": 1,
      "model_id": "model_A",
      "avg_score": 89.5,
      "avg_rmse": 0.12,
      "evaluation_count": 15
    },
    {
      "rank": 2,
      "model_id": "model_B",
      "avg_score": 82.3,
      "avg_rmse": 0.18,
      "evaluation_count": 10
    }
  ]
}
```

---

### 4.6 Comparaison de Modèles

```http
GET /compare?model_a=model_A&model_b=model_B&window_days=7
```

**Response 200:**
```json
{
  "window_days": 7,
  "model_a": {
    "model_id": "model_A",
    "avg_score": 89.5,
    "avg_mae": 0.10,
    "avg_rmse": 0.12,
    "avg_r2": 0.96
  },
  "model_b": {
    "model_id": "model_B",
    "avg_score": 82.3,
    "avg_mae": 0.15,
    "avg_rmse": 0.18,
    "avg_r2": 0.92
  },
  "winner": {
    "by_score": "model_A",
    "by_rmse": "model_A",
    "by_r2": "model_A"
  }
}
```

---

## 5. Schémas de Validation (Pydantic)

### EvaluateRequest

```python
class EvaluateRequest(BaseModel):
    y_true: List[float]           # Valeurs réelles
    y_pred: List[float]           # Prédictions
    baseline_rmse: Optional[float] = None  # RMSE de référence
```

### DataDriftRequest

```python
class DataDriftRequest(BaseModel):
    reference: Dict[str, List[float]]  # Features de référence
    current: Dict[str, List[float]]    # Features actuelles
    alpha: float = 0.05                 # Seuil de significativité
```

### ScheduleRequest

```python
class ScheduleRequest(BaseModel):
    model_id: str
    interval_minutes: int
    y_true: List[float]
    y_pred: List[float]
    baseline_rmse: Optional[float] = None
    max_runs: Optional[int] = None
```

---

## 6. Codes de Réponse HTTP

| Code | Signification | Cas d'usage |
|------|---------------|-------------|
| 200 | OK | Requête réussie |
| 201 | Created | Ressource créée (schedule) |
| 400 | Bad Request | Données invalides |
| 404 | Not Found | Modèle/Schedule non trouvé |
| 422 | Unprocessable Entity | Erreur de validation Pydantic |
| 500 | Internal Server Error | Erreur serveur |

---

## 7. Documentation Interactive

Accès à la documentation Swagger :

```
http://localhost:8000/docs
```

Fonctionnalités :
- ✅ Liste de tous les endpoints
- ✅ Schémas de requêtes/réponses
- ✅ Test interactif des endpoints
- ✅ Génération automatique depuis le code

---

## 8. Exemples cURL

### Évaluer un modèle
```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"y_true": [1,2,3,4,5], "y_pred": [1.1,2.1,3.1,4.1,5.1], "baseline_rmse": 0.2}'
```

### Sauvegarder une évaluation
```bash
curl -X POST http://localhost:8000/models/air_quality_v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"y_true": [1,2,3,4,5], "y_pred": [1.1,2.1,3.1,4.1,5.1], "baseline_rmse": 0.2}'
```

### Lister les modèles
```bash
curl http://localhost:8000/models
```

### Obtenir le classement
```bash
curl "http://localhost:8000/models/ranking?window_days=7"
```

---

## 9. Tests

**Fichier** : Intégration via les autres tests

Vérification du health check :
```bash
curl http://localhost:8000/health
# {"status": "ok"}
```
