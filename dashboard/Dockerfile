# =============================================================================
# Sentinel360 Dashboard - Dockerfile
# =============================================================================

FROM python:3.12-slim

LABEL maintainer="Ilias Belkhder"
LABEL description="Sentinel360 Dashboard - Interface de surveillance IA"

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

WORKDIR /app

# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY app.py .

# Créer un utilisateur non-root
RUN groupadd --gid 1000 dashboard && \
    useradd --uid 1000 --gid dashboard --shell /bin/bash --create-home dashboard && \
    chown -R dashboard:dashboard /app

USER dashboard

# Exposer le port Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Lancer Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
