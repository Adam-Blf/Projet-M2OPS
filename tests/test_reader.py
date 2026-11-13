"""Tests unitaires pour le module reader."""

import pytest

from src.reader import load_sources, read_source, read_all_sources


def test_load_sources_returns_list():
    """test_load_sources_returns_list"""
    sources = load_sources()
    assert isinstance(sources, list)
    assert len(sources) > 0


def test_sources_have_required_fields():
    """test_sources_have_required_fields"""
    sources = load_sources()
    for source in sources:
        assert "nom" in source, f"Source missing 'nom': {source}"
        assert "acces" in source, f"Source missing 'acces': {source}"


def test_read_source_returns_list():
    """test_read_source_returns_list"""
    sources = load_sources()
    if sources:
        first_source = sources[0]
        articles = read_source(first_source)
        assert isinstance(articles, list)


def test_read_all_sources_returns_dict():
    """test_read_all_sources_returns_dict"""
    result = read_all_sources()
    assert isinstance(result, dict)
    assert len(result) > 0