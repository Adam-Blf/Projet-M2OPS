"""Module de lecture de sources de presse et production de JSON.

Ce module lit les flux RSS/Atom des sources de presse listées dans sources.csv,
parse les articles et produit un fichier JSON structuré contenant :
- titre
- extrait court
- lien
- date
- titre de presse (source)
- rubrique
"""

import csv
import feedparser
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

# Chemin vers le fichier sources.csv (racine du projet)
PROJECT_ROOT = Path(__file__).parent.parent.parent
SOURCES_CSV = PROJECT_ROOT / "sources.csv"


def load_sources(csv_path: Optional[Path] = None) -> List[Dict]:
    """Charge la liste des sources depuis sources.csv.

    Returns:
        List de dictionnaires avec: nom, type, region, acces, conditions, notes
    """
    if csv_path is None:
        csv_path = SOURCES_CSV

    sources = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sources.append(row)
    return sources


def parse_feed(url: str, timeout: int = 30) -> Optional[Dict]:
    """Parse un flux RSS/Atom et extrait les informations d'article.

    Args:
        url: URL du flux RSS ou Atom
        timeout: Délai d'attente en secondes

    Returns:
        Dictionnaire avec les articles parsed ou None en cas d'échec
    """
    try:
        feed = feedparser.parse(url, timeout=timeout)
        if feed.bozo:
            # Erreur de parsing, mais on retourne quand même ce qu'on a
            pass

        articles = []
        for entry in feed.entries:
            article = {
                "titre": getattr(entry, "title", None),
                "extrait": getattr(entry, "summary", None),
                "lien": getattr(entry, "link", None),
                "date": getattr(entry, "published_parsed", None),
                "titre_presse": getattr(feed.feed, "title", None),
                "rubrique": getattr(entry, "tags", [None])[0].term
                if getattr(entry, "tags", None)
                else None,
            }
            # S'assurer que la date est au format datetime
            if article["date"]:
                try:
                    article["date"] = datetime(
                        *article["date"][:6],
                        tzinfo=timezone.utc,
                    ).isoformat()
                except (ValueError, TypeError):
                    article["date"] = None
            articles.append(article)

        return {"feed_title": feed.feed.title if hasattr(feed, "feed") else None, "articles": articles}

    except Exception as e:
        print(f"Erreur lors du parsing du flux {url}: {e}")
        return None


def read_source(source_info: Dict) -> List[Dict]:
    """Lit une source spécifique et retourne ses articles.

    Args:
        source_info: Dictionnaire contenant les infos d'une source (lu de sources.csv)
                     Doit contenir la clé 'acces' avec l'URL du flux

    Returns:
        List d'articles structurés
    """
    url = source_info.get("acces", "")
    if not url:
        return []

    result = parse_feed(url)
    if result is None:
        return []

    return result.get("articles", [])


def read_all_sources() -> Dict[str, List[Dict]]:
    """Lit toutes les sources enregistrées et retourne un dictionnaire.

    Returns:
        Dictionnaire mapping le nom de la source vers sa liste d'articles
    """
    sources = load_sources()
    result = {}

    for source in sources:
        name = source.get("nom", "inconnu")
        articles = read_source(source)
        result[name] = articles

    return result


def write_json(articles: List[Dict], output_path: Path) -> None:
    """Écrit une liste d'articles en fichier JSON.

    Args:
        articles: Liste de dictionnaires d'articles
        output_path: Chemin du fichier de sortie
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)


def main():
    """Point d'entrée principal : lit toutes les sources et écrit le JSON."""
    all_articles = read_all_sources()

    # Output directory
    output_dir = PROJECT_ROOT / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write timestamped JSON
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_file = output_dir / f"edition_{timestamp}.json"

    # Agréger tous les articles
    all_items = []
    for name, articles in all_articles.items():
        for article in articles:
            all_items.append(
                {
                    "source": name,
                    "titre": article.get("titre"),
                    "extrait": article.get("extrait"),
                    "lien": article.get("lien"),
                    "date": article.get("date"),
                    "titre_presse": article.get("titre_presse"),
                    "rubrique": article.get("rubrique"),
                }
            )

    write_json(all_items, output_file)
    print(f"Édition écrite dans {output_file} ({len(all_items)} articles)")


if __name__ == "__main__":
    main()