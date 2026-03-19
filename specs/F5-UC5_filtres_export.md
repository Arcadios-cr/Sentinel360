# F5-UC5 : Filtres Avancés et Export des Données

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 12 mars 2026

---

## 1. Description

Page du dashboard permettant d'appliquer des **filtres avancés multi-modèles** (dates, scores, drift) et d'**exporter les données** dans plusieurs formats (CSV, JSON, rapport texte) pour analyse externe ou archivage.

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `dashboard/app.py` | Page `page_advanced()` (« 🔎 Filtres & Export ») |

> **Note** : Cette feature est une fonctionnalité purement dashboard, elle n'a pas de service backend dédié. Elle utilise les endpoints API existants (`GET /models`, `GET /models/{id}/evaluations`).

---

## 3. Filtres Disponibles

### 3.1 Filtres dans la Barre Latérale

| Filtre | Type | Description |
|--------|------|-------------|
| **Modèles** | Multiselect | Sélection d'un ou plusieurs modèles |
| **Période** | Date range | Plage de dates (début → fin) |
| **Score minimum** | Slider | Score minimum (0-100) |
| **Score maximum** | Slider | Score maximum (0-100) |
| **Drift** | Selectbox | Filtrer par sévérité de drift (Tous / low / medium / high) |

### 3.2 Application des Filtres

Les filtres sont appliqués côté client sur les données récupérées via l'API :
1. Récupération des évaluations de chaque modèle sélectionné
2. Filtrage par date
3. Filtrage par plage de score
4. Filtrage par sévérité de drift

---

## 4. Visualisation

### 4.1 Tableau Filtré

- **Colonnes** : Modèle, Date, Score, MAE, RMSE, R², MSE, Drift (sévérité)
- **Tri** : Par date décroissante
- **KPI** : Nombre de résultats après filtrage

### 4.2 Graphique d'Évolution Multi-Modèles

- **Type** : Courbes (line chart Plotly)
- **Axe X** : Temps (dates des évaluations)
- **Axe Y** : Score (0-100)
- **Légende** : Une courbe par modèle sélectionné
- **Interactivité** : Zoom, pan, export PNG

---

## 5. Export

### 5.1 Formats Disponibles

| Format | Bouton | Contenu |
|--------|--------|---------|
| **CSV** | 📥 Télécharger CSV | Tableau filtré au format CSV (colonnes séparées par virgules) |
| **JSON** | 📥 Télécharger JSON | Données brutes au format JSON (array d'objets) |
| **Rapport TXT** | 📄 Générer rapport | Rapport structuré texte avec en-tête, résumé et détails |

### 5.2 Structure du Rapport TXT

```
RAPPORT SENTINEL360
Généré le 2026-03-12 14:30:00
Période : 2026-01-01 → 2026-03-12
Modèles : climatrack, air_quality_v1

============================================================
RÉSUMÉ
============================================================
Nombre d'évaluations : 45
Score moyen : 82.3

============================================================
DÉTAIL PAR ÉVALUATION
============================================================
[2026-03-12] climatrack — Score: 85 | MAE: 0.08 | RMSE: 0.12 | R²: 0.95 | Drift: low
[2026-03-11] climatrack — Score: 83 | MAE: 0.09 | RMSE: 0.13 | R²: 0.94 | Drift: low
...
```

---

## 6. Dashboard

### Navigation

Page accessible via la barre latérale : **« 🔎 Filtres & Export »**

### Interface

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar                │  Main Content                     │
│  ├─ Sélection modèles   │  ┌─ KPIs (nb résultats)         │
│  ├─ Date début/fin       │  ├─ Tableau filtré              │
│  ├─ Score min/max        │  ├─ Graphique évolution         │
│  └─ Filtre drift         │  └─ Boutons export              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Tests

Cette feature est une fonctionnalité d'interface (Streamlit). La validation se fait manuellement via le dashboard.

Les données sous-jacentes sont validées par les tests des endpoints API :
- `tests/test_compare_models.py` — Tests de listing et comparaison
- `tests/test_alerts.py` — Tests des alertes et filtrage

---

## 8. Dépendances

| Package | Usage |
|---------|-------|
| `streamlit` | Interface utilisateur |
| `plotly` | Graphiques interactifs |
| `io` / `base64` | Génération des fichiers téléchargeables |
| `json` / `csv` | Sérialisation des exports |
