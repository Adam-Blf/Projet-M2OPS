# Dockerfile M2Ops - Multi-stage build avec Podman/Docker
# ---------------------------------------------------------
# Étage 1 : Build de l'application
FROM python:3.12-slim AS builder

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd --create-home --shell /bin/bash appuser

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances d'abord (mise en cache Docker)
COPY requirements.txt ./

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY src/ ./src/
COPY tests/ ./tests/

# Générer les fixtures si nécessaire
RUN python -m pytest tests/ --co

# ---------------------------------------------------------
# Étage 2 : Image de production finale (très petite)
FROM python:3.12-slim AS production

# Installer seulement les dépendances runtime nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root (même uid que dans builder)
RUN useradd --create-home --shell /bin/bash appuser

# Définir le répertoire de travail
WORKDIR /app

# Copier uniquement les fichiers nécessaires depuis l'étage builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/src ./src
COPY --from=builder /app/tests ./tests
COPY --from=builder /app/requirements.txt ./

# Passer à l'utilisateur non-root
USER appuser

# Exposer le port d'application (si besoin)
EXPOSE 8000

# Commande par défaut
CMD ["python", "-m", "src.reader"]