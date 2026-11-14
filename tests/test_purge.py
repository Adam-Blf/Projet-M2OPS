"""Tests de la purge des fichiers (la purge en base est testee via compose)."""

import json
from datetime import UTC, date, datetime, timedelta

from src.purge import purge_jsonl, purge_raw


def test_purge_raw_garde_les_7_derniers_jours(tmp_path):
    today = date(2026, 11, 14)
    for delta in (10, 8, 7, 2, 0):
        d = tmp_path / "raw" / (today - timedelta(days=delta)).isoformat() / "src"
        d.mkdir(parents=True)
        (d / "080000.xml.gz").write_bytes(b"x")
    (tmp_path / "raw" / "pas-une-date").mkdir()

    removed = purge_raw(tmp_path, today - timedelta(days=7))

    assert removed == ["2026-11-04", "2026-11-06"]
    restants = sorted(p.name for p in (tmp_path / "raw").iterdir())
    assert restants == ["2026-11-07", "2026-11-12", "2026-11-14", "pas-une-date"]


def test_purge_raw_dry_run_ne_supprime_rien(tmp_path):
    (tmp_path / "raw" / "2020-01-01").mkdir(parents=True)
    assert purge_raw(tmp_path, date(2026, 1, 1), dry_run=True) == ["2020-01-01"]
    assert (tmp_path / "raw" / "2020-01-01").exists()


def test_purge_jsonl(tmp_path):
    now = datetime(2026, 11, 14, 12, tzinfo=UTC)
    f = tmp_path / "fetch_log.jsonl"
    lines = [
        {"ts": (now - timedelta(days=10)).isoformat(), "n": 1},
        {"ts": (now - timedelta(days=2)).isoformat(), "n": 2},
    ]
    f.write_text("\n".join(json.dumps(x) for x in lines) + "\nligne cassee\n")

    assert purge_jsonl(f, now - timedelta(days=7)) == 1
    restant = f.read_text().splitlines()
    assert json.loads(restant[0])["n"] == 2
    assert restant[1] == "ligne cassee"
