# F5-UC3 : Tableau de Bord Synthétique

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 21 février 2026

---

## 1. Description

Le tableau de bord Sentinel360 est une interface web interactive permettant de visualiser les scores, métriques et tendances des modèles d'IA surveillés. Conçu avec Streamlit, il offre une expérience utilisateur moderne et intuitive pour le monitoring en temps réel.

---

## 2. Architecture

### Technologies

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Framework UI | Streamlit | 1.45.0 |
| Graphiques | Plotly | 6.0.1 |
| HTTP Client | Requests | 2.x |
| Data Processing | Pandas | 2.x |

### Fichiers

```
dashboard/
├── app.py              # Application principale
├── Dockerfile          # Image Docker
└── requirements.txt    # Dépendances
```

### Communication

```
┌─────────────────┐         HTTP         ┌─────────────────┐
│    Dashboard    │ ◄──────────────────► │    API FastAPI  │
│   (Streamlit)   │     localhost:8000   │                 │
│   Port: 8501    │                      │   Port: 8000    │
└─────────────────┘                      └─────────────────┘
```

### URLs d'Accès

| Environnement | URL |
|---------------|-----|
| Local | `http://localhost:8501` |
| Docker | `http://localhost:8501` |

---

## 3. Pages du Dashboard

### 3.1 🏠 Vue d'ensemble

**Contenu :**
- 4 KPI cards (modèles, score moyen, alertes, évaluations)
- Distribution des scores (histogramme)
- Top 5 des modèles (tableau)
- Alertes actives (liste)

**Maquette :**
```
┌─────────────────────────────────────────────────────────────┐
│  🛡️ Sentinel360 - Surveillance IA                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Modèles │  │ Score   │  │ Alertes │  │ Evals   │        │
│  │    5    │  │  87.2   │  │    2    │  │   156   │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                             │
│  ┌─────────────────────────┐  ┌────────────────────────┐   │
│  │  Distribution Scores    │  │  Top 5 Modèles         │   │
│  │  ██████████  90-100     │  │  1. model_A    92      │   │
│  │  ████████    80-89      │  │  2. model_B    87      │   │
│  │  ███         70-79      │  │  3. model_C    81      │   │
│  │  █           <70        │  │  ...                   │   │
│  └─────────────────────────┘  └────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 📈 Détail Modèle

**Fonctionnalités :**
- Sélection du modèle (dropdown)
- Période d'analyse (slider 7-90 jours)
- Score actuel et tendance
- Graphique d'évolution du score
- Graphique des métriques (MAE, RMSE, R²)
- Tableau des évaluations récentes

### 3.3 ⚖️ Comparaison

**Fonctionnalités :**
- Sélection multiple de modèles
- Tableau comparatif (scores, métriques)
- Graphique radar multi-dimensions
- Identification du meilleur modèle

### 3.4 ⏰ Planificateur

**Fonctionnalités :**
- Liste des tâches planifiées
- Statut (active/pause/terminé)
- Actions (pause, resume, supprimer, trigger)
- Formulaire de création

### 3.5 🧪 Évaluation Manuelle

**Fonctionnalités :**
- Formulaire de saisie (y_true, y_pred)
- Baseline RMSE optionnel
- Résultats instantanés
- Option de sauvegarde

---

## 4. Composants UI

### 4.1 KPI Cards

```python
def render_kpi_card(value, label, card_type="default"):
    """
    Affiche une carte KPI stylisée.
    
    card_type: "default", "success", "warning", "danger"
    """
    css_class = f"kpi-card kpi-card-{card_type}"
    st.markdown(f"""
        <div class="{css_class}">
            <p class="kpi-value">{value}</p>
            <p class="kpi-label">{label}</p>
        </div>
    """, unsafe_allow_html=True)
```

### 4.2 Styles CSS

```css
.kpi-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1.5rem;
    border-radius: 1rem;
    color: white;
    text-align: center;
}

.kpi-card-success {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.kpi-card-warning {
    background: linear-gradient(135deg, #F2994A 0%, #F2C94C 100%);
}

.kpi-card-danger {
    background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
}

.alert-high {
    background-color: #fee2e2;
    border-left: 4px solid #ef4444;
}

.alert-medium {
    background-color: #fef3c7;
    border-left: 4px solid #f59e0b;
}
```

### 4.3 Graphiques Plotly

**Évolution du Score :**
```python
fig = px.line(
    df, 
    x="timestamp", 
    y="score",
    title="Évolution du Score",
    markers=True
)
fig.update_layout(
    yaxis_range=[0, 100],
    hovermode="x unified"
)
```

**Graphique Radar (Comparaison) :**
```python
fig = go.Figure()
for model in models:
    fig.add_trace(go.Scatterpolar(
        r=[model.mae, model.rmse, model.r2, model.score],
        theta=["MAE", "RMSE", "R²", "Score"],
        fill='toself',
        name=model.id
    ))
```

---

## 5. Communication API

### 5.1 Configuration

```python
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
```

### 5.2 Fonctions Utilitaires

```python
@st.cache_data(ttl=30)
def fetch_api(endpoint: str, params: dict = None):
    """Appel GET avec cache de 30 secondes."""
    response = requests.get(f"{API_BASE_URL}{endpoint}", params=params)
    return response.json()

def post_api(endpoint: str, json_data: dict = None):
    """Appel POST sans cache."""
    response = requests.post(f"{API_BASE_URL}{endpoint}", json=json_data)
    return response.json()
```

### 5.3 Gestion des Erreurs

```python
def check_api_health():
    """Vérifie la disponibilité de l'API."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# Affichage conditionnel
if not check_api_health():
    st.error("⚠️ API non disponible. Vérifiez que le service est démarré.")
    st.stop()
```

---

## 6. Exemples d'utilisation

### Lancement Local

```bash
# Installation des dépendances
pip install -r dashboard/requirements.txt

# Lancement de l'application
cd dashboard
streamlit run app.py
```

### Lancement Docker

```bash
# Via docker-compose (avec l'API)
docker-compose up dashboard

# Image seule
docker build -t sentinel360-dashboard ./dashboard
docker run -p 8501:8501 -e API_BASE_URL=http://host.docker.internal:8000 sentinel360-dashboard
```

### Accès aux Pages

| Page | Navigation |
|------|------------|
| Vue d'ensemble | Sélectionner "🏠 Vue d'ensemble" dans le menu latéral |
| Détail Modèle | Sélectionner "📈 Détail Modèle" puis choisir un modèle |
| Comparaison | Sélectionner "⚖️ Comparaison" puis plusieurs modèles |
| Planificateur | Sélectionner "⏰ Planificateur" pour gérer les schedules |
| Évaluation | Sélectionner "🧪 Évaluation Manuelle" pour tester |

---

## 7. Déploiement

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### docker-compose.yml

```yaml
dashboard:
  build: ./dashboard
  ports:
    - "8501:8501"
  environment:
    - API_BASE_URL=http://api:8000
  depends_on:
    api:
      condition: service_healthy
```

---

## 8. Variables d'Environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | URL de l'API FastAPI |

---

## 9. Dépendances

**Fichier** : `dashboard/requirements.txt`

```
streamlit==1.45.0
plotly==6.0.1
requests>=2.0.0
pandas>=2.0.0
```

---

## 10. Tests

Pour tester manuellement le dashboard :

1. Démarrer l'API FastAPI sur le port 8000
2. Lancer le dashboard Streamlit
3. Vérifier chaque page du menu latéral
4. Tester les interactions (sélection de modèles, évaluations)

```bash
# Vérifier que l'API répond
curl http://localhost:8000/health

# Ouvrir le dashboard
streamlit run dashboard/app.py
```
