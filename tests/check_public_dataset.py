#!/usr/bin/env python3
"""Verify GitHub's versioned data snapshot against the deployed-site build inputs."""
from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/public/2026"
SITE = ROOT / "site/dist/data"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check() -> None:
    catalog = json.loads((RELEASE / "catalog.json").read_text())
    manifest = json.loads((SITE / "manifest.json").read_text())
    site_files = {p.relative_to(SITE) for p in SITE.rglob("*.json")}
    release_files = {p.relative_to(RELEASE / "site") for p in (RELEASE / "site").rglob("*.json")}
    assert site_files == release_files, (len(site_files), len(release_files), site_files ^ release_files)
    assert len(site_files) == 352, len(site_files)
    for path in site_files:
        assert digest(SITE / path) == digest(RELEASE / "site" / path), path

    entries = catalog["files"]
    assert entries and len({entry["path"] for entry in entries}) == len(entries)
    all_files = {str(path.relative_to(RELEASE)) for path in RELEASE.rglob("*") if path.is_file()}
    assert all_files - {"catalog.json"} == {entry["path"] for entry in entries}, "unlisted or missing files"
    for entry in entries:
        path = RELEASE / entry["path"]
        assert path.stat().st_size == entry["bytes"], entry["path"]
        assert digest(path) == entry["sha256"], entry["path"]
        assert path.stat().st_size < 50 * 1024 * 1024, entry["path"]
        if entry["path"].startswith("sources/"):
            original = ROOT / entry["origin"]
            assert original.is_file() and digest(original) == digest(path), entry["path"]

    lookup = json.loads((RELEASE / "tree/lookup.json").read_text())
    seen = set()
    for owner, chunk_path in manifest["chunks"].items():
        nodes = json.loads((SITE / chunk_path).read_text())["nodes"]
        assert owner in {node["id"] for node in nodes}, owner
        for node in nodes:
            identifier = node["id"]
            assert identifier not in seen, identifier
            seen.add(identifier)
            pointer = lookup[identifier]
            assert pointer["chunk"] == f"site/{chunk_path}", identifier
            assert pointer["root"] == node["root"], identifier
            assert pointer["parent_id"] == node["parent_id"], identifier
            tree_path = RELEASE / pointer["tree"]
            assert tree_path.is_file(), tree_path
    assert seen == set(lookup), "lookup does not cover every box"
    assert len(seen) == manifest["counts"]["nodes"] == 47360
    assert len(manifest["chunks"]) == manifest["counts"]["chunks"] == 296
    assert {node["root"] for chunk in manifest["chunks"].values()
            for node in json.loads((SITE / chunk).read_text())["nodes"]} == {"city", "city-twice", "cps", "parks"}

    gz = RELEASE / "budget.db.gz"
    with gzip.open(gz, "rb") as compressed:
        h = hashlib.sha256()
        for chunk in iter(lambda: compressed.read(1024 * 1024), b""):
            h.update(chunk)
    assert h.hexdigest() == digest(ROOT / "data/budget.db"), "database archive differs"
    with sqlite3.connect(ROOT / "data/budget.db") as db:
        assert db.execute("select count(*) from nodes").fetchone()[0] == len(seen)
        assert db.execute("pragma integrity_check").fetchone()[0] == "ok"
    print(f"Verified {len(site_files)} complete site data files, {len(seen)} indexed boxes, "
          f"{len(manifest['chunks'])} chunks, {len(entries)} checksummed publication files")


if __name__ == "__main__":
    try:
        check()
    except (AssertionError, KeyError, OSError, ValueError) as error:
        print(f"Public dataset check failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
