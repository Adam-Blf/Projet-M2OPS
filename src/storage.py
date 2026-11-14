"""Acces PostgreSQL : schema, insertion des articles, purge."""

import os
import time

import psycopg2
from psycopg2.extras import execute_values

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles_bruts (
    id            BIGSERIAL PRIMARY KEY,
    url_canonique TEXT        NOT NULL UNIQUE,
    lien          TEXT        NOT NULL,
    titre         TEXT        NOT NULL,
    extrait       TEXT        CHECK (char_length(extrait) <= 200),
    publie_le     TIMESTAMPTZ,
    rubrique      TEXT,
    titre_presse  TEXT,
    source_id     TEXT        NOT NULL,
    source        TEXT        NOT NULL,
    type          TEXT,
    region        TEXT,
    collecte_le   TIMESTAMPTZ NOT NULL DEFAULT now(),
    run_id        TEXT        NOT NULL
);
CREATE INDEX IF NOT EXISTS articles_bruts_collecte_le ON articles_bruts (collecte_le);
CREATE INDEX IF NOT EXISTS articles_bruts_source_id ON articles_bruts (source_id);
"""


def connect(retries: int = 5, delay: float = 2.0):
    """Connexion avec quelques essais (la base peut demarrer en meme temps que nous)."""
    last = None
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=os.environ.get("POSTGRES_HOST", "localhost"),
                port=int(os.environ.get("POSTGRES_PORT", "5432")),
                dbname=os.environ.get("POSTGRES_DB", "m2ops"),
                user=os.environ.get("POSTGRES_USER", "m2ops_user"),
                password=os.environ.get("POSTGRES_PASSWORD", ""),
                connect_timeout=5,
                application_name="m2ops",
            )
            conn.autocommit = False
            return conn
        except psycopg2.OperationalError as exc:
            last = exc
            if attempt < retries:
                time.sleep(delay * attempt)
    raise last


def ensure_schema(conn) -> None:
    with conn, conn.cursor() as cur:
        cur.execute(SCHEMA)


def insert_articles(conn, source: dict, articles: list[dict], source_id: str, run_id: str) -> int:
    """Insere les articles ; les URL deja connues sont ignorees. Retourne le nombre ajoute."""
    if not articles:
        return 0
    rows = [
        (
            a["url_canonique"],
            a["lien"],
            a["titre"],
            a["extrait"],
            a["date"],
            a["rubrique"],
            a["titre_presse"],
            source_id,
            source.get("nom", ""),
            source.get("type"),
            source.get("region"),
            run_id,
        )
        for a in articles
    ]
    with conn, conn.cursor() as cur:
        inserted = execute_values(
            cur,
            """
            INSERT INTO articles_bruts (url_canonique, lien, titre, extrait, publie_le,
                rubrique, titre_presse, source_id, source, type, region, run_id)
            VALUES %s
            ON CONFLICT (url_canonique) DO NOTHING
            RETURNING id
            """,
            rows,
            fetch=True,
        )
    return len(inserted)


def purge_articles(conn, days: int, dry_run: bool = False) -> int:
    """Supprime (ou compte, en dry_run) les articles collectes il y a plus de `days` jours."""
    with conn, conn.cursor() as cur:
        if dry_run:
            cur.execute(
                "SELECT count(*) FROM articles_bruts "
                "WHERE collecte_le < now() - make_interval(days => %s)",
                (days,),
            )
            return cur.fetchone()[0]
        cur.execute(
            "DELETE FROM articles_bruts WHERE collecte_le < now() - make_interval(days => %s)",
            (days,),
        )
        return cur.rowcount
