# F3-UC1 : Détection des Baisses Anormales de Performance (Performance Drift)

> **Statut** : 🔄 En cours  
> **Version** : 0.9  
> **Date** : 21 février 2026

---

## 1. Objectif

Détecter automatiquement toute dégradation anormale des performances d'un modèle prédictif en comparant le RMSE actuel au RMSE de référence (baseline).

---

## 2. État Actuel

### ✅ Implémenté

| Composant | Description |
|-----------|-------------|
| Algorithme de détection | Comparaison ratio RMSE actuel/baseline |
| Seuils d'alerte | 3 niveaux (low, medium, high) |
| Intégration API | Endpoint `/evaluate` retourne le drift |
| Stockage | Drift enregistré dans l'historique |

### 🔄 En cours / À faire

| Composant | Description | Priorité |
|-----------|-------------|----------|
| Seuils personnalisables par modèle | Permettre de définir des seuils différents selon le modèle | Haute |
| Historique de drift | Visualiser l'évolution du drift dans le temps | Moyenne |
| Notifications | Alerter en cas de drift détecté (voir F3-UC4) | Haute |

---

## 3. Spécification Technique

### 3.1 Algorithme

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

### 3.3 Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `current_rmse` | float | - | RMSE des prédictions actuelles |
| `baseline_rmse` | float | None | RMSE de référence |
| `warn_ratio` | float | 1.10 | Seuil pour sévérité medium |
| `alert_ratio` | float | 1.25 | Seuil pour sévérité high |

---

## 4. Structure de Sortie

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

## 5. Implémentation Actuelle

**Fichier** : `app/services/drift.py`

```python
def detect_performance_drift(
    current_rmse: float,
    baseline_rmse: Optional[float],
    warn_ratio: float = 1.10,
    alert_ratio: float = 1.25
) -> Dict:
    if baseline_rmse is None or baseline_rmse <= 0:
        return {
            "severity": "unknown",
            "drift_detected": False,
            "reason": "baseline_rmse manquant ou invalide"
        }

    ratio = current_rmse / baseline_rmse

    if ratio >= alert_ratio:
        severity = "high"
        drift_detected = True
    elif ratio >= warn_ratio:
        severity = "medium"
        drift_detected = True
    else:
        severity = "low"
        drift_detected = False

    return {
        "baseline_rmse": baseline_rmse,
        "current_rmse": current_rmse,
        "ratio": ratio,
        "severity": severity,
        "drift_detected": drift_detected
    }
```

---

## 6. Évolutions Prévues

### 6.1 Seuils Personnalisables (Priorité Haute)

**Objectif** : Permettre de définir des seuils spécifiques par modèle.

**Proposition d'API** :
```http
POST /models/{model_id}/drift-config
{
  "warn_ratio": 1.15,
  "alert_ratio": 1.30
}
```

**Stockage** : Fichier `app/data/drift_config_{model_id}.json`

### 6.2 Historique de Drift (Priorité Moyenne)

**Objectif** : Visualiser l'évolution du ratio de drift dans le temps.

**Endpoint proposé** :
```http
GET /models/{model_id}/drift-history?window_days=30
```

**Réponse** :
```json
{
  "model_id": "air_quality_v1",
  "history": [
    {"timestamp": "2026-02-20T10:00:00Z", "ratio": 0.95, "severity": "low"},
    {"timestamp": "2026-02-20T14:00:00Z", "ratio": 1.12, "severity": "medium"},
    {"timestamp": "2026-02-21T08:00:00Z", "ratio": 1.28, "severity": "high"}
  ]
}
```

---

## 7. Diagramme de Flux

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

## 8. Critères d'Acceptation

### MVP (Actuel)
- [x] Calcul du ratio RMSE/baseline
- [x] 3 niveaux de sévérité (low, medium, high)
- [x] Intégration avec l'endpoint `/evaluate`
- [x] Stockage du drift dans l'historique

### Lot 1 (En cours)
- [ ] Seuils personnalisables par modèle
- [ ] Endpoint dédié pour la configuration des seuils
- [ ] Historique de drift consultable via API

### Lot 2 (Futur)
- [ ] Visualisation graphique de l'évolution du drift
- [ ] Prédiction de drift (tendance)
- [ ] Alertes proactives avant dépassement de seuil
