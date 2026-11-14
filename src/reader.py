"""Lecture de sources.csv et parsing des flux RSS/Atom.

On ne garde que ce que la note de cadrage autorise : titre, extrait court
(200 caracteres au plus), lien, date, titre de presse et rubrique. Le texte
integral (`content:encoded`, `content`) et les auteurs sont ignores.
"""

import csv
import html
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCES_CSV = PROJECT_ROOT / "sources.csv"

EXTRAIT_MAX = 200
_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")
# Parametres de suivi retires pour obtenir l'URL canonique (deduplication)
_TRACKING = ("utm_", "xtor", "at_", "fbclid", "gclid")


def load_sources(csv_path: Path | None = None) -> list[dict]:
    """Charge les sources depuis sources.csv (colonnes nom, type, region, acces...)."""
    with open(csv_path or SOURCES_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def source_id(nom: str) -> str:
    """Identifiant sans accent : "L'Est Republicain" -> "l-est-republicain"."""
    ascii_nom = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_nom.lower()).strip("-")


def clean_text(value: str | None) -> str:
    """Retire les balises HTML et les entites, et compacte les espaces."""
    if not value:
        return ""
    return _SPACES.sub(" ", html.unescape(_TAG.sub(" ", value))).strip()


def truncate(text: str, max_len: int = EXTRAIT_MAX) -> str:
    """Coupe a max_len caracteres au plus, sur une fin de mot, avec une ellipse."""
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:.") + "…"


def canonical_url(url: str) -> str:
    """URL sans fragment ni parametres de suivi, hote en minuscules."""
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING)
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(query), "")
    )


def _entry_date(entry) -> str | None:
    """Date de publication en ISO 8601 UTC (feedparser rend deja de l'UTC)."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    try:
        return datetime(*parsed[:6], tzinfo=UTC).isoformat()
    except (TypeError, ValueError):
        return None


def parse_feed(content: bytes | str) -> dict:
    """Parse le contenu d'un flux deja telecharge (aucun appel reseau ici).

    Retourne le titre du flux, l'etat `bozo` de feedparser et la liste des
    articles qui ont au moins un titre et un lien.
    """
    feed = feedparser.parse(content)
    feed_title = clean_text(feed.feed.get("title")) or None
    articles = []
    for entry in feed.entries:
        titre = clean_text(entry.get("title"))
        lien = (entry.get("link") or "").strip()
        if not titre or not lien:
            continue
        tags = entry.get("tags") or []
        articles.append(
            {
                "titre": titre,
                # `summary` seulement : jamais `content`, et toujours tronque
                "extrait": truncate(clean_text(entry.get("summary"))) or None,
                "lien": lien,
                "url_canonique": canonical_url(lien),
                "date": _entry_date(entry),
                "titre_presse": feed_title,
                "rubrique": clean_text(tags[0].get("term")) or None if tags else None,
            }
        )
    bozo_exc = feed.get("bozo_exception")
    return {
        "feed_title": feed_title,
        "bozo": bool(feed.get("bozo")),
        "bozo_exception": str(bozo_exc) if bozo_exc else None,
        "articles": articles,
    }
