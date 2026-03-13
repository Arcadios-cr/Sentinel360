"""
Sentinel360 - Dashboard de Surveillance IA
F5-UC3 : Tableau de bord synthétique affichant scores et tendances

Interface interactive pour visualiser :
- Scores et métriques en temps réel
- Évolution temporelle des performances
- Ranking des modèles
- Alertes de drift
- Comparaison entre modèles
- Gestion des schedules
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import io
import base64

# =============================================================================
# CONFIGURATION
# =============================================================================

import os

# URL de l'API - configurable via variable d'environnement
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Sentinel360 - Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# STYLES CSS PERSONNALISÉS
# =============================================================================

st.markdown("""
<style>
    /* Style général */
    .main {
        padding: 1rem 2rem;
    }
    
    /* Cards KPI */
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
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
    
    .kpi-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    
    .kpi-label {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    /* Alertes */
    .alert-high {
        background-color: #fee2e2;
        border-left: 4px solid #ef4444;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
    
    .alert-medium {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
    
    /* Header */
    .dashboard-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        padding: 1.5rem 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        color: white;
    }
    
    .dashboard-title {
        font-size: 2rem;
        font-weight: bold;
        margin: 0;
    }
    
    .dashboard-subtitle {
        opacity: 0.8;
        margin-top: 0.5rem;
    }
    
    /* Tables */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #f8fafc;
    }
    
    /* Status badges */
    .status-active {
        background-color: #10b981;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.8rem;
    }
    
    .status-paused {
        background-color: #f59e0b;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.8rem;
    }
    
    .status-completed {
        background-color: #6b7280;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# FONCTIONS API
# =============================================================================

@st.cache_data(ttl=30)
def fetch_api(endpoint: str, params: dict = None):
    """Appel API avec cache de 30 secondes."""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur API: {e}")
        return None


def post_api(endpoint: str, json_data: dict = None):
    """Appel POST à l'API."""
    try:
        response = requests.post(f"{API_BASE_URL}{endpoint}", json=json_data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur API: {e}")
        return None


def delete_api(endpoint: str):
    """Appel DELETE à l'API."""
    try:
        response = requests.delete(f"{API_BASE_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur API: {e}")
        return None


def check_api_health():
    """Vérifie si l'API est accessible."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


# =============================================================================
# COMPOSANTS UI
# =============================================================================

def render_kpi_card(value, label, card_type="default", delta=None):
    """Affiche une carte KPI stylisée."""
    class_name = f"kpi-card kpi-card-{card_type}" if card_type != "default" else "kpi-card"
    
    delta_html = ""
    if delta is not None:
        delta_icon = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        delta_color = "#10b981" if delta > 0 else "#ef4444" if delta < 0 else "#6b7280"
        delta_html = f'<span style="color: {delta_color}; font-size: 0.9rem;"> {delta_icon} {abs(delta):.1f}%</span>'
    
    st.markdown(f"""
        <div class="{class_name}">
            <p class="kpi-value">{value}{delta_html}</p>
            <p class="kpi-label">{label}</p>
        </div>
    """, unsafe_allow_html=True)


def render_header():
    """Affiche l'en-tête du dashboard."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("""
            <div class="dashboard-header">
                <p class="dashboard-title">🛡️ Sentinel360</p>
                <p class="dashboard-subtitle">Tableau de Bord de Surveillance des Modèles IA</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        api_status = check_api_health()
        if api_status:
            st.success("🟢 API Connectée")
        else:
            st.error("🔴 API Déconnectée")
        
        if st.button("🔄 Rafraîchir", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


def render_drift_alert(model_id: str, severity: str, ratio: float):
    """Affiche une alerte de drift."""
    if severity == "high":
        st.markdown(f"""
            <div class="alert-high">
                <strong>🔴 ALERTE HAUTE</strong> - {model_id}<br>
                Ratio RMSE: {ratio:.2f}x (>{1.25}x seuil critique)
            </div>
        """, unsafe_allow_html=True)
    elif severity == "medium":
        st.markdown(f"""
            <div class="alert-medium">
                <strong>🟡 ALERTE MOYENNE</strong> - {model_id}<br>
                Ratio RMSE: {ratio:.2f}x (>{1.10}x seuil d'attention)
            </div>
        """, unsafe_allow_html=True)


def get_score_color(score: float) -> str:
    """Retourne la couleur selon le score."""
    if score >= 80:
        return "#10b981"  # Vert
    elif score >= 60:
        return "#f59e0b"  # Orange
    else:
        return "#ef4444"  # Rouge


def get_drift_color(severity: str) -> str:
    """Retourne la couleur selon la sévérité du drift."""
    colors = {
        "low": "#10b981",
        "medium": "#f59e0b", 
        "high": "#ef4444"
    }
    return colors.get(severity, "#6b7280")


# =============================================================================
# PAGES DU DASHBOARD
# =============================================================================

def page_overview():
    """Page principale : Vue d'ensemble."""
    st.title("📊 Vue d'ensemble")
    
    # Récupérer les données
    models_data = fetch_api("/models")
    ranking_data = fetch_api("/models/ranking", {"window_days": 30})
    scheduler_data = fetch_api("/scheduler/status")
    
    if not models_data or not ranking_data:
        st.warning("Impossible de charger les données. Vérifiez que l'API est accessible.")
        return
    
    # =========================================================================
    # KPIs PRINCIPAUX
    # =========================================================================
    st.subheader("🎯 Indicateurs Clés")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_models = models_data.get("total", 0)
    
    # Calcul du score moyen
    rankings = ranking_data.get("ranking", [])
    avg_score = sum(r.get("avg_score", 0) or 0 for r in rankings) / len(rankings) if rankings else 0
    
    # Compter les alertes
    high_alerts = sum(1 for r in rankings if r.get("drift_summary", {}).get("high", 0) > 0)
    medium_alerts = sum(1 for r in rankings if r.get("drift_summary", {}).get("medium", 0) > 0)
    
    # Schedules actifs
    active_schedules = scheduler_data.get("status_counts", {}).get("active", 0) if scheduler_data else 0
    
    with col1:
        render_kpi_card(total_models, "Modèles Surveillés", "default")
    
    with col2:
        card_type = "success" if avg_score >= 80 else "warning" if avg_score >= 60 else "danger"
        render_kpi_card(f"{avg_score:.0f}", "Score Moyen", card_type)
    
    with col3:
        card_type = "danger" if high_alerts > 0 else "warning" if medium_alerts > 0 else "success"
        render_kpi_card(high_alerts + medium_alerts, "Alertes Drift", card_type)
    
    with col4:
        render_kpi_card(active_schedules, "Schedules Actifs", "default")
    
    st.markdown("---")
    
    # =========================================================================
    # RANKING ET ALERTES
    # =========================================================================
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("🏆 Ranking des Modèles")
        
        if rankings:
            # Créer le graphique de ranking
            df_ranking = pd.DataFrame(rankings)
            df_ranking = df_ranking.sort_values("rank")
            
            fig = go.Figure()
            
            colors = [get_score_color(score or 0) for score in df_ranking["avg_score"]]
            
            fig.add_trace(go.Bar(
                x=df_ranking["avg_score"],
                y=df_ranking["model_id"],
                orientation='h',
                marker=dict(color=colors, line=dict(width=0)),
                text=[f'{s:.0f}' if s else 'N/A' for s in df_ranking["avg_score"]],
                textposition='inside',
                textfont=dict(color='white', size=14, family='Arial Black')
            ))
            
            fig.update_layout(
                height=max(200, len(rankings) * 50),
                margin=dict(l=0, r=20, t=10, b=0),
                xaxis=dict(range=[0, 100], title="Score"),
                yaxis=dict(title="", autorange="reversed"),
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucun modèle évalué pour le moment.")
    
    with col_right:
        st.subheader("🚨 Alertes Actives")
        
        has_alerts = False
        for r in rankings:
            drift_summary = r.get("drift_summary", {})
            model_id = r.get("model_id", "Unknown")
            
            if drift_summary.get("high", 0) > 0:
                render_drift_alert(model_id, "high", 1.25)
                has_alerts = True
            elif drift_summary.get("medium", 0) > 0:
                render_drift_alert(model_id, "medium", 1.10)
                has_alerts = True
        
        if not has_alerts:
            st.success("✅ Aucune alerte - Tous les modèles sont stables")
    
    st.markdown("---")
    
    # =========================================================================
    # TABLEAU DÉTAILLÉ
    # =========================================================================
    st.subheader("📋 Détails des Modèles")
    
    if rankings:
        df_details = pd.DataFrame(rankings)
        df_details = df_details[["rank", "model_id", "avg_score", "avg_rmse", "evaluation_count", "last_evaluation"]]
        df_details.columns = ["Rang", "Modèle", "Score Moyen", "RMSE Moyen", "Nb Évaluations", "Dernière Évaluation"]
        
        # Formater les colonnes
        df_details["Score Moyen"] = df_details["Score Moyen"].apply(lambda x: f"{x:.1f}" if x else "N/A")
        df_details["RMSE Moyen"] = df_details["RMSE Moyen"].apply(lambda x: f"{x:.4f}" if x else "N/A")
        df_details["Dernière Évaluation"] = df_details["Dernière Évaluation"].apply(
            lambda x: x[:19].replace("T", " ") if x else "N/A"
        )
        
        st.dataframe(df_details, use_container_width=True, hide_index=True)


def page_model_detail():
    """Page de détail d'un modèle."""
    st.title("🔍 Analyse Détaillée")
    
    # Récupérer la liste des modèles
    models_data = fetch_api("/models")
    
    if not models_data or models_data.get("total", 0) == 0:
        st.warning("Aucun modèle disponible.")
        return
    
    models = [m["model_id"] for m in models_data.get("models", [])]
    
    # Sélecteur de modèle
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_model = st.selectbox("Sélectionner un modèle", models)
    with col2:
        window_days = st.slider("Période (jours)", 1, 90, 30)
    
    if not selected_model:
        return
    
    # Récupérer l'historique
    history = fetch_api(f"/models/{selected_model}/evaluations", {"limit": 1000})
    
    if not history or len(history.get("items", [])) == 0:
        st.info(f"Aucune évaluation pour {selected_model}")
        return
    
    items = history.get("items", [])
    
    # Convertir en DataFrame
    df = pd.DataFrame(items)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["score"] = df["score"].astype(float)
    
    # Extraire les métriques
    df["mae"] = df["metrics"].apply(lambda x: x.get("mae") if x else None)
    df["mse"] = df["metrics"].apply(lambda x: x.get("mse") if x else None)
    df["rmse"] = df["metrics"].apply(lambda x: x.get("rmse") if x else None)
    df["r2"] = df["metrics"].apply(lambda x: x.get("r2") if x else None)
    df["drift_severity"] = df["performance_drift"].apply(lambda x: x.get("severity") if x else None)
    
    # Filtrer par période (avec timezone UTC pour compatibilité)
    cutoff_date = pd.Timestamp.now(tz='UTC') - timedelta(days=window_days)
    df = df[df["timestamp"] >= cutoff_date]
    
    if df.empty:
        st.info(f"Aucune donnée pour les {window_days} derniers jours")
        return
    
    # =========================================================================
    # KPIs DU MODÈLE
    # =========================================================================
    st.subheader(f"📊 Métriques de {selected_model}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    latest = df.iloc[-1]
    avg_score = df["score"].mean()
    
    with col1:
        card_type = "success" if latest["score"] >= 80 else "warning" if latest["score"] >= 60 else "danger"
        render_kpi_card(f"{latest['score']:.0f}", "Score Actuel", card_type)
    
    with col2:
        render_kpi_card(f"{latest['rmse']:.4f}", "RMSE Actuel", "default")
    
    with col3:
        render_kpi_card(f"{latest['r2']:.3f}", "R² Actuel", "default")
    
    with col4:
        severity = latest.get("drift_severity", "low")
        card_type = "success" if severity == "low" else "warning" if severity == "medium" else "danger"
        render_kpi_card(severity.upper(), "Drift Status", card_type)
    
    st.markdown("---")
    
    # =========================================================================
    # GRAPHIQUES D'ÉVOLUTION
    # =========================================================================
    st.subheader("📈 Évolution Temporelle")
    
    tab1, tab2, tab3 = st.tabs(["Score", "Métriques", "Drift"])
    
    with tab1:
        fig = px.line(
            df, x="timestamp", y="score",
            title="Évolution du Score",
            labels={"timestamp": "Date", "score": "Score"}
        )
        fig.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Excellent (80)")
        fig.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="Acceptable (60)")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = make_subplots(rows=2, cols=2, subplot_titles=("MAE", "MSE", "RMSE", "R²"))
        
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["mae"], mode="lines", name="MAE", line=dict(color="#667eea")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["mse"], mode="lines", name="MSE", line=dict(color="#764ba2")), row=1, col=2)
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["rmse"], mode="lines", name="RMSE", line=dict(color="#f59e0b")), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["r2"], mode="lines", name="R²", line=dict(color="#10b981")), row=2, col=2)
        
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Graphique de distribution des drifts
        drift_counts = df["drift_severity"].value_counts()
        
        fig = px.pie(
            values=drift_counts.values,
            names=drift_counts.index,
            title="Distribution des Niveaux de Drift",
            color=drift_counts.index,
            color_discrete_map={"low": "#10b981", "medium": "#f59e0b", "high": "#ef4444"}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # =========================================================================
    # HISTORIQUE DÉTAILLÉ
    # =========================================================================
    st.subheader("📜 Historique des Évaluations")
    
    df_display = df[["timestamp", "score", "rmse", "r2", "drift_severity"]].copy()
    df_display.columns = ["Date", "Score", "RMSE", "R²", "Drift"]
    df_display["Date"] = df_display["Date"].dt.strftime("%Y-%m-%d %H:%M")
    df_display = df_display.sort_values("Date", ascending=False)
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)


def page_compare():
    """Page de comparaison de modèles."""
    st.title("⚖️ Comparaison de Modèles")
    
    # Récupérer la liste des modèles
    models_data = fetch_api("/models")
    
    if not models_data or models_data.get("total", 0) < 2:
        st.warning("Il faut au moins 2 modèles pour effectuer une comparaison.")
        return
    
    models = [m["model_id"] for m in models_data.get("models", [])]
    
    # Sélecteurs
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        model_a = st.selectbox("Modèle A", models, index=0)
    
    with col2:
        model_b = st.selectbox("Modèle B", models, index=min(1, len(models)-1))
    
    with col3:
        window_days = st.number_input("Période (jours)", min_value=1, max_value=365, value=7)
    
    if model_a == model_b:
        st.warning("Sélectionnez deux modèles différents.")
        return
    
    # Récupérer la comparaison
    comparison = fetch_api("/compare", {"model_a": model_a, "model_b": model_b, "window_days": window_days})
    
    if not comparison:
        st.error("Impossible de récupérer la comparaison.")
        return
    
    # =========================================================================
    # RÉSULTAT DE LA COMPARAISON
    # =========================================================================
    winner = comparison.get("winner")
    
    if winner:
        st.success(f"🏆 **Gagnant : {winner}**")
    else:
        st.info("Pas assez de données pour déterminer un gagnant.")
    
    st.markdown("---")
    
    # =========================================================================
    # COMPARAISON CÔTE À CÔTE
    # =========================================================================
    col_a, col_vs, col_b = st.columns([5, 1, 5])
    
    model_a_data = comparison.get("model_a", {})
    model_b_data = comparison.get("model_b", {})
    
    with col_a:
        st.markdown(f"### 🅰️ {model_a}")
        
        score_a = model_a_data.get("avg_score")
        rmse_a = model_a_data.get("avg_rmse")
        n_a = model_a_data.get("n", 0)
        
        if score_a is not None:
            card_type = "success" if score_a >= 80 else "warning" if score_a >= 60 else "danger"
            render_kpi_card(f"{score_a:.1f}", "Score Moyen", card_type)
        
        st.metric("RMSE Moyen", f"{rmse_a:.4f}" if rmse_a else "N/A")
        st.metric("Nb Évaluations", n_a)
    
    with col_vs:
        st.markdown("<div style='text-align: center; font-size: 3rem; padding-top: 3rem;'>VS</div>", unsafe_allow_html=True)
    
    with col_b:
        st.markdown(f"### 🅱️ {model_b}")
        
        score_b = model_b_data.get("avg_score")
        rmse_b = model_b_data.get("avg_rmse")
        n_b = model_b_data.get("n", 0)
        
        if score_b is not None:
            card_type = "success" if score_b >= 80 else "warning" if score_b >= 60 else "danger"
            render_kpi_card(f"{score_b:.1f}", "Score Moyen", card_type)
        
        st.metric("RMSE Moyen", f"{rmse_b:.4f}" if rmse_b else "N/A")
        st.metric("Nb Évaluations", n_b)
    
    st.markdown("---")
    
    # =========================================================================
    # GRAPHIQUE COMPARATIF
    # =========================================================================
    st.subheader("📊 Comparaison Visuelle")
    
    metrics = ["Score", "RMSE (inversé)", "Évaluations"]
    
    # Normaliser les valeurs pour le radar chart
    max_score = 100
    max_rmse = max(rmse_a or 0, rmse_b or 0, 0.001)
    max_n = max(n_a, n_b, 1)
    
    values_a = [
        (score_a or 0) / max_score * 100,
        (1 - (rmse_a or 0) / max_rmse) * 100 if rmse_a else 0,
        n_a / max_n * 100
    ]
    
    values_b = [
        (score_b or 0) / max_score * 100,
        (1 - (rmse_b or 0) / max_rmse) * 100 if rmse_b else 0,
        n_b / max_n * 100
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values_a + [values_a[0]],
        theta=metrics + [metrics[0]],
        fill='toself',
        name=model_a,
        line=dict(color='#667eea')
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=values_b + [values_b[0]],
        theta=metrics + [metrics[0]],
        fill='toself',
        name=model_b,
        line=dict(color='#f59e0b')
    ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def page_scheduler():
    """Page de gestion des schedules."""
    st.title("⏰ Planification des Évaluations")
    
    # Récupérer le status du scheduler
    scheduler_status = fetch_api("/scheduler/status")
    schedules_data = fetch_api("/scheduler/schedules")
    
    # =========================================================================
    # STATUS DU SCHEDULER
    # =========================================================================
    st.subheader("📊 État du Scheduler")
    
    if scheduler_status:
        col1, col2, col3, col4 = st.columns(4)
        
        status_counts = scheduler_status.get("status_counts", {})
        
        with col1:
            running = scheduler_status.get("running", False)
            st.metric("Status", "🟢 Actif" if running else "🔴 Inactif")
        
        with col2:
            st.metric("Total Schedules", scheduler_status.get("total_schedules", 0))
        
        with col3:
            st.metric("Actifs", status_counts.get("active", 0))
        
        with col4:
            st.metric("En Pause", status_counts.get("paused", 0))
    
    st.markdown("---")
    
    # =========================================================================
    # CRÉER UN NOUVEAU SCHEDULE
    # =========================================================================
    st.subheader("➕ Créer un Nouveau Schedule")
    
    with st.expander("Nouveau Schedule", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            new_model_id = st.text_input("ID du Modèle", placeholder="mon_modele")
            new_interval = st.number_input("Intervalle (minutes)", min_value=1, max_value=10080, value=60)
            new_max_runs = st.number_input("Nombre max d'exécutions (0 = infini)", min_value=0, value=0)
        
        with col2:
            new_y_true = st.text_area("y_true (valeurs séparées par virgule)", "1.0, 2.0, 3.0, 4.0, 5.0")
            new_y_pred = st.text_area("y_pred (valeurs séparées par virgule)", "1.1, 2.1, 2.9, 4.1, 4.9")
            new_baseline = st.number_input("Baseline RMSE (optionnel)", min_value=0.0, value=0.5)
        
        if st.button("Créer le Schedule", type="primary"):
            try:
                y_true = [float(x.strip()) for x in new_y_true.split(",")]
                y_pred = [float(x.strip()) for x in new_y_pred.split(",")]
                
                payload = {
                    "model_id": new_model_id,
                    "interval_minutes": new_interval,
                    "y_true": y_true,
                    "y_pred": y_pred,
                    "baseline_rmse": new_baseline if new_baseline > 0 else None,
                    "max_runs": new_max_runs if new_max_runs > 0 else None
                }
                
                result = post_api("/scheduler/schedules", payload)
                
                if result:
                    st.success(f"✅ Schedule créé : {result.get('schedule_id')}")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
            except ValueError as e:
                st.error(f"Erreur de format : {e}")
    
    st.markdown("---")
    
    # =========================================================================
    # LISTE DES SCHEDULES
    # =========================================================================
    st.subheader("📋 Schedules Existants")
    
    if schedules_data and schedules_data.get("schedules"):
        schedules = schedules_data.get("schedules", [])
        
        for schedule in schedules:
            schedule_id = schedule.get("schedule_id", "")
            model_id = schedule.get("model_id", "")
            status = schedule.get("status", "")
            interval = schedule.get("interval_minutes", 0)
            run_count = schedule.get("run_count", 0)
            max_runs = schedule.get("max_runs")
            next_run = schedule.get("next_run", "")
            
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
                
                with col1:
                    st.markdown(f"**{model_id}**")
                    st.caption(f"ID: {schedule_id[:30]}...")
                
                with col2:
                    status_color = {"active": "🟢", "paused": "🟡", "completed": "⚫", "error": "🔴"}
                    st.markdown(f"{status_color.get(status, '⚪')} {status.upper()}")
                
                with col3:
                    st.markdown(f"⏱️ {interval} min")
                    st.caption(f"Runs: {run_count}" + (f"/{max_runs}" if max_runs else ""))
                
                with col4:
                    if next_run:
                        st.caption(f"Prochain: {next_run[:16]}")
                
                with col5:
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if status == "active":
                            if st.button("⏸️", key=f"pause_{schedule_id}", help="Pause"):
                                post_api(f"/scheduler/schedules/{schedule_id}/pause")
                                st.cache_data.clear()
                                st.rerun()
                        elif status == "paused":
                            if st.button("▶️", key=f"resume_{schedule_id}", help="Resume"):
                                post_api(f"/scheduler/schedules/{schedule_id}/resume")
                                st.cache_data.clear()
                                st.rerun()
                    
                    with col_btn2:
                        if st.button("🎯", key=f"trigger_{schedule_id}", help="Trigger"):
                            result = post_api(f"/scheduler/schedules/{schedule_id}/trigger")
                            if result:
                                st.success("Évaluation déclenchée!")
                                st.cache_data.clear()
                    
                    with col_btn3:
                        if st.button("🗑️", key=f"delete_{schedule_id}", help="Delete"):
                            delete_api(f"/scheduler/schedules/{schedule_id}")
                            st.cache_data.clear()
                            st.rerun()
                
                st.markdown("---")
    else:
        st.info("Aucun schedule configuré.")


def page_evaluate():
    """Page d'évaluation manuelle et automatique ClimaTrack."""
    st.title("🧪 Évaluation des Modèles")
    
    # Onglets pour les différents modes d'évaluation
    tab_climatrack, tab_manual = st.tabs(["🌡️ ClimaTrack (Automatique)", "✏️ Évaluation Manuelle"])
    
    # =========================================================================
    # ONGLET CLIMATRACK - ÉVALUATION AUTOMATIQUE
    # =========================================================================
    with tab_climatrack:
        st.markdown("""
        ### Évaluation automatique du modèle ClimaTrack
        
        Ce module évalue le modèle de prédiction **Humidex** (indice de confort thermique) 
        entraîné sur les données des capteurs ClimaTrack.
        """)
        
        # Rechercher les fichiers de données disponibles
        import glob
        import os
        import json
        import math
        
        # Chemins possibles pour les données
        base_paths = [
            "../IA modele/Prédictions",
            "IA modele/Prédictions",
            "../data",
            "data"
        ]
        
        data_files = []
        for base_path in base_paths:
            pattern = os.path.join(base_path, "merged_data_*.json")
            data_files.extend(glob.glob(pattern))
        
        # Dédupliquer et trier
        data_files = sorted(list(set(data_files)), reverse=True)
        
        if data_files:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                selected_file = st.selectbox(
                    "📂 Fichier de données",
                    data_files,
                    format_func=lambda x: os.path.basename(x)
                )
            
            with col2:
                baseline_rmse_ct = st.number_input(
                    "RMSE Baseline", 
                    min_value=0.01, 
                    value=0.5, 
                    step=0.1,
                    key="baseline_climatrack",
                    help="Seuil de référence pour la détection de drift"
                )
            
            save_result = st.checkbox("💾 Sauvegarder dans l'historique", value=True)
            
            if st.button("🚀 Lancer l'évaluation ClimaTrack", type="primary", use_container_width=True):
                with st.spinner("Chargement et évaluation en cours..."):
                    try:
                        # Charger les données NDJSON
                        records = []
                        with open(selected_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    try:
                                        records.append(json.loads(line))
                                    except json.JSONDecodeError:
                                        continue
                        
                        if not records:
                            st.error("Aucun enregistrement trouvé dans le fichier.")
                        else:
                            st.info(f"📊 {len(records)} enregistrements chargés")
                            
                            # Filtrer les données valides
                            valid_data = []
                            for r in records:
                                try:
                                    temp = float(r.get("temperature", 0))
                                    hum = float(r.get("humidity", 0))
                                    if temp > 0 and hum > 0:
                                        valid_data.append({"temperature": temp, "humidity": hum})
                                except (ValueError, TypeError):
                                    continue
                            
                            if len(valid_data) < 10:
                                st.error("Pas assez de données valides (minimum 10 requis)")
                            else:
                                st.success(f"✅ {len(valid_data)} enregistrements valides")
                                
                                # Calcul de l'humidex réel (formule météorologique)
                                def calc_humidex(temp, humidity):
                                    """Calcule l'humidex à partir de la température et de l'humidité."""
                                    if humidity <= 0:
                                        return temp
                                    dewpoint = temp - ((100 - humidity) / 5)
                                    e = 6.11 * math.exp(5417.7530 * ((1/273.16) - (1/(273.15 + dewpoint))))
                                    humidex = temp + 0.5555 * (e - 10)
                                    return humidex
                                
                                # Préparer y_true (humidex calculé)
                                y_true_all = [calc_humidex(d["temperature"], d["humidity"]) for d in valid_data]
                                
                                # Entraîner le modèle LinearRegression
                                try:
                                    from sklearn.linear_model import LinearRegression
                                    from sklearn.model_selection import train_test_split
                                    import numpy as np
                                    
                                    X = np.array([[d["temperature"], d["humidity"]] for d in valid_data])
                                    y = np.array(y_true_all)
                                    
                                    X_train, X_test, y_train, y_test = train_test_split(
                                        X, y, test_size=0.2, random_state=42
                                    )
                                    
                                    model = LinearRegression()
                                    model.fit(X_train, y_train)
                                    y_pred = model.predict(X_test)
                                    
                                    st.info(f"🤖 Modèle entraîné - {len(y_test)} prédictions générées")
                                    
                                    # Appeler l'API pour évaluer
                                    payload = {
                                        "y_true": y_test.tolist(),
                                        "y_pred": y_pred.tolist(),
                                        "baseline_rmse": baseline_rmse_ct
                                    }
                                    
                                    model_id = "climatrack_humidex_v1"
                                    
                                    if save_result:
                                        result = post_api(f"/models/{model_id}/evaluate", payload)
                                        if result:
                                            st.success(f"✅ Évaluation sauvegardée pour {model_id}")
                                            result = result.get("result", result)
                                    else:
                                        result = post_api("/evaluate", payload)
                                    
                                    if result:
                                        st.markdown("---")
                                        st.subheader("📊 Résultats ClimaTrack")
                                        
                                        score = result.get("score", 0)
                                        metrics = result.get("metrics", {})
                                        drift = result.get("performance_drift", {})
                                        
                                        # KPIs principaux
                                        col1, col2, col3, col4 = st.columns(4)
                                        
                                        with col1:
                                            card_type = "success" if score >= 80 else "warning" if score >= 60 else "danger"
                                            render_kpi_card(f"{score:.0f}", "Score Global", card_type)
                                        
                                        with col2:
                                            rmse = metrics.get("rmse", 0)
                                            render_kpi_card(f"{rmse:.4f}", "RMSE", "default")
                                        
                                        with col3:
                                            r2 = metrics.get("r2", 0)
                                            card_type = "success" if r2 >= 0.95 else "warning" if r2 >= 0.8 else "danger"
                                            render_kpi_card(f"{r2:.4f}", "R²", card_type)
                                        
                                        with col4:
                                            severity = drift.get("severity", "low")
                                            card_type = "success" if severity == "low" else "warning" if severity == "medium" else "danger"
                                            render_kpi_card(severity.upper(), "Drift", card_type)
                                        
                                        # Graphique de comparaison
                                        st.markdown("#### 📈 Prédictions vs Réalité")
                                        
                                        fig = go.Figure()
                                        fig.add_trace(go.Scatter(
                                            x=list(range(len(y_test))),
                                            y=y_test.tolist(),
                                            mode='lines+markers',
                                            name='Valeurs Réelles',
                                            line=dict(color='#10b981')
                                        ))
                                        fig.add_trace(go.Scatter(
                                            x=list(range(len(y_pred))),
                                            y=y_pred.tolist(),
                                            mode='lines+markers',
                                            name='Prédictions',
                                            line=dict(color='#667eea', dash='dash')
                                        ))
                                        fig.update_layout(
                                            xaxis_title="Échantillon",
                                            yaxis_title="Humidex",
                                            legend=dict(orientation="h", yanchor="bottom", y=1.02),
                                            height=400
                                        )
                                        st.plotly_chart(fig, use_container_width=True)
                                        
                                        # Métriques détaillées
                                        st.markdown("#### 📋 Métriques Détaillées")
                                        col1, col2, col3, col4 = st.columns(4)
                                        col1.metric("MAE", f"{metrics.get('mae', 0):.6f}")
                                        col2.metric("MSE", f"{metrics.get('mse', 0):.6f}")
                                        col3.metric("RMSE", f"{metrics.get('rmse', 0):.6f}")
                                        col4.metric("R²", f"{metrics.get('r2', 0):.6f}")
                                        
                                        # Analyse drift
                                        st.markdown("#### 🔍 Analyse du Drift")
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.metric("Ratio RMSE/Baseline", f"{drift.get('ratio', 0):.2f}x")
                                            st.metric("Drift Détecté", "✅ Non" if not drift.get("drift_detected") else "⚠️ Oui")
                                        with col2:
                                            st.metric("Delta", f"{drift.get('delta', 0):.6f}")
                                            st.metric("Sévérité", drift.get("severity", "N/A").upper())
                                        
                                        st.info(f"💡 {drift.get('reason', 'Performances stables')}")
                                        
                                except ImportError:
                                    st.error("scikit-learn n'est pas installé. Exécutez : `pip install scikit-learn`")
                                    
                    except Exception as e:
                        st.error(f"Erreur lors de l'évaluation : {e}")
        else:
            st.warning("""
            ⚠️ Aucun fichier de données ClimaTrack trouvé.
            
            Placez vos fichiers `merged_data_*.json` dans :
            - `IA modele/Prédictions/`
            - ou `data/`
            """)
    
    # =========================================================================
    # ONGLET ÉVALUATION MANUELLE
    # =========================================================================
    with tab_manual:
        st.markdown("""
        Effectuez une évaluation ponctuelle d'un modèle en fournissant les données de prédiction.
        """)
    
        # =========================================================================
        # FORMULAIRE D'ÉVALUATION
        # =========================================================================
        col1, col2 = st.columns(2)
    
        with col1:
            model_id = st.text_input("ID du Modèle (optionnel)", placeholder="mon_modele", help="Si renseigné, l'évaluation sera sauvegardée")
            y_true_input = st.text_area(
                "Valeurs Réelles (y_true)",
                "10.0, 20.0, 30.0, 40.0, 50.0",
                help="Valeurs séparées par des virgules"
            )
    
        with col2:
            baseline_rmse = st.number_input("RMSE Baseline", min_value=0.0, value=5.0, help="RMSE de référence pour la détection de drift")
            y_pred_input = st.text_area(
                "Valeurs Prédites (y_pred)",
                "11.0, 19.0, 31.0, 39.0, 51.0",
                help="Valeurs séparées par des virgules"
            )
    
        if st.button("🚀 Évaluer", type="primary", use_container_width=True):
            try:
                y_true = [float(x.strip()) for x in y_true_input.split(",")]
                y_pred = [float(x.strip()) for x in y_pred_input.split(",")]
            
                if len(y_true) != len(y_pred):
                    st.error("y_true et y_pred doivent avoir le même nombre de valeurs.")
                    return
            
                payload = {
                    "y_true": y_true,
                    "y_pred": y_pred,
                    "baseline_rmse": baseline_rmse
                }
            
                # Appeler l'API appropriée
                if model_id:
                    result = post_api(f"/models/{model_id}/evaluate", payload)
                    if result:
                        st.success(f"✅ Évaluation sauvegardée pour {model_id}")
                        result = result.get("result", result)
                else:
                    result = post_api("/evaluate", payload)
            
                if result:
                    st.markdown("---")
                    st.subheader("📊 Résultats")
                
                    # Afficher les résultats
                    col1, col2, col3 = st.columns(3)
                
                    score = result.get("score", 0)
                    metrics = result.get("metrics", {})
                    drift = result.get("performance_drift", {})
                
                    with col1:
                        card_type = "success" if score >= 80 else "warning" if score >= 60 else "danger"
                        render_kpi_card(f"{score:.0f}", "Score Global", card_type)
                
                    with col2:
                        severity = drift.get("severity", "low")
                        card_type = "success" if severity == "low" else "warning" if severity == "medium" else "danger"
                        render_kpi_card(severity.upper(), "Drift Status", card_type)
                
                    with col3:
                        rmse = metrics.get("rmse", 0)
                        render_kpi_card(f"{rmse:.4f}", "RMSE", "default")
                
                    # Détails des métriques
                    st.markdown("#### Métriques Détaillées")
                
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("MAE", f"{metrics.get('mae', 0):.4f}")
                    col2.metric("MSE", f"{metrics.get('mse', 0):.4f}")
                    col3.metric("RMSE", f"{metrics.get('rmse', 0):.4f}")
                    col4.metric("R²", f"{metrics.get('r2', 0):.4f}")
                
                    # Détails du drift
                    st.markdown("#### Analyse du Drift")
                
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Ratio RMSE", f"{drift.get('ratio', 0):.2f}x")
                    col2.metric("Delta", f"{drift.get('delta', 0):.4f}")
                    col3.metric("Détecté", "Oui" if drift.get("drift_detected") else "Non")
                
                    st.info(f"💡 {drift.get('reason', 'N/A')}")
                
            except ValueError as e:
                st.error(f"Erreur de format : {e}")


# =============================================================================
# PAGE INTERPRÉTATION & RISQUES (F2-UC5, F4-UC3, F4-UC4, F4-UC5)
# =============================================================================

def page_interpretation():
    """Page d'interprétation, justification et recommandations."""
    st.title("🧠 Interprétation & Risques")

    models_data = fetch_api("/models")
    if not models_data or models_data.get("total", 0) == 0:
        st.warning("Aucun modèle disponible.")
        return

    models = [m["model_id"] for m in models_data.get("models", [])]

    tab_interpret, tab_risk_overview = st.tabs(["🔍 Détail Modèle", "📊 Vue des Risques"])

    # =========================================================================
    # ONGLET INTERPRÉTATION D'UN MODÈLE
    # =========================================================================
    with tab_interpret:
        selected_model = st.selectbox("Sélectionner un modèle", models, key="interpret_model")

        if st.button("🔎 Analyser", type="primary", key="btn_interpret"):
            with st.spinner("Analyse en cours..."):
                data = fetch_api(f"/models/{selected_model}/interpret", {"window_days": 30})

            if data:
                # --- Risque ---
                risk = data.get("risk", {})
                st.markdown(f"### {risk.get('icon', '')} Niveau de risque : **{risk.get('label', 'N/A')}**")
                if risk.get("risk_note"):
                    st.warning(risk["risk_note"])

                st.markdown("---")

                # --- Interprétation ---
                interp = data.get("interpretation", {})
                st.subheader("📝 Interprétation")
                st.info(interp.get("summary", ""))

                if interp.get("details"):
                    for detail in interp["details"]:
                        st.markdown(f"- {detail}")

                st.markdown("#### Analyse par métrique")
                for metric_name, analysis in interp.get("metrics_analysis", {}).items():
                    st.markdown(f"- **{metric_name.upper()}** : {analysis}")

                st.markdown(f"**Drift** : {interp.get('drift_explanation', 'N/A')}")

                st.markdown("---")

                # --- Justification (F4-UC4) ---
                justif = data.get("justification", {})
                st.subheader(f"🎯 Justification du Score : {justif.get('score_global', 'N/A')}/100")

                decomp = justif.get("decomposition", [])
                if decomp:
                    # Graphique de décomposition
                    df_decomp = pd.DataFrame(decomp)
                    fig = go.Figure()
                    colors_map = {
                        "EXCELLENT": "#10b981", "BON": "#3b82f6",
                        "ACCEPTABLE": "#f59e0b", "DEGRADE": "#f97316", "CRITIQUE": "#ef4444",
                    }
                    fig.add_trace(go.Bar(
                        x=df_decomp["metrique"].str.upper(),
                        y=df_decomp["contribution"],
                        marker_color=[colors_map.get(e, "#6b7280") for e in df_decomp["evaluation"]],
                        text=[f"{c:.1f}" for c in df_decomp["contribution"]],
                        textposition="auto",
                    ))
                    fig.update_layout(
                        title="Contribution de chaque métrique au score",
                        xaxis_title="Métrique", yaxis_title="Points",
                        height=350,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Tableau détaillé
                    st.dataframe(
                        pd.DataFrame(decomp)[["metrique", "valeur", "poids", "score_metrique", "contribution", "evaluation"]].rename(
                            columns={"metrique": "Métrique", "valeur": "Valeur", "poids": "Poids",
                                     "score_metrique": "Score", "contribution": "Contribution", "evaluation": "Évaluation"}
                        ),
                        use_container_width=True, hide_index=True,
                    )

                # Pénalités
                penalites = justif.get("penalites", [])
                if penalites:
                    st.markdown("#### ⚠️ Pénalités")
                    for p in penalites:
                        st.markdown(f"- **{p['type']}** ({p['niveau']}) : {p['impact']} points — {p['raison']}")

                # Analyse
                analyse = justif.get("analyse", {})
                pf = analyse.get("point_fort")
                pw = analyse.get("point_faible")
                if pf:
                    st.success(f"💪 Point fort : **{pf['metrique'].upper()}** (score {pf['score']})")
                if pw:
                    st.warning(f"📉 Point faible : **{pw['metrique'].upper()}** (score {pw['score']})")

                st.markdown("---")

                # --- Recommandations (F4-UC5) ---
                st.subheader("🔧 Recommandations de Maintenance")
                for rec in data.get("recommendations", []):
                    st.markdown(f"- {rec}")

    # =========================================================================
    # ONGLET VUE D'ENSEMBLE DES RISQUES
    # =========================================================================
    with tab_risk_overview:
        st.subheader("📊 Catégorisation des Risques")

        risk_data = fetch_api("/risk/overview")
        if risk_data:
            summary = risk_data.get("summary", {})

            # KPIs par catégorie
            cols = st.columns(5)
            cats = ["EXCELLENT", "BON", "ACCEPTABLE", "DEGRADE", "CRITIQUE"]
            icons = ["🟢", "🔵", "🟡", "🟠", "🔴"]
            card_types = ["success", "default", "warning", "warning", "danger"]

            for i, (cat, icon, ct) in enumerate(zip(cats, icons, card_types)):
                with cols[i]:
                    render_kpi_card(summary.get(cat, 0), f"{icon} {cat}", ct)

            st.markdown("---")

            # Graphique circulaire
            labels = [cat for cat in cats if summary.get(cat, 0) > 0]
            values = [summary.get(cat, 0) for cat in cats if summary.get(cat, 0) > 0]
            color_map = {"EXCELLENT": "#10b981", "BON": "#3b82f6", "ACCEPTABLE": "#f59e0b",
                         "DEGRADE": "#f97316", "CRITIQUE": "#ef4444"}

            if labels:
                fig = px.pie(
                    values=values, names=labels,
                    title="Répartition des Modèles par Risque",
                    color=labels,
                    color_discrete_map=color_map,
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

            # Détails par catégorie
            by_cat = risk_data.get("by_category", {})
            for cat in cats:
                items = by_cat.get(cat, [])
                if items:
                    st.markdown(f"#### {icons[cats.index(cat)]} {cat} ({len(items)} modèle(s))")
                    for item in items:
                        st.markdown(f"- **{item['model_id']}** — Score: {item['score']}, Drift: {item['drift_severity']}")
        else:
            st.warning("Impossible de charger les données de risques.")


# =============================================================================
# PAGE FILTRES AVANCÉS & EXPORT (F5-UC5)
# =============================================================================

def _generate_pdf_report(model_id: str, history_items: list, interp_data: dict) -> bytes:
    """Génère un rapport texte structuré pour export."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"RAPPORT SENTINEL360 — {model_id}")
    lines.append(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 60)

    if interp_data:
        risk = interp_data.get("risk", {})
        lines.append(f"\nNiveau de risque : {risk.get('label', 'N/A')} {risk.get('icon', '')}")
        lines.append(f"Score : {interp_data.get('latest_score', 'N/A')}/100")

        interp = interp_data.get("interpretation", {})
        lines.append(f"\nRésumé : {interp.get('summary', '')}")

        lines.append("\nAnalyse des métriques :")
        for name, analysis in interp.get("metrics_analysis", {}).items():
            lines.append(f"  - {name.upper()} : {analysis}")

        justif = interp_data.get("justification", {})
        decomp = justif.get("decomposition", [])
        if decomp:
            lines.append("\nDécomposition du score :")
            for c in decomp:
                lines.append(
                    f"  - {c['metrique'].upper()} (poids {c['poids']}) : "
                    f"score {c['score_metrique']}, contribution {c['contribution']} pts ({c['evaluation']})"
                )

        recs = interp_data.get("recommendations", [])
        if recs:
            lines.append("\nRecommandations :")
            for r in recs:
                lines.append(f"  - {r}")

    if history_items:
        lines.append(f"\nHistorique ({len(history_items)} évaluations) :")
        lines.append("-" * 60)
        lines.append(f"{'Date':<22} {'Score':>6} {'RMSE':>10} {'R²':>8} {'Drift':>8}")
        lines.append("-" * 60)
        for item in history_items[-50:]:
            ts = item.get("timestamp", "")[:19].replace("T", " ")
            sc = item.get("score", "N/A")
            rmse = item.get("metrics", {}).get("rmse", 0)
            r2 = item.get("metrics", {}).get("r2", 0)
            drift = item.get("performance_drift", {}).get("severity", "?")
            lines.append(f"{ts:<22} {sc:>6} {rmse:>10.4f} {r2:>8.4f} {drift:>8}")

    lines.append("\n" + "=" * 60)
    lines.append("Généré par Sentinel360 — EcoWatch / Neusta")

    return "\n".join(lines).encode("utf-8")


def page_advanced():
    """Page de filtres avancés et export (F5-UC5)."""
    st.title("🔎 Filtres Avancés & Export")

    models_data = fetch_api("/models")
    if not models_data or models_data.get("total", 0) == 0:
        st.warning("Aucun modèle disponible.")
        return

    models = [m["model_id"] for m in models_data.get("models", [])]

    # =========================================================================
    # FILTRES
    # =========================================================================
    st.subheader("🎛️ Filtres")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        selected_models = st.multiselect("Modèles", models, default=models)
    with col2:
        date_from = st.date_input("Date début", value=datetime.now() - timedelta(days=30))
    with col3:
        date_to = st.date_input("Date fin", value=datetime.now())
    with col4:
        score_range = st.slider("Score", 0, 100, (0, 100))

    drift_filter = st.multiselect(
        "Filtrer par drift",
        ["low", "medium", "high"],
        default=["low", "medium", "high"],
    )

    st.markdown("---")

    # =========================================================================
    # DONNÉES FILTRÉES
    # =========================================================================
    st.subheader("📋 Résultats Filtrés")

    all_data = []
    for model_id in selected_models:
        from_ts = f"{date_from}T00:00:00Z"
        to_ts = f"{date_to}T23:59:59Z"
        history = fetch_api(
            f"/models/{model_id}/evaluations",
            {"from_ts": from_ts, "to_ts": to_ts, "limit": 5000}
        )
        if history and history.get("items"):
            for item in history["items"]:
                item["model_id"] = model_id
                all_data.append(item)

    if not all_data:
        st.info("Aucune donnée trouvée avec ces filtres.")
        return

    # Convertir en DataFrame
    df = pd.DataFrame(all_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["score"] = df["score"].astype(float)
    df["rmse"] = df["metrics"].apply(lambda x: x.get("rmse", 0) if x else 0)
    df["mae"] = df["metrics"].apply(lambda x: x.get("mae", 0) if x else 0)
    df["r2"] = df["metrics"].apply(lambda x: x.get("r2", 0) if x else 0)
    df["drift_severity"] = df["performance_drift"].apply(
        lambda x: x.get("severity", "low") if x else "low"
    )

    # Appliquer les filtres
    df = df[
        (df["score"] >= score_range[0]) &
        (df["score"] <= score_range[1]) &
        (df["drift_severity"].isin(drift_filter))
    ]

    st.markdown(f"**{len(df)} évaluations** trouvées")

    # Tableau
    df_display = df[["model_id", "timestamp", "score", "rmse", "r2", "drift_severity"]].copy()
    df_display.columns = ["Modèle", "Date", "Score", "RMSE", "R²", "Drift"]
    df_display["Date"] = df_display["Date"].dt.strftime("%Y-%m-%d %H:%M")
    df_display = df_display.sort_values("Date", ascending=False)

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Graphique multi-modèles
    if len(selected_models) > 0:
        st.subheader("📈 Évolution Comparée")
        fig = px.line(
            df, x="timestamp", y="score", color="model_id",
            title="Score au fil du temps",
            labels={"timestamp": "Date", "score": "Score", "model_id": "Modèle"},
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # EXPORT (F5-UC5)
    # =========================================================================
    st.subheader("📤 Export")

    col_exp1, col_exp2, col_exp3 = st.columns(3)

    with col_exp1:
        # Export CSV
        csv_data = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv_data,
            file_name=f"sentinel360_export_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_exp2:
        # Export JSON
        json_data = df_display.to_json(orient="records", date_format="iso", force_ascii=False).encode("utf-8")
        st.download_button(
            label="📥 Télécharger JSON",
            data=json_data,
            file_name=f"sentinel360_export_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_exp3:
        # Export rapport texte
        if st.button("📄 Générer Rapport", use_container_width=True):
            with st.spinner("Génération du rapport..."):
                report_lines = []
                for mid in selected_models:
                    interp_data = fetch_api(f"/models/{mid}/interpret", {"window_days": 30})
                    model_items = [item for item in all_data if item.get("model_id") == mid]
                    report_bytes = _generate_pdf_report(mid, model_items, interp_data)
                    report_lines.append(report_bytes.decode("utf-8"))

                full_report = ("\n\n" + "=" * 60 + "\n\n").join(report_lines)

                st.download_button(
                    label="📥 Télécharger Rapport (.txt)",
                    data=full_report.encode("utf-8"),
                    file_name=f"sentinel360_rapport_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

def main():
    """Point d'entrée principal du dashboard."""
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/200x60/667eea/ffffff?text=Sentinel360", use_container_width=True)
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["🏠 Vue d'ensemble", "🔍 Analyse Détaillée", "⚖️ Comparaison", "⏰ Planification", "🧪 Évaluation", "🧠 Interprétation", "🔎 Filtres & Export"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Informations
        st.markdown("### ℹ️ À propos")
        st.markdown("""
        **Sentinel360** est un module d'audit et de surveillance de modèles IA prédictifs.
        
        - 📊 Suivi des performances
        - 🚨 Détection de drift
        - 📈 Analyse de tendances
        """)
        
        st.markdown("---")
        st.caption("© 2026 EcoWatch - Neusta")
    
    # Rendu de la page
    render_header()
    
    if page == "🏠 Vue d'ensemble":
        page_overview()
    elif page == "🔍 Analyse Détaillée":
        page_model_detail()
    elif page == "⚖️ Comparaison":
        page_compare()
    elif page == "⏰ Planification":
        page_scheduler()
    elif page == "🧪 Évaluation":
        page_evaluate()
    elif page == "🧠 Interprétation":
        page_interpretation()
    elif page == "🔎 Filtres & Export":
        page_advanced()


if __name__ == "__main__":
    main()
