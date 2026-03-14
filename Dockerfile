# =============================================================================
# Sentinel360 - Dockerfile
# Module d'audit et de surveillance de modèles IA prédictifs
# =============================================================================

# Étape 1 : Image de base Python légère
FROM python:3.12-slim AS base

# Métadonnées de l'image
LABEL maintainer="Ilias Belkhder <ilias@sentinel360.io>"
LABEL description="Sentinel360 - API de surveillance et notation de modèles IA"
LABEL version="1.0.0"

# Variables d'environnement pour Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /app

# =============================================================================
# Étape 2 : Installation des dépendances (layer cache optimisé)
# =============================================================================
FROM base AS dependencies

# Copier uniquement les fichiers de dépendances pour exploiter le cache Docker
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Étape 3 : Image de production
# =============================================================================
FROM dependencies AS production

# Créer un utilisateur non-root pour la sécurité
RUN groupadd --gid 1000 sentinel && \
    useradd --uid 1000 --gid sentinel --shell /bin/bash --create-home sentinel

# Copier le code source de l'application
COPY --chown=sentinel:sentinel app/ ./app/
COPY --chown=sentinel:sentinel tests/ ./tests/

# Basculer vers l'utilisateur non-root
USER sentinel

# Exposer le port de l'API
EXPOSE 8000

# Health check pour Docker et orchestrateurs
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Commande de démarrage par défaut
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Étape 4 : Image de développement (optionnelle)
# =============================================================================
FROM dependencies AS development

# Installer les dépendances de développement supplémentaires
RUN pip install --no-cache-dir pytest pytest-cov httpx

# Copier tout le code source
COPY . .

# Commande par défaut en mode développement (avec hot-reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
