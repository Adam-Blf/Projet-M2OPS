"""Tests de la collecte avec un faux serveur HTTP (httpx.MockTransport), sans reseau."""

import gzip
import json
from pathlib import Path

import httpx

from src import collect

FIXTURE = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_bytes()
SOURCE = {
    "nom": "Gazette Test",
    "type": "PQN",
    "region": "National",
    "acces": "https://news.example/rss",
}


def make_client(handler):
    return httpx.Client(
        transport=httpx.MockTransport(handler), headers={"User-Agent": collect.USER_AGENT}
    )


def make_ctx(tmp_path):
    return collect.Context(tmp_path, "test-run", conn=None, sleep=lambda s: None)


def feed_server(robots="User-agent: *\nAllow: /\n", etag='"v1"'):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        if request.headers.get("If-None-Match") == etag:
            return httpx.Response(304)
        return httpx.Response(200, content=FIXTURE, headers={"ETag": etag})

    return handler, calls


def read_log(tmp_path):
    return [json.loads(x) for x in (tmp_path / "logs" / "fetch_log.jsonl").read_text().splitlines()]


def test_collecte_puis_304(tmp_path):
    handler, calls = feed_server()
    ctx = make_ctx(tmp_path)
    with make_client(handler) as client:
        first = collect.process_source(client, ctx, SOURCE)
        second = collect.process_source(client, ctx, SOURCE)

    assert first["status"] == "ok" and first["items"] == 2 and first["items_valides"] == 2
    raw = tmp_path / first["raw_file"]
    assert gzip.decompress(raw.read_bytes()) == FIXTURE  # brut garde tel quel
    assert raw.name.endswith(".xml.gz") and "gazette-test" in str(raw)
    assert json.loads((tmp_path / "state" / "gazette-test.json").read_text())["etag"] == '"v1"'

    assert second["status"] == "not_modified" and second["http_status"] == 304
    assert calls[-1].headers["If-None-Match"] == '"v1"'
    assert calls[-1].headers["User-Agent"].startswith("RevuePresseBot/")
    # robots.txt lu une seule fois pour les deux appels
    assert sum(1 for c in calls if c.url.path == "/robots.txt") == 1
    assert [e["status"] for e in read_log(tmp_path)] == ["ok", "not_modified"]
    assert not list(tmp_path.rglob("*.tmp"))


def test_robots_interdit(tmp_path):
    handler, calls = feed_server(robots="User-agent: *\nDisallow: /\n")
    with make_client(handler) as client:
        r = collect.process_source(client, make_ctx(tmp_path), SOURCE)
    assert r["status"] == "skipped_robots"
    assert all(c.url.path == "/robots.txt" for c in calls)


def test_timeout_journalise_sans_lever(tmp_path):
    attempts = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        attempts.append(request)
        raise httpx.ConnectTimeout("trop lent", request=request)

    with make_client(handler) as client:
        r = collect.process_source(client, make_ctx(tmp_path), SOURCE)
    assert r["status"] == "error" and "ConnectTimeout" in r["error"]
    assert len(attempts) == collect.RETRIES
    assert read_log(tmp_path)[0]["status"] == "error"


def test_url_invalide(tmp_path):
    handler, _ = feed_server()
    with make_client(handler) as client:
        r = collect.process_source(client, make_ctx(tmp_path), {"nom": "X", "acces": "pas-une-url"})
    assert r["status"] == "error" and "URL invalide" in r["error"]


def test_select_sources():
    sources = [{"nom": "A"}, {"nom": "B"}, {"nom": "C"}]
    assert collect.select_sources(sources, [], 2) == sources[:2]
    assert collect.select_sources(sources, ["c"], None) == [{"nom": "C"}]


def test_domaine_injoignable_est_une_erreur(tmp_path):
    def handler(request):
        raise httpx.ConnectError("nom inconnu", request=request)

    with make_client(handler) as client:
        r = collect.process_source(client, make_ctx(tmp_path), SOURCE)
    assert r["status"] == "error" and "RobotsUnreachable" in r["error"]
    assert not (tmp_path / "state" / "robots").exists()  # pas de cache d'une panne
