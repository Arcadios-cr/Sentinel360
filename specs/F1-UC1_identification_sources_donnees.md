# F1-UC1 : Identification des Sources de Données

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 8 mars 2026

---

## 1. Description

Cette feature identifie et structure les sources de données utilisées par Sentinel360 pour l'évaluation des modèles IA. Elle couvre :
- Les **données capteurs** (ClimaTrack)
- Les **prédictions** des modèles IA
- Le **format** et la **structure** des fichiers

---

## 2. Sources de Données Identifiées

### 2.1 Capteurs ClimaTrack

Les capteurs ClimaTrack collectent des mesures environnementales en temps réel.

| Champ | Type | Unité | Description |
|-------|------|-------|-------------|
| `timestamp` | ISO 8601 | - | Date/heure de la mesure |
| `ID` | string | - | Identifiant du capteur |
| `type` | string | - | Type de capteur ("ClimaTrack") |
| `temperature` | float | °C | Température ambiante |
| `humidity` | float | % | Humidité relative |
| `TVOC` | float | ppb | Composés organiques volatils |
| `CO2` | float | ppm | Concentration CO2 |
| `PM1.0` | float | µg/m³ | Particules fines < 1µm |
| `PM2.5` | float | µg/m³ | Particules fines < 2.5µm |
| `PM10` | float | µg/m³ | Particules < 10µm |
| `sound_level` | float | dB | Niveau sonore |

### 2.2 Prédictions du Modèle IA

Le modèle ClimaTrack prédit l'**humidex** (indice de confort thermique) à partir de :
- `temperature` (entrée)
- `humidity` (entrée)
- `humidex` (sortie prédite)

---

## 3. Format des Fichiers

### 3.1 Format NDJSON

Les données sont stockées au format **NDJSON** (Newline Delimited JSON) :
- Un objet JSON par ligne
- Pas de tableau englobant
- Facilite le streaming et le traitement ligne par ligne

**Exemple :**
```json
{"timestamp":"2026-01-05T10:52:41+0100","ID":"20240313101500","type":"ClimaTrack","temperature":"20.85","humidity":"21.21","TVOC":"136.00","CO2":"607.00"}
{"timestamp":"2026-01-05T10:57:46+0100","ID":"20240313101500","type":"ClimaTrack","temperature":"20.77","humidity":"21.32","TVOC":"86.00","CO2":"526.00"}
```

### 3.2 Convention de Nommage

| Pattern | Description | Exemple |
|---------|-------------|---------|
| `merged_data_YYYY-MM-DD.json` | Données capteurs brutes | `merged_data_2026-01-05.json` |
| `cleaned_merged_data_*.json` | Données nettoyées | `cleaned_merged_data_2026-01-05.json` |

---

## 4. Emplacements des Données

### 4.1 Structure des Dossiers

```
Sentinel360/
├── data/                              # Données du projet
│   ├── merged_data_2026-01-05.json   # Données brutes
│   ├── merged_data_2026-01-06.json
│   ├── merged_data_2026-01-07.json
│   └── cleaned/                       # Données nettoyées
│       └── cleaned_merged_data_*.json
│
├── IA modele/                         # Modèle client (externe)
│   └── Prédictions/
│       └── merged_data_*.json
│
└── app/data/                          # Données internes API
    ├── evals_model_A.json            # Historique évaluations
    ├── evals_model_B.json
    └── schedules.json                 # Planifications
```

### 4.2 Chemins Configurés

| Variable | Chemin | Description |
|----------|--------|-------------|
| `DATA_DIR` | `data/` | Données capteurs |
| `CLEANED_DIR` | `data/cleaned/` | Données nettoyées |
| `IA_MODEL_DIR` | `IA modele/Prédictions/` | Données modèle client |
| `APP_DATA_DIR` | `app/data/` | Historique et config |

---

## 5. API - Accès aux Données

### 5.1 Liste des fichiers disponibles

```http
GET /data/files
```

**Réponse :**
```json
{
  "files": [
    "merged_data_2026-01-05.json",
    "merged_data_2026-01-06.json",
    "merged_data_2026-01-07.json"
  ],
  "count": 3
}
```

### 5.2 Prévisualisation d'un fichier

```http
POST /data/preview
{
  "filename": "merged_data_2026-01-05.json"
}
```

**Réponse :**
```json
{
  "filename": "merged_data_2026-01-05.json",
  "total_records": 156,
  "columns": ["timestamp", "ID", "type", "temperature", "humidity", "TVOC", "CO2", "PM1.0", "PM2.5", "PM10", "sound_level"],
  "sample": [...],
  "statistics": {
    "temperature": {"min": 19.5, "max": 25.2, "mean": 21.8},
    "humidity": {"min": 18.0, "max": 35.5, "mean": 24.2}
  }
}
```

---

## 6. Validation des Données

### 6.1 Critères de Validité

| Champ | Validation | Action si invalide |
|-------|------------|-------------------|
| `timestamp` | Format ISO 8601 | Rejet de la ligne |
| `temperature` | Numérique, > -50, < 60 | Valeur ignorée |
| `humidity` | Numérique, 0-100 | Valeur ignorée |
| `CO2` | Numérique, > 0 | Valeur ignorée |
| Valeurs `nan` | Détection string "nan" | Conversion en null |

### 6.2 Gestion des Valeurs Manquantes

Les valeurs `"nan"` (string) sont converties en `null` lors du nettoyage (F1-UC2).

---

## 7. Intégration avec Sentinel360

### 7.1 Flux de Données

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Capteurs        │────►│ Fichiers NDJSON │────►│ Sentinel360     │
│ ClimaTrack      │     │ merged_data_*   │     │ API             │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌─────────────────┐              │
                        │ Modèle IA       │◄─────────────┘
                        │ (Prédictions)   │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ Évaluation      │
                        │ (Métriques)     │
                        └─────────────────┘
```

### 7.2 Utilisation dans l'Évaluation

1. **Chargement** : `load_climatrack_data(file_path)`
2. **Nettoyage** : `clean_data(records)` (F1-UC2)
3. **Extraction** : température, humidité → X
4. **Calcul humidex réel** : formule météo → y_true
5. **Prédiction** : modèle LinearRegression → y_pred
6. **Évaluation** : `/evaluate` → score, métriques, drift

---

## 8. Dashboard - Sélection des Données

Dans le dashboard (onglet **🧪 Évaluation > ClimaTrack**) :

1. **Sélection du fichier** via dropdown
2. **Aperçu** du nombre d'enregistrements
3. **Évaluation** en un clic

Les fichiers sont automatiquement découverts dans :
- `data/merged_data_*.json`
- `IA modele/Prédictions/merged_data_*.json`

---

## 9. Extensibilité

### 9.1 Ajouter une Nouvelle Source

Pour intégrer une nouvelle source de données :

1. **Créer un loader** dans `scripts/` :
   ```python
   def load_new_source_data(file_path):
       # Charger et parser les données
       return records
   ```

2. **Adapter le format** vers le schéma standard :
   ```python
   {
       "timestamp": "...",
       "feature1": value,
       "feature2": value,
       ...
   }
   ```

3. **Intégrer** dans le dashboard ou créer un script d'évaluation dédié.

### 9.2 Formats Supportés

| Format | Support | Module |
|--------|---------|--------|
| NDJSON | ✅ Natif | `json` |
| CSV | 🔄 À ajouter | `pandas` |
| Parquet | 🔄 À ajouter | `pyarrow` |
| API externe | 🔄 À ajouter | `requests` |
