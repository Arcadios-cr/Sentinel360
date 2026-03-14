# F5-UC4 : Déploiement Docker

> **Statut** : ✅ Terminé  
> **Version** : 1.0  
> **Date** : 8 mars 2026

---

## 1. Description

Déploiement de l'application Sentinel360 (API + Dashboard) sous Docker avec une exécution reproductible et une orchestration via Docker Compose.

---

## 2. Architecture

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `Dockerfile` | Image Docker pour l'API FastAPI |
| `dashboard/Dockerfile` | Image Docker pour le Dashboard Streamlit |
| `docker-compose.yml` | Orchestration des services |
| `requirements.txt` | Dépendances Python |

### Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────┐      ┌────────────────────┐         │
│  │   sentinel360-api  │      │ sentinel360-dashboard│        │
│  │                    │◄────►│                     │         │
│  │   FastAPI          │ HTTP │   Streamlit         │         │
│  │   Port: 8000       │      │   Port: 8501        │         │
│  └─────────┬──────────┘      └─────────────────────┘         │
│            │                                                  │
│            ▼                                                  │
│  ┌────────────────────┐                                      │
│  │   sentinel-data    │  (Volume persistant)                 │
│  │   /app/app/data    │                                      │
│  └────────────────────┘                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| `sentinel360-api` | Python 3.12 + FastAPI | 8000 | API REST |
| `sentinel360-dashboard` | Python 3.12 + Streamlit | 8501 | Interface web |

---

## 4. Commandes

### Démarrage complet

```bash
# Build et démarrage
docker-compose up --build -d

# Voir les logs
docker-compose logs -f

# Statut des services
docker-compose ps
```

### Arrêt

```bash
# Arrêter les services
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v
```

### Accès

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| Documentation API | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |

---

## 5. Configuration

### Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | URL de l'API pour le dashboard |
| `PYTHONPATH` | `/app` | Chemin Python |

### Volumes

| Volume | Chemin | Description |
|--------|--------|-------------|
| `sentinel-data` | `/app/app/data` | Persistance des données (historique, schedules) |

---

## 6. Dockerfile API

```dockerfile
FROM python:3.12-slim

LABEL maintainer="Sentinel360"
LABEL version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY tests/ ./tests/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 7. Dockerfile Dashboard

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

---

## 8. docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: sentinel360-api
    ports:
      - "8000:8000"
    volumes:
      - sentinel-data:/app/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  dashboard:
    build: ./dashboard
    container_name: sentinel360-dashboard
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://api:8000
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

volumes:
  sentinel-data:

networks:
  default:
    name: sentinel-network
```

---

## 9. Health Checks

Les deux services exposent des endpoints de santé :

| Service | Endpoint | Réponse |
|---------|----------|---------|
| API | `GET /health` | `{"status": "healthy"}` |
| Dashboard | `GET /_stcore/health` | `ok` |

---

## 10. Makefile (optionnel)

```makefile
.PHONY: build up down logs

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

clean:
	docker-compose down -v --rmi local
```

Usage :
```bash
make up      # Démarrer
make down    # Arrêter
make logs    # Voir les logs
make restart # Redémarrer
```
