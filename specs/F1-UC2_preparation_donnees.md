# F1-UC2 : Préparation et Nettoyage des Données

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 21 février 2026

---

## 1. Description

Ce service assure la préparation et le nettoyage des données brutes provenant des capteurs environnementaux (ClimaTrack) avant leur utilisation pour l'évaluation des modèles prédictifs.

---

## 2. Architecture

### Module
- **Fichier** : `app/services/data_cleaning.py`
- **Classe** : `DataCleaningService`

### Endpoints API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/data/files` | Liste les fichiers de données disponibles |
| `POST` | `/data/preview` | Prévisualise un fichier avec statistiques |
| `POST` | `/data/clean` | Nettoie un fichier de données |
| `POST` | `/data/clean-all` | Nettoie tous les fichiers du dossier data |

---

## 3. Pipeline de Nettoyage

Le nettoyage s'effectue en 5 étapes séquentielles :

```
┌─────────────────┐
│ 1. Chargement   │ ──► Détection auto JSON/NDJSON
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. Conversion   │ ──► Strings → Float/Int/Datetime
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. Doublons     │ ──► Suppression par clés (timestamp + ID)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. Manquants    │ ──► Remove ou Fill (mean/median/zero)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. Validation   │ ──► Vérification des plages + Outliers (optionnel)
└─────────────────┘
```

---

## 4. Configuration

### Options de nettoyage

```json
{
  "remove_duplicates": true,
  "duplicate_keys": ["timestamp", "ID"],
  "missing_strategy": "fill",
  "numeric_strategy": "median",
  "validate_ranges": true,
  "remove_outliers": false,
  "outlier_method": "iqr"
}
```

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `remove_duplicates` | bool | `true` | Activer la suppression des doublons |
| `duplicate_keys` | list | `["timestamp", "ID"]` | Colonnes pour identifier les doublons |
| `missing_strategy` | str | `"fill"` | Stratégie : `"remove"` ou `"fill"` |
| `numeric_strategy` | str | `"median"` | Pour fill : `"mean"`, `"median"`, `"zero"` |
| `validate_ranges` | bool | `true` | Valider les plages de valeurs |
| `remove_outliers` | bool | `false` | Supprimer les valeurs aberrantes |
| `outlier_method` | str | `"iqr"` | Méthode : `"iqr"` ou `"zscore"` |

---

## 5. Schéma de Données (ClimaTrack)

### Types de colonnes

| Colonne | Type | Description |
|---------|------|-------------|
| `timestamp` | datetime | Horodatage de la mesure |
| `ID` | str | Identifiant du capteur |
| `type` | str | Type de capteur |
| `temperature` | float | Température en °C |
| `humidity` | float | Humidité relative en % |
| `TVOC` | float | Composés organiques volatils (ppb) |
| `CO2` | float | Dioxyde de carbone (ppm) |
| `PM1.0` | float | Particules fines ≤1µm (µg/m³) |
| `PM2.5` | float | Particules fines ≤2.5µm (µg/m³) |
| `PM10` | float | Particules ≤10µm (µg/m³) |
| `sound_level` | float | Niveau sonore (dB) |

### Plages de validation

| Colonne | Minimum | Maximum | Unité |
|---------|---------|---------|-------|
| `temperature` | -40.0 | 60.0 | °C |
| `humidity` | 0.0 | 100.0 | % |
| `TVOC` | 0.0 | 60000.0 | ppb |
| `CO2` | 0.0 | 10000.0 | ppm |
| `PM1.0` | 0.0 | 1000.0 | µg/m³ |
| `PM2.5` | 0.0 | 1000.0 | µg/m³ |
| `PM10` | 0.0 | 1000.0 | µg/m³ |
| `sound_level` | 0.0 | 150.0 | dB |

---

## 6. Exemples d'utilisation

### Via API

**Nettoyer un fichier :**
```bash
curl -X POST http://localhost:8000/data/clean \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "merged_data_2026-01-05.json",
    "config": {
      "remove_duplicates": true,
      "missing_strategy": "fill",
      "numeric_strategy": "median"
    }
  }'
```

**Réponse :**
```json
{
  "filename": "merged_data_2026-01-05.json",
  "original_count": 156,
  "final_count": 156,
  "total_removed": 0,
  "removal_percentage": 0.0,
  "steps": [
    {"step": "convert_types", "schema_applied": ["temperature", "humidity", "CO2"]},
    {"step": "remove_duplicates", "duplicates_removed": 0},
    {"step": "handle_missing_values", "strategy": "fill", "remaining": 156},
    {"step": "validate_ranges", "stats": {"valid": 156, "invalid": 0}}
  ],
  "statistics": {
    "temperature": {"count": 156, "min": 20.77, "max": 24.46, "mean": 22.9, "median": 22.84}
  },
  "output_file": "data/cleaned/cleaned_merged_data_2026-01-05.json"
}
```

### Via Python

```python
from app.services.data_cleaning import data_cleaning_service

# Nettoyer un fichier avec configuration personnalisée
report = data_cleaning_service.clean_dataset(
    filename="merged_data_2026-01-05.json",
    config={
        "remove_duplicates": True,
        "missing_strategy": "fill",
        "numeric_strategy": "median",
        "validate_ranges": True
    }
)

print(f"Lignes originales: {report['original_count']}")
print(f"Lignes finales: {report['final_count']}")
print(f"Fichier nettoyé: {report['output_file']}")
```

---

## 7. Sortie

Les fichiers nettoyés sont sauvegardés dans `data/cleaned/` avec le préfixe `cleaned_`.

**Structure des dossiers :**
```
data/
├── merged_data_2026-01-05.json      # Données brutes
├── merged_data_2026-01-06.json
└── cleaned/
    └── cleaned_merged_data_2026-01-05.json  # Données nettoyées
```

---

## 8. Tests

**Fichier** : `tests/test_data_cleaning.py`  
**Nombre de tests** : 35

Exécution :
```bash
python -m pytest tests/test_data_cleaning.py -v
```
