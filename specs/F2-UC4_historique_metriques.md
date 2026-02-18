# F2-UC4 : Organisation de l'Historique des Métriques

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 8 mars 2026

---

## 1. Description

Ce module organise l'historique des métriques de performance (MAE, MSE, RMSE, R²) de manière structurée, classé par modèle et par date, pour faciliter l'analyse temporelle et la comparaison.

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `app/services/history.py` | Stockage et récupération |
| `app/data/evals_*.json` | Fichiers d'historique |
| `app/main.py` | Endpoint `/models/{id}/history` |
| `dashboard/app.py` | Visualisation graphique |

---

## 3. Structure des Données

### 3.1 Fichier d'Historique

Chaque modèle a son fichier : `evals_{model_id}.json`

```json
[
  {
    "timestamp": "2026-03-01T10:00:00Z",
    "metrics": {
      "mae": 0.15,
      "mse": 0.022,
      "rmse": 0.148,
      "r2": 0.985
    },
    "score": 95,
    "performance_drift": {
      "severity": "low",
      "drift_detected": false
    }
  },
  {
    "timestamp": "2026-03-02T10:00:00Z",
    "metrics": {
      "mae": 0.18,
      "mse": 0.032,
      "rmse": 0.179,
      "r2": 0.962
    },
    "score": 92,
    "performance_drift": {
      "severity": "low",
      "drift_detected": false
    }
  }
]
```

### 3.2 Tri Chronologique

Les évaluations sont **automatiquement triées par date croissante** lors de la récupération, ce qui permet :
- Tracer des courbes d'évolution cohérentes
- Identifier les tendances facilement
- La dernière évaluation est toujours en fin de liste

---

## 4. API

### 4.1 Consulter l'Historique

```http
GET /models/{model_id}/history
```

**Paramètres optionnels :**

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `from_ts` | ISO 8601 | - | Date de début |
| `to_ts` | ISO 8601 | - | Date de fin |
| `limit` | int | 200 | Nombre max de résultats |

**Exemples :**

```bash
# Tout l'historique
curl http://localhost:8000/models/model_A/history

# Dernière semaine
curl "http://localhost:8000/models/model_A/history?from_ts=2026-03-01T00:00:00Z"

# Période spécifique, limité à 50
curl "http://localhost:8000/models/model_A/history?from_ts=2026-03-01&to_ts=2026-03-08&limit=50"
```

**Réponse :**

```json
{
  "model_id": "model_A",
  "evaluations": [
    {
      "timestamp": "2026-03-01T10:00:00Z",
      "metrics": {"mae": 0.15, "mse": 0.022, "rmse": 0.148, "r2": 0.985},
      "score": 95,
      "performance_drift": {"severity": "low", "drift_detected": false}
    },
    {
      "timestamp": "2026-03-02T10:00:00Z",
      "metrics": {"mae": 0.18, "mse": 0.032, "rmse": 0.179, "r2": 0.962},
      "score": 92,
      "performance_drift": {"severity": "low", "drift_detected": false}
    }
  ],
  "count": 2
}
```

---

## 5. Python - Utilisation

```python
from app.services.history import list_evaluations

# Récupérer l'historique complet
history = list_evaluations("model_A")

# Filtrer par période
history = list_evaluations(
    model_id="model_A",
    from_ts="2026-03-01T00:00:00Z",
    to_ts="2026-03-08T23:59:59Z",
    limit=100
)

# Extraire les métriques pour analyse
dates = [e["timestamp"] for e in history]
scores = [e["score"] for e in history]
rmse_values = [e["metrics"]["rmse"] for e in history]
```

---

## 6. Dashboard - Visualisation

### Page "Analyse Détaillée"

1. **Sélection du modèle** via dropdown
2. **Sélection de la période** (7j, 30j, 90j, tout)
3. **Graphique d'évolution** :
   - Score au fil du temps
   - RMSE au fil du temps
   - Indicateurs de drift

### Graphique interactif

```
Score
100 ┤
 95 ┤    ●───●
 90 ┤   ●     ●───●
 85 ┤  ●           ●
 80 ┤ ●
    └──────────────────► Date
      01   02   03   04
```

### Tableau historique

Le dashboard affiche aussi un tableau interactif :

| Date | Score | MAE | RMSE | R² | Drift |
|------|-------|-----|------|-----|-------|
| 08/03 14:30 | 95 | 0.15 | 0.15 | 0.98 | 🟢 LOW |
| 07/03 10:00 | 92 | 0.18 | 0.18 | 0.96 | 🟢 LOW |
| 06/03 10:00 | 78 | 0.25 | 0.28 | 0.89 | 🟠 MEDIUM |

---

## 7. Classement par Date

### Fonctionnement

1. Les évaluations sont stockées **à la suite** dans le fichier JSON
2. À la lecture, elles sont **triées par timestamp**
3. Le tri est **croissant** (plus ancien → plus récent)
4. Permet d'afficher des courbes cohérentes

### Code

```python
# Dans history.py
out.sort(key=lambda x: _parse_ts(x["timestamp"]))
return out[-max(1, limit):]  # Retourne les N dernières
```

---

## 8. Intégration

### Avec F1-UC4 (Archivage)

Les données sont stockées via `store_evaluation()` et récupérées via `list_evaluations()`.

### Avec F5-UC3 (Dashboard)

Le dashboard utilise l'endpoint `/models/{id}/history` pour afficher les graphiques.

### Avec F5-UC2 (Comparaison)

L'endpoint `/compare` utilise `list_evaluations()` pour récupérer l'historique des deux modèles.
