"""Tests du parsing, sans reseau (fixtures dans tests/fixtures/)."""

from pathlib import Path

from src.reader import (
    EXTRAIT_MAX,
    canonical_url,
    load_sources,
    parse_feed,
    source_id,
    truncate,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_sources_trouve_le_csv():
    sources = load_sources()
    assert len(sources) > 0
    for s in sources:
        assert s["nom"] and s["acces"].startswith("http")


def test_parse_fixture_simple():
    parsed = parse_feed((FIXTURES / "sample_feed.xml").read_bytes())
    assert parsed["feed_title"] == "La Gazette de Test"
    assert parsed["bozo"] is False
    assert [a["titre"] for a in parsed["articles"]] == ["Titre de test 1", "Titre de test 2"]
    premier = parsed["articles"][0]
    assert premier["lien"] == "https://example.com/article1"
    assert premier["date"] == "2026-11-13T09:00:00+00:00"  # 10h +01:00 -> 9h UTC


def test_parse_fixture_cas_limites():
    parsed = parse_feed((FIXTURES / "feed_complet.xml").read_bytes())
    articles = parsed["articles"]
    # l'article sans lien est ecarte, celui sans date est garde
    assert [a["titre"] for a in articles] == [
        "Un article avec du HTML et un long extrait",
        "Article sans date",
    ]
    long = articles[0]
    assert len(long["extrait"]) <= EXTRAIT_MAX
    assert long["extrait"].endswith("…")
    assert "<" not in long["extrait"]
    assert long["rubrique"] == "Politique"
    assert long["titre_presse"] == "Journal & Fixture"
    assert long["url_canonique"] == "https://example.com/article-long?id=42"
    assert articles[1]["date"] is None
    # ni texte integral ni auteur dans ce qu'on garde
    tout = repr(articles)
    assert "TEXTE INTEGRAL" not in tout
    assert "Auteur" not in tout


def test_truncate_et_source_id():
    assert truncate("court") == "court"
    assert len(truncate("mot " * 100)) <= EXTRAIT_MAX
    assert source_id("L'Est Républicain") == "l-est-republicain"
    assert canonical_url("HTTPS://A.fr/x?xtor=RSS-1#f") == "https://a.fr/x"
