"""Purge des donnees de plus de N jours (7 par defaut, RETENTION_DAYS).

Supprime :
  - les articles de `articles_bruts` collectes il y a plus de N jours ;
  - les dossiers data/raw/AAAA-MM-JJ plus anciens que N jours ;
  - les lignes des journaux data/logs/*.jsonl plus anciennes que N jours.

Exemples :
    python -m src.purge
    python -m src.purge --days 7 --dry-run
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from src import storage
from src.utils import PARIS, atomic_write_bytes, data_dir, log, now_utc

_DAY_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def purge_raw(root: Path, cutoff: date, dry_run: bool = False) -> list[str]:
    """Supprime data/raw/<jour> pour tout jour strictement anterieur a `cutoff`."""
    raw = root / "raw"
    removed = []
    if not raw.is_dir():
        return removed
    for d in sorted(raw.iterdir()):
        if not (d.is_dir() and _DAY_DIR.match(d.name)):
            continue  # on ne touche qu'aux dossiers dates
        if date.fromisoformat(d.name) < cutoff:
            if not dry_run:
                shutil.rmtree(d)
            removed.append(d.name)
    return removed


def purge_jsonl(path: Path, cutoff: datetime, dry_run: bool = False) -> int:
    """Retire les lignes dont `ts` est anterieur a `cutoff` ; reecriture atomique."""
    if not path.exists():
        return 0
    kept, dropped = [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            ts = datetime.fromisoformat(json.loads(line)["ts"])
        except (ValueError, KeyError, TypeError):
            kept.append(line)  # ligne illisible : on la garde plutot que la perdre
            continue
        if ts < cutoff:
            dropped += 1
        else:
            kept.append(line)
    if dropped and not dry_run:
        atomic_write_bytes(path, ("\n".join(kept) + "\n" if kept else "").encode())
    return dropped


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Purge des donnees anciennes")
    p.add_argument("--days", type=int, default=int(os.environ.get("RETENTION_DAYS", "7")))
    p.add_argument("--dry-run", action="store_true", help="compter sans supprimer")
    p.add_argument("--no-db", action="store_true", help="ne purger que les fichiers")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.days < 1:
        log("purge_error", error="--days doit valoir au moins 1")
        return 1
    root = data_dir()
    now = now_utc()
    cutoff_dt = now - timedelta(days=args.days)
    cutoff_day = now.astimezone(PARIS).date() - timedelta(days=args.days)

    articles = None
    if not args.no_db:
        try:
            conn = storage.connect()
            storage.ensure_schema(conn)
            articles = storage.purge_articles(conn, args.days, dry_run=args.dry_run)
            conn.close()
        except Exception as exc:
            log("purge_error", error=f"base : {exc}".strip())
            return 1

    try:
        raw_days = purge_raw(root, cutoff_day, args.dry_run)
        log_lines = {
            p.name: purge_jsonl(p, cutoff_dt, args.dry_run)
            for p in sorted((root / "logs").glob("*.jsonl"))
        }
    except OSError as exc:
        log("purge_error", error=str(exc))
        return 1

    log(
        "purge_end",
        days=args.days,
        dry_run=args.dry_run,
        articles_supprimes=articles,
        dossiers_bruts_supprimes=raw_days,
        lignes_journal_supprimees=log_lines,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
