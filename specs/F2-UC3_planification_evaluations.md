# F2-UC3 : Planification Automatique des Évaluations

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 21 février 2026

---

## 1. Description

Ce service gère la planification automatique des évaluations de modèles. Il permet d'exécuter périodiquement le calcul des métriques de performance sans intervention manuelle, en utilisant asyncio pour l'exécution en arrière-plan.

---

## 2. Architecture

### Module
- **Fichier** : `app/services/scheduler.py`
- **Classe** : `Scheduler`
- **Instance globale** : `scheduler`

### Stockage
- **Format** : JSON
- **Emplacement** : `app/data/schedules.json`
- **Persistance** : Automatique à chaque modification

### Dépendances
- `asyncio` : Exécution asynchrone
- `dataclasses` : Structures de données
- `logging` : Journalisation

---

## 3. Structure des Données

### ScheduleConfig

```python
@dataclass
class ScheduleConfig:
    schedule_id: str              # Identifiant unique
    model_id: str                 # Modèle à évaluer
    interval_minutes: int         # Intervalle entre exécutions
    y_true: List[float]           # Valeurs réelles
    y_pred: List[float]           # Valeurs prédites
    baseline_rmse: Optional[float] # RMSE de référence
    status: ScheduleStatus        # État du schedule
    created_at: str               # Date de création (ISO 8601)
    last_run: Optional[str]       # Dernière exécution
    next_run: Optional[str]       # Prochaine exécution
    run_count: int                # Nombre d'exécutions
    max_runs: Optional[int]       # Limite d'exécutions (None = infini)
```

### ScheduleStatus (Enum)

| Valeur | Description |
|--------|-------------|
| `ACTIVE` | Schedule actif, en cours d'exécution |
| `PAUSED` | Schedule en pause |
| `COMPLETED` | Terminé (max_runs atteint) |
| `ERROR` | Erreur lors de l'exécution |

---

## 4. API Endpoints

### Statut global du scheduler

```http
GET /scheduler/status
```

**Response 200 :**
```json
{
  "running": true,
  "total_schedules": 3,
  "active_tasks": 2,
  "status_counts": {
    "active": 2,
    "paused": 1,
    "completed": 0,
    "error": 0
  }
}
```

### Lister les schedules

```http
GET /scheduler/schedules
```

**Response 200 :**
```json
{
  "schedules": [
    {
      "schedule_id": "sched_model_A_20260221143000",
      "model_id": "model_A",
      "interval_minutes": 60,
      "status": "active",
      "run_count": 5,
      "last_run": "2026-02-21T14:30:00Z",
      "next_run": "2026-02-21T15:30:00Z"
    }
  ]
}
```

### Créer un schedule

```http
POST /scheduler/schedules
Content-Type: application/json
```

**Request Body :**
```json
{
  "model_id": "air_quality_v1",
  "interval_minutes": 60,
  "y_true": [1.0, 2.0, 3.0, 4.0, 5.0],
  "y_pred": [1.1, 2.1, 2.9, 4.1, 4.9],
  "baseline_rmse": 0.5,
  "max_runs": 100
}
```

**Response 201 :**
```json
{
  "schedule_id": "sched_air_quality_v1_20260221150000",
  "model_id": "air_quality_v1",
  "status": "active",
  "interval_minutes": 60,
  "created_at": "2026-02-21T15:00:00Z",
  "next_run": "2026-02-21T15:00:00Z"
}
```

### Détail d'un schedule

```http
GET /scheduler/schedules/{schedule_id}
```

### Mettre en pause

```http
POST /scheduler/schedules/{schedule_id}/pause
```

**Response 200 :**
```json
{
  "schedule_id": "sched_model_A_20260221143000",
  "status": "paused",
  "message": "Schedule mis en pause"
}
```

### Reprendre

```http
POST /scheduler/schedules/{schedule_id}/resume
```

### Déclencher manuellement

```http
POST /scheduler/schedules/{schedule_id}/trigger
```

**Response 200 :**
```json
{
  "schedule_id": "sched_model_A_20260221143000",
  "evaluation_result": {
    "metrics": {"mae": 0.14, "rmse": 0.16},
    "score": 87
  }
}
```

### Supprimer un schedule

```http
DELETE /scheduler/schedules/{schedule_id}
```

---

## 5. Fonctionnalités

### 5.1 Création de Schedule

- Génération d'un ID unique : `sched_{model_id}_{timestamp}`
- Initialisation des timestamps (created_at, next_run)
- Sauvegarde immédiate dans le fichier JSON
- Démarrage automatique si le scheduler est actif

### 5.2 Exécution Périodique

- Boucle asyncio pour chaque schedule actif
- Calcul du délai jusqu'au prochain run
- Exécution de l'évaluation via callback
- Mise à jour des compteurs et timestamps

### 5.3 Gestion du Cycle de Vie

| Action | Effet |
|--------|-------|
| **Pause** | Arrête la tâche asyncio, conserve l'état |
| **Resume** | Replanifie immédiatement, relance la tâche |
| **Delete** | Annule la tâche, supprime de la persistance |
| **Trigger** | Exécute immédiatement sans attendre |

### 5.4 Complétion Automatique

Lorsque `max_runs` est défini et atteint :
- Le status passe à `COMPLETED`
- La tâche asyncio est arrêtée
- Le schedule reste en historique

---

## 6. Exemples d'utilisation

### Via API

**Créer un schedule :**
```bash
curl -X POST http://localhost:8000/scheduler/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "temperature_predictor",
    "interval_minutes": 30,
    "y_true": [22.5, 23.0, 22.8, 23.2],
    "y_pred": [22.4, 23.1, 22.7, 23.3],
    "baseline_rmse": 0.2
  }'
```

**Déclencher manuellement :**
```bash
curl -X POST http://localhost:8000/scheduler/schedules/sched_temperature_predictor_20260221/trigger
```

**Mettre en pause :**
```bash
curl -X POST http://localhost:8000/scheduler/schedules/sched_temperature_predictor_20260221/pause
```

### Via Python

```python
from app.services.scheduler import scheduler

# Définir le callback d'évaluation
def evaluate_model(model_id, y_true, y_pred, baseline_rmse=None):
    from app.services.metrics import compute_metrics
    from app.services.drift import detect_drift
    from app.services.scoring import calculate_score
    
    metrics = compute_metrics(y_true, y_pred)
    drift = detect_drift(metrics["rmse"], baseline_rmse)
    score = calculate_score(metrics["rmse"], baseline_rmse, drift["severity"])
    
    return {"metrics": metrics, "drift": drift, "score": score}

scheduler.set_evaluation_callback(evaluate_model)

# Créer un schedule
schedule = scheduler.create_schedule(
    model_id="air_quality_v1",
    interval_minutes=60,
    y_true=[1.0, 2.0, 3.0],
    y_pred=[1.1, 2.0, 3.1],
    baseline_rmse=0.5,
    max_runs=24  # Évaluer pendant 24 heures
)

print(f"Schedule créé : {schedule.schedule_id}")

# Déclencher manuellement
result = scheduler.trigger_now(schedule.schedule_id)
print(f"Score : {result['score']}")

# Lister les schedules
for s in scheduler.list_schedules():
    print(f"{s['model_id']}: {s['status']} ({s['run_count']} runs)")
```

---

## 7. Persistance

### Format du fichier schedules.json

```json
[
  {
    "schedule_id": "sched_model_A_20260221100000",
    "model_id": "model_A",
    "interval_minutes": 60,
    "y_true": [1.0, 2.0, 3.0],
    "y_pred": [1.1, 2.0, 3.1],
    "baseline_rmse": 0.5,
    "status": "active",
    "created_at": "2026-02-21T10:00:00Z",
    "last_run": "2026-02-21T14:00:00Z",
    "next_run": "2026-02-21T15:00:00Z",
    "run_count": 4,
    "max_runs": null
  }
]
```

### Chargement au démarrage
- Les schedules sont chargés depuis le fichier au démarrage
- Les tâches actives sont relancées automatiquement
- Le `next_run` est recalculé si nécessaire

---

## 8. Tests

**Fichier** : `tests/test_scheduler.py`  
**Nombre de tests** : 319 lignes de tests

### Exécution

```bash
python -m pytest tests/test_scheduler.py -v
```

### Couverture des tests

| Catégorie | Description |
|-----------|-------------|
| Création | IDs uniques, timestamps, max_runs |
| Pause/Resume | Changement d'état, annulation tâches |
| Delete | Suppression, nettoyage |
| Trigger | Exécution manuelle |
| Statistiques | Compteurs, états |

---

## 9. Logging

Le scheduler utilise le module `logging` pour tracer les événements :

| Niveau | Événement |
|--------|-----------|
| `INFO` | Création, pause, resume, suppression |
| `INFO` | Exécution d'une évaluation |
| `INFO` | Complétion (max_runs atteint) |
| `ERROR` | Erreur lors d'une évaluation |
| `DEBUG` | Détails techniques (boucle asyncio) |

### Exemple de logs

```
INFO:scheduler:Schedule créé: sched_model_A_20260221143000 pour modèle model_A
INFO:scheduler:Évaluation exécutée pour model_A (run #1)
INFO:scheduler:Schedule pausé: sched_model_A_20260221143000
INFO:scheduler:Schedule repris: sched_model_A_20260221143000
INFO:scheduler:Schedule sched_model_A_20260221143000 terminé (max_runs atteint)
```

---

## 10. Intégration

### Avec le Dashboard (F5-UC3)

La page "⏰ Planification" du dashboard permet de :
- Visualiser tous les schedules
- Créer de nouveaux schedules
- Pause/Resume/Delete via l'interface
- Déclencher manuellement des évaluations

### Avec l'Historique (F1-UC5)

Chaque évaluation planifiée est automatiquement enregistrée dans l'historique du modèle via le callback d'évaluation.
