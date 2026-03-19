# F1-UC3 : Construction d'un Dataset de Référence (Golden Set)

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 12 mars 2026

---

## 1. Description

Ce service permet de construire et maintenir un **dataset de référence** (« Golden Set ») pour chaque modèle, servant de base de comparaison pour :
- La détection de data drift (comparaison distribution actuelle vs. référence)
- Le benchmark des performances
- L'audit et la traçabilité des données

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `app/services/reference_dataset.py` | CRUD complet du Golden Set + calcul de statistiques |
| `app/main.py` | Endpoints REST (POST, GET, DELETE, LIST) |
| `app/schemas.py` | Schéma `ReferenceDatasetRequest` |
| `tests/test_reference_dataset.py` | 13 tests unitaires |

### Stockage

Les golden sets sont persistés en fichiers JSON dans `app/data/` :

```
app/data/
├── reference_climatrack_humidex_v1.json
├── reference_air_quality_v1.json
└── reference_model_A.json
```

---

## 3. Fonctions du Service

### `create_reference_dataset(model_id, features, description, version)`

Crée ou remplace le golden set d'un modèle.

- **Validation** : au minimum 5 valeurs par feature, dictionnaire non vide
- **Calcul automatique** : statistiques descriptives (min, max, mean, std, median) par feature
- **Persistance** : fichier `reference_{model_id}.json`

### `get_reference_dataset(model_id)`

Récupère le golden set complet (données + métadonnées + statistiques).

### `get_reference_features(model_id)`

Récupère uniquement les features (pour utilisation directe dans le data drift).

### `delete_reference_dataset(model_id)`

Supprime le golden set d'un modèle.

### `list_reference_datasets()`

Liste tous les golden sets disponibles avec leurs métadonnées.

### `_compute_feature_stats(values)`

Calcule les statistiques descriptives d'une feature : count, min, max, mean, std, median.

---

## 4. Format du Golden Set

```json
{
  "model_id": "climatrack_humidex_v1",
  "created_at": "2026-03-12T10:00:00Z",
  "updated_at": "2026-03-12T10:00:00Z",
  "version": "1.0",
  "description": "Dataset de référence initial",
  "features": {
    "temperature": [20.1, 20.5, 21.0, 21.5, 22.0],
    "humidity": [45.0, 46.2, 47.5, 48.1, 49.0]
  },
  "statistics": {
    "temperature": {"count": 5, "min": 20.1, "max": 22.0, "mean": 21.02, "std": 0.697, "median": 21.0},
    "humidity": {"count": 5, "min": 45.0, "max": 49.0, "mean": 47.16, "std": 1.445, "median": 47.5}
  },
  "n_samples": 5,
  "n_features": 2
}
```

---

## 5. API Endpoints

### POST `/models/{model_id}/reference`

Crée ou remplace le golden set d'un modèle.

**Request :**
```bash
curl -X POST http://localhost:8000/models/climatrack/reference \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "temperature": [20.1, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0],
      "humidity": [45.0, 46.2, 47.5, 48.1, 49.0, 50.2, 51.0]
    },
    "description": "Données de janvier 2026",
    "version": "1.0"
  }'
```

**Response 200 :**
```json
{
  "model_id": "climatrack",
  "version": "1.0",
  "n_samples": 7,
  "n_features": 2,
  "features": ["temperature", "humidity"],
  "statistics": { "..." },
  "created_at": "2026-03-12T10:00:00Z"
}
```

### GET `/models/{model_id}/reference`

Récupère le golden set complet.

**Response 200 :** Golden set avec données, statistiques et métadonnées.  
**Response 404 :** `{"detail": "Aucun dataset de référence pour {model_id}"}`

### DELETE `/models/{model_id}/reference`

Supprime le golden set.

**Response 200 :** `{"message": "Dataset de référence supprimé", "model_id": "..."}`  
**Response 404 :** `{"detail": "Aucun dataset de référence pour {model_id}"}`

### GET `/references`

Liste tous les golden sets disponibles.

**Response 200 :**
```json
{
  "total": 2,
  "references": [
    {"model_id": "climatrack", "version": "1.0", "n_samples": 500, "n_features": 3}
  ]
}
```

### POST `/models/{model_id}/drift-data`

Analyse le data drift en utilisant automatiquement le golden set comme référence.

**Request :**
```json
{
  "current": {"temperature": [25, 26, 27, 28, 29, 30]},
  "alpha": 0.05
}
```

**Response 200 :** Résultat de l'analyse data drift avec comparaison au golden set.

---

## 6. Tests

**Fichier** : `tests/test_reference_dataset.py` — **13 tests**

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestReferenceDataset` | 10 | CRUD, validation, listing, overwrite |
| `TestFeatureStatistics` | 3 | Calcul de stats, cas limites |

### Commande

```bash
python -m pytest tests/test_reference_dataset.py -v
```

---

## 7. Intégration

- **Data Drift** : L'endpoint `POST /models/{id}/drift-data` utilise automatiquement le golden set comme distribution de référence
- **Dashboard** : Les golden sets sont accessibles via l'API pour la page d'interprétation
- **Évaluation** : L'endpoint `POST /models/{id}/evaluate` peut charger les seuils du modèle associés au golden set
