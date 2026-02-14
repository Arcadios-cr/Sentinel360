# F2-UC1 : Calcul des Métriques d'Erreur Standards

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 21 février 2026

---

## 1. Description

Ce service calcule les métriques d'erreur standards permettant d'évaluer la qualité des prédictions d'un modèle d'IA. Ces indicateurs mesurent l'écart entre les valeurs réelles (`y_true`) et les valeurs prédites (`y_pred`).

---

## 2. Architecture

### Module
- **Fichier** : `app/services/metrics.py`
- **Fonction** : `compute_metrics(y_true, y_pred)`

### Dépendances
- `math` (bibliothèque standard Python)

---

## 3. Métriques Calculées

| Métrique | Nom Complet | Formule | Interprétation |
|----------|-------------|---------|----------------|
| **MAE** | Mean Absolute Error | $\frac{1}{n}\sum_{i=1}^{n}\vert y_i - \hat{y}_i \vert$ | Erreur moyenne absolue |
| **MSE** | Mean Squared Error | $\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2$ | Erreur quadratique moyenne |
| **RMSE** | Root Mean Squared Error | $\sqrt{MSE}$ | Racine de l'erreur quadratique |
| **R²** | Coefficient de détermination | $1 - \frac{SS_{res}}{SS_{tot}}$ | Qualité de l'ajustement (0-1) |

### Détail des calculs

#### MAE (Mean Absolute Error)
- Mesure l'erreur moyenne en valeur absolue
- Robuste aux valeurs aberrantes
- Même unité que les données

#### MSE (Mean Squared Error)
- Pénalise davantage les grandes erreurs (quadratique)
- Sensible aux outliers
- Unité au carré

#### RMSE (Root Mean Squared Error)
- Racine carrée du MSE
- Même unité que les données originales
- Utilisé comme référence pour la détection de drift

#### R² (Coefficient de détermination)
- Mesure la proportion de variance expliquée
- **R² = 1** : Prédiction parfaite
- **R² = 0** : Modèle équivalent à la moyenne
- **R² < 0** : Modèle pire que la moyenne

---

## 4. API Endpoint

### Évaluation complète

```http
POST /evaluate
Content-Type: application/json
```

**Request Body :**
```json
{
  "y_true": [1.0, 2.0, 3.0, 4.0, 5.0],
  "y_pred": [1.1, 2.2, 2.9, 4.1, 4.8],
  "baseline_rmse": 0.2
}
```

**Response 200 :**
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
    "severity": "low",
    "drift_detected": false
  },
  "score": 100
}
```

---

## 5. Validation des Entrées

| Règle | Description |
|-------|-------------|
| Taille identique | `y_true` et `y_pred` doivent avoir le même nombre d'éléments |
| Non vide | Les listes ne doivent pas être vides |
| Type numérique | Toutes les valeurs doivent être des floats |

### Erreurs possibles

| Erreur | Message |
|--------|---------|
| Tailles différentes | `y_true et y_pred doivent avoir la même taille` |
| Liste vide | `Les listes ne doivent pas être vides` |

---

## 6. Exemples d'utilisation

### Via API

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "y_true": [10.0, 20.0, 30.0, 40.0, 50.0],
    "y_pred": [11.0, 19.0, 31.0, 39.0, 51.0],
    "baseline_rmse": 2.0
  }'
```

### Via Python

```python
from app.services.metrics import compute_metrics

# Données d'exemple
y_true = [10.0, 20.0, 30.0, 40.0, 50.0]
y_pred = [11.0, 19.0, 31.0, 39.0, 51.0]

# Calcul des métriques
result = compute_metrics(y_true, y_pred)

print(f"MAE: {result['mae']:.4f}")   # MAE: 1.0000
print(f"MSE: {result['mse']:.4f}")   # MSE: 1.0000
print(f"RMSE: {result['rmse']:.4f}") # RMSE: 1.0000
print(f"R²: {result['r2']:.4f}")     # R²: 0.9950
```

---

## 7. Cas de Référence

Les cas de référence suivants sont utilisés pour valider l'implémentation :

### Cas 1 : Prédiction parfaite
```python
y_true = [1.0, 2.0, 3.0, 4.0, 5.0]
y_pred = [1.0, 2.0, 3.0, 4.0, 5.0]
# Résultat : MAE=0, MSE=0, RMSE=0, R²=1
```

### Cas 2 : Erreur constante
```python
y_true = [10.0, 20.0, 30.0, 40.0, 50.0]
y_pred = [11.0, 21.0, 31.0, 41.0, 51.0]
# Résultat : MAE=1.0, MSE=1.0, RMSE=1.0, R²=0.995
```

### Cas 3 : Erreurs mixtes
```python
y_true = [3.0, 5.0, 2.0, 7.0]
y_pred = [2.0, 6.0, 3.0, 8.0]
# Résultat : MAE=1.0, MSE=1.0, RMSE=1.0, R²≈0.729
```

---

## 8. Tests

**Fichier** : `tests/test_metrics.py`  
**Nombre de tests** : 358 lignes de tests

### Exécution

```bash
python -m pytest tests/test_metrics.py -v
```

### Couverture des tests

| Catégorie | Description |
|-----------|-------------|
| Prédiction parfaite | Erreurs nulles |
| Erreur constante | Décalage uniforme |
| Erreurs mixtes | Positives et négatives |
| Valeurs décimales | Précision flottante |
| Cas limites | Listes vides, tailles différentes |
| Grande échelle | Nombreuses valeurs |

---

## 9. Intégration

Les métriques calculées sont utilisées par les modules suivants :

| Module | Utilisation |
|--------|-------------|
| `drift.py` | Comparaison du RMSE au baseline |
| `scoring.py` | Calcul du score de performance |
| `history.py` | Stockage dans l'historique |
| `scheduler.py` | Évaluations planifiées |
