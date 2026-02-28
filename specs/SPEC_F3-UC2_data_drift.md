# F3-UC2 : Reconnaissance des Dérives Statistiques (Data Drift)

> **Statut** : 🔄 En cours  
> **Version** : 0.9  
> **Date** : 21 février 2026

---

## 1. Objectif

Détecter automatiquement les changements de distribution des données d'entrée (features) entre une période de référence et la période actuelle, via le test statistique de Kolmogorov-Smirnov (KS).

---

## 2. État Actuel

### ✅ Implémenté

| Composant | Description |
|-----------|-------------|
| Test KS 2 échantillons | Implémentation manuelle sans dépendances |
| Endpoint API | `POST /drift-data` |
| Analyse multi-features | Comparaison de plusieurs features simultanément |
| Seuil dynamique | D_crit calculé selon taille des échantillons |

### 🔄 En cours / À faire

| Composant | Description | Priorité |
|-----------|-------------|----------|
| Données de référence persistantes | Stocker un jeu de référence par modèle | Haute |
| Tests supplémentaires | Chi², PSI (Population Stability Index) | Moyenne |
| Analyse automatique | Drift sur données des schedules | Haute |
| Visualisation | Graphiques de comparaison des distributions | Moyenne |

---

## 3. Spécification Technique

### 3.1 Test de Kolmogorov-Smirnov

Le test KS compare les fonctions de distribution cumulative (CDF) de deux échantillons.

**Hypothèses :**
- **H0** : Les deux échantillons proviennent de la même distribution
- **H1** : Les distributions sont différentes

**Statistique KS :**
```
D = max |F_ref(x) - F_cur(x)|
```

**Seuil critique :**
```
D_crit = c(α) × √((n + m) / (n × m))
```

Où :
- `n` = taille de l'échantillon de référence
- `m` = taille de l'échantillon courant
- `c(α)` = constante selon le niveau de confiance

| Alpha (α) | c(α) |
|-----------|------|
| 0.05 | 1.36 |
| 0.01 | 1.63 |

**Décision :** Si `D > D_crit` → Drift détecté

---

### 3.2 Paramètres

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `reference` | Dict[str, List[float]] | - | Features de référence |
| `current` | Dict[str, List[float]] | - | Features actuelles |
| `alpha` | float | 0.05 | Niveau de significativité |

### 3.3 Contraintes

- Minimum 5 valeurs par feature pour le test
- Features comparées = intersection des clés reference/current

---

## 4. Structure de Sortie

### Réponse API

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

## 5. Implémentation Actuelle

**Fichier** : `app/services/data_drift.py`

```python
def _ks_statistic(x: List[float], y: List[float]) -> float:
    """Calcule la statistique KS entre deux échantillons."""
    x_sorted = sorted(x)
    y_sorted = sorted(y)
    n, m = len(x_sorted), len(y_sorted)
    
    i, j = 0, 0
    cdf_x, cdf_y = 0.0, 0.0
    d = 0.0

    while i < n and j < m:
        if x_sorted[i] <= y_sorted[j]:
            i += 1
            cdf_x = i / n
        else:
            j += 1
            cdf_y = j / m
        d = max(d, abs(cdf_x - cdf_y))
    
    # Parcourir les éléments restants
    while i < n:
        i += 1
        cdf_x = i / n
        d = max(d, abs(cdf_x - cdf_y))
    while j < m:
        j += 1
        cdf_y = j / m
        d = max(d, abs(cdf_x - cdf_y))

    return d


def detect_data_drift(reference, current, alpha=0.05) -> Dict:
    c_alpha = 1.36 if alpha == 0.05 else 1.63 if alpha == 0.01 else 1.36
    
    feature_results = {}
    for feat in common_features:
        ref_vals = reference[feat]
        cur_vals = current[feat]
        
        if len(ref_vals) < 5 or len(cur_vals) < 5:
            feature_results[feat] = {"status": "skipped"}
            continue
        
        d = _ks_statistic(ref_vals, cur_vals)
        d_crit = c_alpha * math.sqrt((n + m) / (n * m))
        
        feature_results[feat] = {
            "ks_stat": d,
            "ks_crit": d_crit,
            "drift_detected": d > d_crit
        }
    
    return {"feature_results": feature_results}
```

---

## 6. Évolutions Prévues

### 6.1 Données de Référence Persistantes (Priorité Haute)

**Objectif** : Stocker un jeu de données de référence (Golden Set) par modèle.

**Endpoints proposés** :
```http
POST /models/{model_id}/reference-data
PUT /models/{model_id}/reference-data
GET /models/{model_id}/reference-data
```

**Stockage** : `app/data/reference_{model_id}.json`

### 6.2 Analyse Automatique (Priorité Haute)

**Objectif** : Exécuter l'analyse de drift automatiquement lors des évaluations planifiées.

**Intégration avec le scheduler** :
1. Le schedule stocke les données de référence initiales
2. À chaque exécution, comparer les nouvelles données à la référence
3. Inclure le résultat du data drift dans le rapport d'évaluation

### 6.3 Tests Supplémentaires (Priorité Moyenne)

| Test | Cas d'usage |
|------|-------------|
| Chi² | Variables catégorielles |
| PSI (Population Stability Index) | Scoring de crédit, assurance |
| Jensen-Shannon Divergence | Mesure symétrique de divergence |

### 6.4 Visualisation (Priorité Moyenne)

**Graphiques proposés** :
- Histogrammes superposés (référence vs actuel)
- Courbes CDF comparatives
- Heatmap de drift par feature et par période

---

## 7. Diagramme de Flux

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

## 8. Exemple d'Utilisation

### Requête API

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

## 9. Critères d'Acceptation

### MVP (Actuel)
- [x] Test KS 2 échantillons implémenté
- [x] Endpoint `/drift-data` fonctionnel
- [x] Analyse multi-features
- [x] Seuil critique dynamique

### Lot 1 (En cours)
- [ ] Stockage des données de référence par modèle
- [ ] Intégration automatique avec le scheduler
- [ ] Inclusion du data drift dans les rapports d'évaluation

### Lot 2 (Futur)
- [ ] Tests statistiques supplémentaires (Chi², PSI)
- [ ] Visualisation des distributions
- [ ] Alertes sur drift de données
