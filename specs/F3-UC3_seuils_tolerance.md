# F3-UC3 : Définition des Seuils de Tolérance par Modèle

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 12 mars 2026

---

## 1. Description

Permet de définir et persister des **seuils de tolérance personnalisés** par modèle pour la détection de drift et les alertes. Chaque modèle peut avoir ses propres valeurs de `baseline_rmse`, `warn_ratio`, `alert_ratio`, `alpha` et seuils de score, avec un système de **fallback à 3 niveaux** (défaut → config modèle → override).

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `app/services/thresholds.py` | CRUD des configurations + résolution par fallback |
| `app/main.py` | Endpoints REST (GET, PUT, DELETE, LIST) + intégration dans `/evaluate` |
| `app/schemas.py` | Schémas `ThresholdConfig`, `ModelConfigRequest` |
| `tests/test_thresholds.py` | 10 tests unitaires |

### Stockage

```
app/data/
├── config_air_quality_v1.json
├── config_climatrack_humidex_v1.json
└── config_model_A.json
```

---

## 3. Valeurs par Défaut

```python
DEFAULT_THRESHOLDS = {
    "performance_drift": {
        "baseline_rmse": None,
        "warn_ratio": 1.10,    # +10% → medium drift
        "alert_ratio": 1.25,   # +25% → high drift
    },
    "data_drift": {
        "alpha": 0.05,         # Seuil KS test
    },
    "score": {
        "warning_threshold": 70,
        "critical_threshold": 50,
    },
}
```

---

## 4. Système de Fallback (3 niveaux)

La fonction `get_thresholds(model_id, override)` résout les seuils effectifs :

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Défauts    │ ──► │  Config Modèle   │ ──► │   Override   │
│  (globaux)   │     │  (persistée)     │     │  (requête)   │
└──────────────┘     └──────────────────┘     └──────────────┘
     Priorité             Priorité               Priorité
     la plus              moyenne                la plus
     basse                                       haute
```

**Exemple :**
- Défaut `warn_ratio = 1.10`
- Config modèle `warn_ratio = 1.15`
- Override `warn_ratio = 1.20`
- → **Résultat effectif : 1.20**

---

## 5. Format de Configuration

```json
{
  "model_id": "air_quality_v1",
  "created_at": "2026-03-12T10:00:00Z",
  "updated_at": "2026-03-12T14:30:00Z",
  "thresholds": {
    "performance_drift": {
      "baseline_rmse": 0.20,
      "warn_ratio": 1.15,
      "alert_ratio": 1.30
    },
    "data_drift": {
      "alpha": 0.01
    },
    "score": {
      "warning_threshold": 75,
      "critical_threshold": 55
    }
  },
  "description": "Seuils ajustés pour le modèle de qualité de l'air"
}
```

---

## 6. API Endpoints

### GET `/models/{model_id}/config`

Récupère la configuration d'un modèle avec ses seuils effectifs (fusion défaut + config).

**Response 200 :**
```json
{
  "model_id": "air_quality_v1",
  "config": { "..." },
  "effective_thresholds": {
    "performance_drift": {"baseline_rmse": 0.20, "warn_ratio": 1.15, "alert_ratio": 1.30},
    "data_drift": {"alpha": 0.01},
    "score": {"warning_threshold": 75, "critical_threshold": 55}
  }
}
```

### PUT `/models/{model_id}/config`

Crée ou met à jour la configuration (merge intelligent avec l'existant).

**Request :**
```bash
curl -X PUT http://localhost:8000/models/air_quality_v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "thresholds": {
      "performance_drift": {"warn_ratio": 1.20, "alert_ratio": 1.40}
    },
    "description": "Seuils relâchés pour modèle stable"
  }'
```

### DELETE `/models/{model_id}/config`

Supprime la configuration personnalisée (retour aux valeurs par défaut).

### GET `/configs`

Liste toutes les configurations de modèles.

---

## 7. Intégration dans l'Évaluation

L'endpoint `POST /models/{model_id}/evaluate` charge automatiquement les seuils du modèle :

```python
# Dans main.py - endpoint /models/{model_id}/evaluate
thresholds = get_thresholds(model_id)
perf = thresholds["performance_drift"]
baseline = perf.get("baseline_rmse") or payload.baseline_rmse
drift = detect_performance_drift(
    current_rmse=metrics["rmse"],
    baseline_rmse=baseline,
    warn_ratio=perf["warn_ratio"],
    alert_ratio=perf["alert_ratio"],
)
```

---

## 8. Tests

**Fichier** : `tests/test_thresholds.py` — **10 tests**

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestThresholdsPersistence` | 6 | CRUD, merge, listing |
| `TestThresholdsResolution` | 4 | Fallback 3 niveaux, priorités |

```bash
python -m pytest tests/test_thresholds.py -v
```
