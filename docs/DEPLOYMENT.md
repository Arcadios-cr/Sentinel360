# 🚀 Guide de Déploiement - Sentinel360

## Table des Matières

1. [Prérequis](#prérequis)
2. [Déploiement Docker](#déploiement-docker)
3. [Déploiement Local](#déploiement-local)
4. [Configuration](#configuration)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)

---

## Prérequis

### Docker (Recommandé)

| Logiciel | Version minimale |
|----------|-----------------|
| Docker | 24.0+ |
| Docker Compose | 2.0+ |

### Installation Locale

| Logiciel | Version minimale |
|----------|-----------------|
| Python | 3.12+ |
| pip | 23.0+ |

---

## Déploiement Docker

### 1. Démarrage Rapide

```bash
# Cloner le repository
git clone <repository-url>
cd Sentinel360

# Lancer tous les services
docker compose up -d

# Vérifier le statut
docker ps
```

**Services démarrés :**

| Service | Port | URL |
|---------|------|-----|
| API | 8000 | http://localhost:8000 |
| Swagger | 8000 | http://localhost:8000/docs |
| Dashboard | 8501 | http://localhost:8501 |

### 2. Commandes Docker

```bash
# Démarrer les services
docker compose up -d

# Démarrer uniquement l'API
docker compose up -d api

# Voir les logs en temps réel
docker compose logs -f

# Logs d'un service spécifique
docker compose logs -f api
docker compose logs -f dashboard

# Arrêter les services
docker compose down

# Reconstruire après modification
docker compose build
docker compose up -d

# Reconstruire un service spécifique
docker compose build api
docker compose up -d api

# Nettoyer tout (images, volumes)
docker compose down --rmi all --volumes
```

### 3. Makefile

Pour simplifier les commandes, utilisez le Makefile :

```bash
make help      # Afficher toutes les commandes disponibles
make build     # Construire les images
make run       # Lancer en production
make dev       # Lancer en développement (hot-reload)
make stop      # Arrêter les conteneurs
make logs      # Afficher les logs
make test      # Exécuter les tests
make clean     # Nettoyer les ressources
```

### 4. Structure Docker

```
Sentinel360/
├── Dockerfile              # Image API (multi-stage)
├── docker-compose.yml      # Orchestration
├── .dockerignore           # Fichiers exclus
└── dashboard/
    └── Dockerfile          # Image Dashboard
```

#### Dockerfile API (Multi-stage)

```dockerfile
# Stage 1: Build
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY app/ ./app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=info
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  dashboard:
    build: ./dashboard
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://api:8000
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped
```

---

## Déploiement Local

### 1. Environnement Virtuel

```bash
# Créer l'environnement
python -m venv .venv

# Activer (Linux/Mac)
source .venv/bin/activate

# Activer (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activer (Windows CMD)
.venv\Scripts\activate.bat
```

### 2. Installation des Dépendances

```bash
# API
pip install -r requirements.txt

# Dashboard (dans un autre terminal)
cd dashboard
pip install -r requirements.txt
```

### 3. Lancement

**Terminal 1 - API :**
```bash
cd Sentinel360
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Dashboard :**
```bash
cd Sentinel360/dashboard
source ../.venv/bin/activate
streamlit run app.py --server.port 8501
```

### 4. Mode Développement

Pour le hot-reload automatique :

```bash
# API avec rechargement automatique
uvicorn app.main:app --reload

# Dashboard (hot-reload natif)
streamlit run app.py
```

---

## Configuration

### Variables d'Environnement

Créer un fichier `.env` à partir de `.env.example` :

```bash
cp .env.example .env
```

#### Variables Disponibles

| Variable | Description | Défaut |
|----------|-------------|--------|
| `API_HOST` | Hôte de l'API | `0.0.0.0` |
| `API_PORT` | Port de l'API | `8000` |
| `LOG_LEVEL` | Niveau de log (debug, info, warning, error) | `info` |
| `API_BASE_URL` | URL de l'API (pour le dashboard) | `http://localhost:8000` |

#### Exemple .env

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=info

# Dashboard Configuration
API_BASE_URL=http://api:8000

# Future: Database
# DATABASE_URL=postgresql://user:pass@db:5432/sentinel360

# Future: Auth
# JWT_SECRET=your-secret-key
# JWT_ALGORITHM=HS256
```

### Configuration Docker Compose

Pour personnaliser le déploiement, modifiez `docker-compose.yml` :

```yaml
services:
  api:
    environment:
      - LOG_LEVEL=debug  # Plus de logs
    ports:
      - "8080:8000"  # Changer le port externe
```

---

## Monitoring

### Health Checks

L'API expose un endpoint de santé :

```bash
# Vérifier l'API
curl http://localhost:8000/health
# {"status": "ok"}

# Vérifier le dashboard
curl -I http://localhost:8501
# HTTP/1.1 200 OK
```

### Logs Docker

```bash
# Tous les logs
docker compose logs

# Logs en temps réel
docker compose logs -f

# Logs d'un service
docker compose logs -f api

# Dernières 100 lignes
docker compose logs --tail=100 api
```

### Métriques (Future)

> **Note** : L'intégration Prometheus/Grafana est prévue pour le Lot 2.

```yaml
# Future docker-compose.yml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

---

## Troubleshooting

### Problèmes Courants

#### 1. Port déjà utilisé

```
Error: bind: address already in use
```

**Solution :**
```bash
# Trouver le processus
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Tuer le processus ou changer le port
docker compose down
# Modifier le port dans docker-compose.yml
docker compose up -d
```

#### 2. Docker daemon non démarré

```
Cannot connect to the Docker daemon
```

**Solution :**
```bash
# Linux
sudo service docker start

# Windows/Mac
# Démarrer Docker Desktop
```

#### 3. Image non trouvée

```
Error: No such image
```

**Solution :**
```bash
docker compose build
docker compose up -d
```

#### 4. Erreur de mémoire

```
Container killed due to OOM
```

**Solution :**
```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 512M
```

#### 5. Dashboard ne trouve pas l'API

```
ConnectionError: Unable to connect to API
```

**Solution :**
```bash
# Vérifier que l'API est démarrée
docker compose ps

# Vérifier les logs
docker compose logs api

# Recréer les conteneurs
docker compose down
docker compose up -d
```

#### 6. WSL - Commandes Linux

Sur Windows avec WSL, utilisez :
```powershell
wsl -d Ubuntu bash -c "cd /path/to/project && docker compose up -d"
```

### Vérifications de Base

```bash
# 1. Statut des conteneurs
docker ps

# 2. Logs récents
docker compose logs --tail=50

# 3. Health check API
curl http://localhost:8000/health

# 4. Test endpoint
curl http://localhost:8000/models

# 5. Réseau Docker
docker network ls
docker network inspect sentinel360_default
```

### Réinitialisation Complète

Si rien ne fonctionne :

```bash
# Arrêter tout
docker compose down

# Supprimer les images
docker compose down --rmi all

# Supprimer les volumes
docker volume prune -f

# Reconstruire
docker compose build --no-cache

# Relancer
docker compose up -d
```

---

## Déploiement Production (Recommandations)

### 1. Sécurité

- [ ] Activer HTTPS (certificat SSL)
- [ ] Configurer un reverse proxy (Nginx, Traefik)
- [ ] Ajouter l'authentification (JWT - Lot 2)
- [ ] Limiter les CORS
- [ ] Rate limiting

### 2. Performance

- [ ] Configurer les workers Uvicorn
- [ ] Activer la mise en cache (Redis)
- [ ] Optimiser les requêtes DB (Lot 2)

### 3. Haute Disponibilité

- [ ] Load balancer
- [ ] Réplication des conteneurs
- [ ] Health checks automatiques

### Exemple Nginx

```nginx
upstream api {
    server api:8000;
}

upstream dashboard {
    server dashboard:8501;
}

server {
    listen 80;
    server_name sentinel360.example.com;

    location /api {
        proxy_pass http://api;
    }

    location / {
        proxy_pass http://dashboard;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

*Dernière mise à jour : 1er février 2026*
