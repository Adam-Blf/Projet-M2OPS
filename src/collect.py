"""Collecte quotidienne des flux (boite 1 du pipeline) vers PostgreSQL (boite 2).

Pour chaque source :
  1. verifie robots.txt (une fois par jour et par domaine, avec cache) ;
  2. GET conditionnel (ETag / Last-Modified gardes dans data/state/<source>.json) ;
  3. sauvegarde la reponse brute AVANT de la parser :
     data/raw/AAAA-MM-JJ/<source>/HHMMSS.xml.gz (ecriture atomique) ;
  4. parse et insere titre, extrait, lien, date dans `articles_bruts` ;
  5. ajoute une ligne a data/logs/fetch_log.jsonl.

L'echec d'une source ne bloque jamais les autres.

Codes de sortie : 0 = run termine (meme si des sources ont echoue),
1 = erreur de configuration ou base injoignable, 2 = toutes les sources ont echoue.

Exemples :
    python -m src.collect --limit 5
    python -m src.collect --source "Le Monde" --source "La Croix" --dry-run
"""

import argparse
import json
import os
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from src import storage
from src.reader import load_sources, parse_feed, source_id
from src.utils import (
    PARIS,
    append_jsonl,
    atomic_write_gzip,
    atomic_write_json,
    data_dir,
    log,
    now_utc,
)

USER_AGENT = os.environ.get("USER_AGENT", "RevuePresseBot/0.1 (projet etudiant EFREI M2Ops)")
TIMEOUT = float(os.environ.get("FETCH_TIMEOUT", "12"))
RETRIES = int(os.environ.get("FETCH_RETRIES", "3"))
BACKOFF = float(os.environ.get("FETCH_BACKOFF", "2"))
RETRY_STATUS = {429, 500, 502, 503, 504}


class Context:
    """Ce qui est commun a tout le run."""

    def __init__(self, root: Path, run_id: str, conn=None, sleep=time.sleep):
        self.root = root
        self.run_id = run_id
        self.conn = conn  # None = --dry-run, rien n'est ecrit en base
        self.sleep = sleep
        self.started = now_utc().astimezone(PARIS)
        self.robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    @property
    def log_file(self) -> Path:
        return self.root / "logs" / "fetch_log.jsonl"


# ---------------------------------------------------------------- robots.txt
class RobotsUnreachable(Exception):
    """robots.txt n'a pas pu etre telecharge (DNS, timeout, connexion)."""


def _load_robots(client: httpx.Client, ctx: Context, domain: str):
    """Retourne le parser robots.txt du domaine (None = tout est interdit)."""
    if domain in ctx.robots:
        if isinstance(ctx.robots[domain], RobotsUnreachable):
            raise ctx.robots[domain]
        return ctx.robots[domain]
    today = ctx.started.date().isoformat()
    cache = ctx.state_dir / "robots" / f"{domain}.json"
    cached = None
    if cache.exists():
        try:
            cached = json.loads(cache.read_text())
        except (OSError, ValueError):
            cached = None
    if not cached or cached.get("date") != today:
        try:
            resp = client.get(f"https://{domain}/robots.txt")
        except httpx.HTTPError as exc:
            # Erreur reseau : pas mise en cache disque (on reessaiera au prochain run),
            # et la source sera journalisee en erreur, pas en "interdit".
            ctx.robots[domain] = RobotsUnreachable(f"{type(exc).__name__}: {exc}")
            raise ctx.robots[domain] from exc
        cached = {"date": today, "status": resp.status_code, "body": resp.text}
        atomic_write_json(cache, cached)

    status = cached["status"]
    if not isinstance(status, int) or status >= 500 or status in (401, 403):
        # Serveur en erreur ou acces refuse : on s'abstient (prudence).
        parser = None
    else:
        parser = urllib.robotparser.RobotFileParser()
        # 404 & co : pas de robots.txt -> tout est autorise
        parser.parse(cached["body"].splitlines() if status == 200 else [])
    ctx.robots[domain] = parser
    return parser


def robots_allowed(client: httpx.Client, ctx: Context, url: str) -> bool:
    parser = _load_robots(client, ctx, urlsplit(url).netloc.lower())
    return parser is not None and parser.can_fetch(USER_AGENT, url)


# ---------------------------------------------------------------- HTTP
def fetch(client: httpx.Client, ctx: Context, url: str, state: dict) -> httpx.Response:
    """GET conditionnel avec quelques essais et un delai croissant."""
    headers = {}
    if state.get("etag"):
        headers["If-None-Match"] = state["etag"]
    if state.get("last_modified"):
        headers["If-Modified-Since"] = state["last_modified"]
    for attempt in range(1, RETRIES + 1):
        try:
            resp = client.get(url, headers=headers)
            if resp.status_code not in RETRY_STATUS or attempt == RETRIES:
                return resp
        except httpx.TransportError:
            if attempt == RETRIES:
                raise
        ctx.sleep(BACKOFF * 2 ** (attempt - 1))
    raise RuntimeError("inatteignable")  # pragma: no cover


# ---------------------------------------------------------------- une source
def process_source(client: httpx.Client, ctx: Context, source: dict) -> dict:
    """Collecte une source et retourne (et journalise) son bilan. Ne leve jamais."""
    sid = source_id(source.get("nom", "inconnu"))
    url = (source.get("acces") or "").strip()
    entry = {
        "ts": now_utc().isoformat(timespec="seconds"),
        "run_id": ctx.run_id,
        "source": source.get("nom"),
        "source_id": sid,
        "url": url,
        "status": None,
        "http_status": None,
        "duration_ms": None,
        "bytes": 0,
        "items": None,
        "items_valides": None,
        "inserted": None,
        "bozo": None,
        "raw_file": None,
        "error": None,
    }
    t0 = time.monotonic()
    try:
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL invalide : {url!r}")
        if not robots_allowed(client, ctx, url):
            entry["status"] = "skipped_robots"
            return entry

        state_file = ctx.state_dir / f"{sid}.json"
        state = json.loads(state_file.read_text()) if state_file.exists() else {}
        resp = fetch(client, ctx, url, state)
        entry["http_status"] = resp.status_code

        if resp.status_code == 304:
            entry["status"] = "not_modified"
            return entry
        if resp.status_code != 200:
            entry["status"] = "error"
            entry["error"] = f"HTTP {resp.status_code}"
            return entry

        body = resp.content
        entry["bytes"] = len(body)
        # 1) brut d'abord, tel quel
        stamp = now_utc().astimezone(PARIS)
        raw = ctx.root / "raw" / stamp.date().isoformat() / sid / f"{stamp:%H%M%S}.xml.gz"
        atomic_write_gzip(raw, body)
        entry["raw_file"] = str(raw.relative_to(ctx.root))

        # 2) parsing
        parsed = parse_feed(body)
        articles = parsed["articles"]
        entry["bozo"] = parsed["bozo"]
        entry["items"] = len(articles)
        entry["items_valides"] = sum(1 for a in articles if a["date"])

        # 3) base, puis seulement l'etat HTTP (sinon un echec base ferait perdre
        #    les articles au prochain run, qui recevrait un 304)
        if ctx.conn is not None:
            entry["inserted"] = storage.insert_articles(ctx.conn, source, articles, sid, ctx.run_id)
        atomic_write_json(
            state_file,
            {
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "updated": entry["ts"],
            },
        )
        entry["status"] = "ok"
    except Exception as exc:  # une source ne doit jamais faire tomber le run
        entry["status"] = "error"
        entry["error"] = f"{type(exc).__name__}: {exc}"
        if ctx.conn is not None:
            try:
                ctx.conn.rollback()
            except Exception:
                pass
    finally:
        entry["duration_ms"] = round((time.monotonic() - t0) * 1000)
        try:
            append_jsonl(ctx.log_file, entry)
        except OSError as exc:
            entry["log_error"] = str(exc)
        log("fetch", **{k: v for k, v in entry.items() if k != "ts"})
    return entry


# ---------------------------------------------------------------- run
def select_sources(sources: list[dict], names: list[str], limit: int | None) -> list[dict]:
    if names:
        wanted = {n.casefold() for n in names}
        sources = [s for s in sources if s.get("nom", "").casefold() in wanted]
        missing = wanted - {s["nom"].casefold() for s in sources}
        if missing:
            raise ValueError(f"source(s) absente(s) de sources.csv : {sorted(missing)}")
    return sources[:limit] if limit else sources


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Collecte quotidienne des flux de presse")
    p.add_argument("--source", action="append", default=[], help="nom exact (repetable)")
    p.add_argument("--limit", type=int, help="ne prendre que les N premieres sources")
    p.add_argument("--sources-csv", type=Path, help="autre fichier de sources")
    p.add_argument("--dry-run", action="store_true", help="ne rien ecrire en base")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    run_id = now_utc().strftime("%Y%m%dT%H%M%SZ")
    root = data_dir()
    try:
        sources = select_sources(load_sources(args.sources_csv), args.source, args.limit)
    except (OSError, ValueError) as exc:
        log("run_error", run_id=run_id, error=str(exc))
        return 1

    conn = None
    if not args.dry_run:
        try:
            conn = storage.connect()
            storage.ensure_schema(conn)
        except Exception as exc:
            log("run_error", run_id=run_id, error=f"base injoignable : {exc}".strip())
            return 1

    ctx = Context(root, run_id, conn)
    log("run_start", run_id=run_id, sources=len(sources), dry_run=args.dry_run)
    t0 = time.monotonic()
    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        follow_redirects=True,
    ) as client:
        results = [process_source(client, ctx, s) for s in sources]
    if conn is not None:
        conn.close()

    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    summary = {
        "ts": now_utc().isoformat(timespec="seconds"),
        "run_id": run_id,
        "sources": len(results),
        "statuts": counts,
        "articles_inseres": sum(r["inserted"] or 0 for r in results),
        "duration_s": round(time.monotonic() - t0, 1),
    }
    append_jsonl(root / "logs" / "runs.jsonl", summary)
    log("run_end", **{k: v for k, v in summary.items() if k != "ts"})
    if results and counts.get("error", 0) == len(results):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
