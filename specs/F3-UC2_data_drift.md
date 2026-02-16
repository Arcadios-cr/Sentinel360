# F3-UC2 : Détection des Dérives Statistiques (Data Drift)

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 8 mars 2026

---

## 1. Description

Cette feature détecte automatiquement les changements de distribution des données d'entrée (features) entre une période de référence et la période actuelle, via le test statistique de Kolmogorov-Smirnov (KS).

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `app/services/data_drift.py` | Algorithme de détection du data drift (test KS) |
| `app/main.py` | Endpoint `POST /drift-data` |
| `tests/test_data_drift.py` | Tests unitaires (~25 tests) |

---

## 3. Algorithme - Test de Kolmogorov-Smirnov

### 3.1 Principe

Le test KS compare les fonctions de distribution cumulative (CDF) de deux échantillons.

**Hypothèses :**
- **H0** : Les deux échantillons proviennent de la même distribution
- **H1** : Les distributions sont différentes

### 3.2 Statistique KS

```
D = max |F_ref(x) - F_cur(x)|
```

### 3.3 Seuil Critique

```
D_crit = c(α) × √((n + m) / (n × m))
```

| Alpha (α) | c(α) |
|-----------|------|
| 0.05 | 1.36 |
| 0.01 | 1.63 |

**Décision :** Si `D > D_crit` → Drift détecté

---

## 4. API

### Endpoint

```http
POST /drift-data
```

### Paramètres d'entrée

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `reference` | Dict[str, List[float]] | - | Features de référence |
| `current` | Dict[str, List[float]] | - | Features actuelles |
| `alpha` | float | 0.05 | Niveau de significativité |

### Structure de Sortie

```json
{
  "alpha": 0.05,
  "features_compared": 3,
  "features_drifted": 1,
  "global_drift": true,
  "feature_results": {
    "temperature": {
      "status": "ok",
      "n_ref": 100,
      "n_cur": 50,
      "ks_stat": 0.12,
      "ks_crit": 0.22,
      "drift_detected": false
    },
    "humidity": {
      "status": "ok",
      "n_ref": 100,
      "n_cur": 50,
      "ks_stat": 0.35,
      "ks_crit": 0.22,
      "drift_detected": true
    },
    "CO2": {
      "status": "skipped",
      "reason": "pas assez de données (min 5 valeurs par feature)"
    }
  }
}
```

### Champs par Feature

| Champ | Type | Description |
|-------|------|-------------|
| `status` | string | "ok" ou "skipped" |
| `n_ref` | int | Nombre de valeurs de référence |
| `n_cur` | int | Nombre de valeurs actuelles |
| `ks_stat` | float | Statistique D calculée |
| `ks_crit` | float | Seuil critique D_crit |
| `drift_detected` | bool | D > D_crit |

---

## 5. Exemples d'utilisation

### Python

```python
from app.services.data_drift import detect_data_drift

reference = {
    "temperature": [20.1, 20.5, 21.0, 21.2, 21.8, 22.0, 22.5, 23.0, 23.5, 24.0],
    "humidity": [45, 46, 47, 48, 49, 50, 51, 52, 53, 54]
}

current = {
    "temperature": [25.0, 25.5, 26.0, 26.5, 27.0, 27.5, 28.0, 28.5, 29.0, 29.5],
    "humidity": [44, 45, 46, 47, 48, 49, 50, 51, 52, 53]
}

result = detect_data_drift(reference, current, alpha=0.05)
# result["global_drift"] = True (température a drifté)
```

### Via cURL

```bash
curl -X POST http://localhost:8000/drift-data \
  -H "Content-Type: application/json" \
  -d '{
    "reference": {
      "temperature": [20.1, 20.5, 21.0, 21.2, 21.8, 22.0, 22.5, 23.0, 23.5, 24.0],
      "humidity": [45, 46, 47, 48, 49, 50, 51, 52, 53, 54]
    },
    "current": {
      "temperature": [25.0, 25.5, 26.0, 26.5, 27.0, 27.5, 28.0, 28.5, 29.0, 29.5],
      "humidity": [44, 45, 46, 47, 48, 49, 50, 51, 52, 53]
    },
    "alpha": 0.05
  }'
```

---

## 6. Diagramme de Flux

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT                                     │
│  reference: {feat1: [...], feat2: [...]}                    │
│  current:   {feat1: [...], feat2: [...]}                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Pour chaque feature commune                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────┐             ┌─────────────────┐
│ n < 5 ou m < 5  │             │ n >= 5 et m >= 5│
│    ⬇️ SKIP      │             │                 │
└─────────────────┘             └────────┬────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │ Calcul KS stat  │
                                │ D = max|CDF|    │
                                └────────┬────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │ Calcul D_crit   │
                                │ = c(α) × √...   │
                                └────────┬────────┘
                                         │
                         ┌───────────────┴───────────────┐
                         ▼                               ▼
                ┌─────────────────┐             ┌─────────────────┐
                │   D <= D_crit   │             │   D > D_crit    │
                │   NO DRIFT      │             │   DRIFT ⚠️      │
                └─────────────────┘             └─────────────────┘
```

---

## 7. Tests

**Fichier** : `tests/test_data_drift.py`

```bash
python -m pytest tests/test_data_drift.py -v
```

### Couverture des tests

| Catégorie | Tests |
|-----------|-------|
| Pas de drift | 3 tests |
| Drift détecté | 3 tests |
| Multi-features | 3 tests |
| Cas limites | 5 tests |
| Valeurs alpha | 3 tests |
| Structure de sortie | 3 tests |
| **Total** | **~20 tests** |

---

## 8. Contraintes

- Minimum **5 valeurs** par feature pour exécuter le test
- Features comparées = **intersection** des clés reference/current
- Features absentes d'un côté sont ignorées
