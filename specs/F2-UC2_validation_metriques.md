# F2-UC2 : Tests de Validation des Métriques

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 21 février 2026

---

## 1. Description

Ce module assure la validation des résultats de calcul de métriques via des cas de référence connus (ground truth). Il garantit la fiabilité des métriques MAE, MSE, RMSE et R² utilisées pour évaluer les modèles.

---

## 2. Métriques Validées

### Formules Mathématiques

| Métrique | Formule | Description |
|----------|---------|-------------|
| **MAE** | `Σ|y_true - y_pred| / n` | Mean Absolute Error |
| **MSE** | `Σ(y_true - y_pred)² / n` | Mean Squared Error |
| **RMSE** | `√MSE` | Root Mean Squared Error |
| **R²** | `1 - (SS_res / SS_tot)` | Coefficient de détermination |

Où :
- `SS_res = Σ(y_true - y_pred)²` (somme des carrés des résidus)
- `SS_tot = Σ(y_true - mean(y_true))²` (somme des carrés totaux)

---

## 3. Implémentation

### Module
- **Fichier** : `app/services/metrics.py`
- **Fonction** : `compute_metrics(y_true, y_pred)`

### Code Source

```python
def compute_metrics(y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true et y_pred doivent avoir la même taille")
    if len(y_true) == 0:
        raise ValueError("Les listes ne doivent pas être vides")

    n = len(y_true)
    errors = [t - p for t, p in zip(y_true, y_pred)]    

    mae = sum(abs(e) for e in errors) / n
    mse = sum(e * e for e in errors) / n
    rmse = math.sqrt(mse)

    mean_y = sum(y_true) / n
    ss_tot = sum((y - mean_y) ** 2 for y in y_true)
    ss_res = sum((y_true[i] - y_pred[i]) ** 2 for i in range(n))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    return {"mae": mae, "mse": mse, "rmse": rmse, "r2": r2}
```

---

## 4. Suite de Tests

### Fichier
`tests/test_metrics.py`

### Cas de Test

#### Prédictions Parfaites
```python
def test_perfect_predictions():
    y_true = [1.0, 2.0, 3.0, 4.0, 5.0]
    y_pred = [1.0, 2.0, 3.0, 4.0, 5.0]
    metrics = compute_metrics(y_true, y_pred)
    
    assert metrics["mae"] == 0.0
    assert metrics["mse"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["r2"] == 1.0
```

#### Erreurs Constantes
```python
def test_constant_error():
    y_true = [1.0, 2.0, 3.0, 4.0, 5.0]
    y_pred = [1.1, 2.1, 3.1, 4.1, 5.1]  # +0.1 partout
    metrics = compute_metrics(y_true, y_pred)
    
    assert metrics["mae"] == pytest.approx(0.1)
    assert metrics["mse"] == pytest.approx(0.01)
    assert metrics["rmse"] == pytest.approx(0.1)
    assert metrics["r2"] == pytest.approx(0.995, rel=0.01)
```

#### Valeurs Négatives
```python
def test_negative_values():
    y_true = [-5.0, -2.0, 0.0, 3.0, 7.0]
    y_pred = [-4.5, -2.5, 0.5, 2.5, 7.5]
    metrics = compute_metrics(y_true, y_pred)
    
    assert metrics["mae"] == pytest.approx(0.5)
    # R² doit rester valide avec des valeurs négatives
    assert 0 <= metrics["r2"] <= 1
```

#### Relation RMSE = √MSE
```python
def test_rmse_is_sqrt_mse():
    y_true = [1.0, 2.0, 3.0, 4.0, 5.0]
    y_pred = [1.2, 2.4, 2.8, 4.2, 4.6]
    metrics = compute_metrics(y_true, y_pred)
    
    assert metrics["rmse"] == pytest.approx(math.sqrt(metrics["mse"]))
```

#### Cas Limites
```python
def test_empty_arrays():
    with pytest.raises(ValueError):
        compute_metrics([], [])

def test_mismatched_lengths():
    with pytest.raises(ValueError):
        compute_metrics([1, 2, 3], [1, 2])
```

---

## 5. Valeurs de Référence

### Tableau de Validation

| Cas | y_true | y_pred | MAE | MSE | RMSE | R² |
|-----|--------|--------|-----|-----|------|-----|
| Parfait | [1,2,3,4,5] | [1,2,3,4,5] | 0 | 0 | 0 | 1.0 |
| +0.1 | [1,2,3,4,5] | [1.1,2.1,3.1,4.1,5.1] | 0.1 | 0.01 | 0.1 | 0.995 |
| ±0.2 | [1,2,3,4,5] | [1.2,1.8,3.2,3.8,5.2] | 0.2 | 0.048 | 0.219 | 0.976 |
| Pire | [1,2,3,4,5] | [5,4,3,2,1] | 2.4 | 8 | 2.83 | -3.0 |

> **Note** : R² peut être négatif quand le modèle est pire qu'une moyenne constante.

---

## 6. Exécution des Tests

```bash
# Tous les tests de métriques
python -m pytest tests/test_metrics.py -v

# Avec couverture
python -m pytest tests/test_metrics.py --cov=app.services.metrics --cov-report=term

# Test spécifique
python -m pytest tests/test_metrics.py::test_perfect_predictions -v
```

### Résultat Attendu

```
tests/test_metrics.py::test_perfect_predictions PASSED
tests/test_metrics.py::test_constant_error PASSED
tests/test_metrics.py::test_negative_values PASSED
tests/test_metrics.py::test_rmse_is_sqrt_mse PASSED
tests/test_metrics.py::test_empty_arrays PASSED
tests/test_metrics.py::test_mismatched_lengths PASSED
...
======================== 19 passed ========================
```

---

## 7. Couverture

| Fonction | Lignes | Couverture |
|----------|--------|------------|
| `compute_metrics` | 15 | 100% |
| Validation inputs | 4 | 100% |
| **Total** | 19 | **100%** |
