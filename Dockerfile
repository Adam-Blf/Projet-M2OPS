# Image de la collecte et de la purge (meme image, deux commandes)
# -----------------------------------------------------------------
# Etage 1 : installation des dependances dans un prefixe isole
FROM docker.io/library/python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# -----------------------------------------------------------------
# Etage 2 : image finale, sans outils de build ni tests
FROM docker.io/library/python:3.12-slim

# Utilisateur non root, UID fixe (1000) pour ecrire dans le volume ./data
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app
COPY --from=builder /install /usr/local
COPY sources.csv ./
COPY src/ ./src/
RUN mkdir -p /app/data && chown appuser:appuser /app/data

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/app/data

USER appuser

# Par defaut : la collecte. La purge : python -m src.purge
CMD ["python", "-m", "src.collect"]
