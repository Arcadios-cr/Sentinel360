# F5-UC2 : Endpoints de Comparaison entre Modèles

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 8 mars 2026

---

## 1. Description

Ce module fournit des endpoints API permettant de comparer les performances de plusieurs modèles IA sur une période donnée, avec calcul automatique des moyennes et détermination du meilleur modèle.

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `app/services/history.py` | Fonctions `compare_models()` et `rank_models()` |
| `app/main.py` | Endpoints `/compare` et `/ranking` |
| `dashboard/app.py` | Page "Comparaison" |
| `tests/test_compare_models.py` | Tests unitaires |

---

## 3. API

### 3.1 Comparer Deux Modèles

```http
GET /compare?model_a={id_a}&model_b={id_b}&window_days={n}
```

**Paramètres :**

| Paramètre | Type | Requis | Défaut | Description |
|-----------|------|--------|--------|-------------|
| `model_a` | string | ✅ | - | ID du premier modèle |
| `model_b` | string | ✅ | - | ID du second modèle |
| `window_days` | int | ❌ | 7 | Période d'analyse en jours |

**Exemple :**

```bash
curl "http://localhost:8000/compare?model_a=model_A&model_b=model_B&window_days=30"
```

**Réponse :**

```json
{
  "window_days": 30,
  "model_a": {
    "id": "model_A",
    "n": 45,
    "avg_score": 92.5,
    "avg_rmse": 0.18,
    "last": {
      "timestamp": "2026-03-08T14:30:00Z",
      "score": 95,
      "metrics": {"mae": 0.12, "rmse": 0.15, "r2": 0.98}
    }
  },
  "model_b": {
    "id": "model_B",
    "n": 42,
    "avg_score": 88.3,
    "avg_rmse": 0.22,
    "last": {
      "timestamp": "2026-03-08T12:00:00Z",
      "score": 87,
      "metrics": {"mae": 0.18, "rmse": 0.23, "r2": 0.94}
    }
  },
  "winner": "model_A"
}
```

### 3.2 Classement de Tous les Modèles

```http
GET /ranking?window_days={n}
```

**Paramètres :**

| Paramètre | Type | Requis | Défaut | Description |
|-----------|------|--------|--------|-------------|
| `window_days` | int | ❌ | 7 | Période d'analyse en jours |

**Exemple :**

```bash
curl "http://localhost:8000/ranking?window_days=7"
```

**Réponse :**

```json
{
  "window_days": 7,
  "ranking": [
    {
      "rank": 1,
      "model_id": "climatrack_humidex_v1",
      "avg_score": 98.2,
      "avg_rmse": 0.008,
      "evaluation_count": 15,
      "last_evaluation": "2026-03-08T14:30:00Z"
    },
    {
      "rank": 2,
      "model_id": "model_A",
      "avg_score": 92.5,
      "avg_rmse": 0.18,
      "evaluation_count": 20,
      "last_evaluation": "2026-03-08T12:00:00Z"
    },
    {
      "rank": 3,
      "model_id": "model_B",
      "avg_score": 88.3,
      "avg_rmse": 0.22,
      "evaluation_count": 18,
      "last_evaluation": "2026-03-07T10:00:00Z"
    }
  ],
  "total_models": 3
}
```

---

## 4. Calculs Effectués

### 4.1 Score Moyen

```python
avg_score = sum(scores) / len(scores)
```

Calculé sur toutes les évaluations de la période.

### 4.2 RMSE Moyen

```python
avg_rmse = sum(rmse_values) / len(rmse_values)
```

### 4.3 Détermination du Gagnant

```python
winner = model_a if avg_score_a >= avg_score_b else model_b
```

Le gagnant est le modèle avec le **score moyen le plus élevé**.

---

## 5. Python - Utilisation

### Comparaison

```python
from app.services.history import compare_models

result = compare_models("model_A", "model_B", window_days=30)

print(f"Gagnant: {result['winner']}")
print(f"Model A - Score moyen: {result['model_a']['avg_score']}")
print(f"Model B - Score moyen: {result['model_b']['avg_score']}")
```

### Ranking

```python
from app.services.history import rank_models

ranking = rank_models(window_days=7)

for model in ranking["ranking"]:
    print(f"#{model['rank']} {model['model_id']}: {model['avg_score']:.1f}")
```

---

## 6. Dashboard - Visualisation

### Page "Comparaison"

1. **Sélection des modèles** via 2 dropdowns
2. **Sélection de la période** (7j, 30j, 90j)
3. **Affichage côte à côte** :
   - KPIs (score, RMSE, R²)
   - Graphiques d'évolution superposés
   - Indicateur du gagnant

### Interface

```
┌─────────────────────┬─────────────────────┐
│      MODEL A        │      MODEL B        │
├─────────────────────┼─────────────────────┤
│  Score: 92.5 🏆     │  Score: 88.3        │
│  RMSE:  0.18        │  RMSE:  0.22        │
│  R²:    0.96        │  R²:    0.94        │
│  Evals: 45          │  Evals: 42          │
└─────────────────────┴─────────────────────┘

        📊 Évolution Comparative
   [Graphique avec 2 courbes superposées]
```

---

## 7. Exemples cURL

```bash
# Comparer deux modèles sur 7 jours
curl "http://localhost:8000/compare?model_a=model_A&model_b=model_B"

# Comparer sur 30 jours
curl "http://localhost:8000/compare?model_a=model_A&model_b=model_B&window_days=30"

# Ranking global sur 7 jours
curl http://localhost:8000/ranking

# Ranking sur 30 jours
curl "http://localhost:8000/ranking?window_days=30"
```

---

## 8. Tests

**Fichier** : `tests/test_compare_models.py`

```bash
python -m pytest tests/test_compare_models.py -v
```

### Cas testés

| Test | Description |
|------|-------------|
| Comparaison basique | 2 modèles avec historique |
| Modèle sans données | Gestion du cas vide |
| Période variable | 7j, 30j, 90j |
| Égalité de score | Comportement en cas d'égalité |
| Ranking complet | Tri correct par score |

---

## 9. Intégration

### Avec F2-UC4 (Historique)

Utilise `list_evaluations()` pour récupérer l'historique des modèles à comparer.

### Avec F5-UC3 (Dashboard)

La page "Comparaison" appelle l'endpoint `/compare` et affiche les résultats.

### Avec F4-UC1 (Score Global)

Le score utilisé pour la comparaison est le score global calculé par le module scoring.
