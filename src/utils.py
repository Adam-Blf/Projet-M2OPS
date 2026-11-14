"""Outils communs : chemins, ecritures atomiques, journal JSON."""

import gzip
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.reader import PROJECT_ROOT

PARIS = ZoneInfo("Europe/Paris")


def data_dir() -> Path:
    """Racine des donnees (`data/` du projet, ou DATA_DIR dans le conteneur)."""
    return Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))


def now_utc() -> datetime:
    return datetime.now(UTC)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Ecrit dans un fichier temporaire du meme dossier puis le renomme.

    Le renommage est atomique : un lecteur voit l'ancien fichier ou le nouveau,
    jamais un fichier a moitie ecrit.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def atomic_write_gzip(path: Path, data: bytes) -> None:
    # mtime=0 : meme contenu -> meme fichier compresse
    atomic_write_bytes(path, gzip.compress(data, mtime=0))


def atomic_write_json(path: Path, obj) -> None:
    atomic_write_bytes(path, json.dumps(obj, ensure_ascii=False, indent=2).encode())


def append_jsonl(path: Path, obj: dict) -> None:
    """Ajoute une ligne JSON (une seule ecriture en mode append)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def log(event: str, **fields) -> None:
    """Journal JSON sur la sortie standard (lu par `podman logs` / `kubectl logs`)."""
    line = {"ts": now_utc().isoformat(timespec="seconds"), "event": event, **fields}
    print(json.dumps(line, ensure_ascii=False), file=sys.stdout, flush=True)
