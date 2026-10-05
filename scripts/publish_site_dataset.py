#!/usr/bin/env python3
"""Build a byte-preserving, indexed public snapshot under data/public/2026.

Run from any directory with ``python3 scripts/publish_site_dataset.py``. The
catalog describes every payload except itself (a self-hash is impossible).
"""

import gzip
import hashlib
import json
import shutil
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "data/public/2026"
SITE = REPO / "site/dist/data"
LIMIT = 50 * 1024 * 1024
ROOTS = ("city", "city-twice", "cps", "parks")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def main():
    manifest = json.loads((SITE / "manifest.json").read_bytes())
    owners = manifest["chunks"]
    expected_site = manifest["output_file_count"] + 1  # manifest itself
    site_files = sorted(p for p in SITE.rglob("*.json") if p.is_file())
    if len(site_files) != expected_site or len(owners) != manifest["counts"]["chunks"]:
        raise ValueError("Incomplete site data or chunk owner manifest")
    if len(set(owners.values())) != len(owners):
        raise ValueError("Chunk paths must have exactly one owner")
    if not all((SITE / path).is_file() for path in owners.values()):
        raise ValueError("Missing manifest chunk")

    checksums = {}
    for line in (REPO / "build/inputs.sha256").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        sha, separator, name = line.partition("  ")
        if not separator or len(sha) != 64 or not name.startswith("raw/"):
            raise ValueError(f"Invalid checksum entry: {line}")
        source = REPO / name
        if not source.is_file() or digest(source) != sha:
            raise ValueError(f"Missing or changed curated source: {name}")
        checksums[name] = sha
    if len(checksums) != 12:
        raise ValueError("Expected twelve curated checksum entries")

    people = sorted((REPO / "raw/people").glob("*.json"))
    inputs = [REPO / name for name in sorted(checksums)] + people + [
        REPO / "raw/cps/roster_12312025.xls",
        *(REPO / "data/people" / name for name in (
            "city_employees_2026.json", "cps_positions_2025q4.json",
            "parks_positions.json")),
    ]
    if not people or len(set(inputs)) != len(inputs) or not all(p.is_file() for p in inputs):
        raise ValueError("Missing or duplicate public source inputs")

    # Fully validate before touching the destination.
    by_category = {root: {} for root in ROOTS}
    lookup = {}
    for owner, chunk_path in sorted(owners.items()):
        chunk = json.loads((SITE / chunk_path).read_bytes())
        if not isinstance(chunk.get("nodes"), list):
            raise ValueError(f"Invalid chunk: {chunk_path}")
        for node in chunk["nodes"]:
            node_id = node["id"]
            root = node["root"]
            if root not in ROOTS or node_id in lookup:
                raise ValueError(f"Duplicate ID or unexpected root: {node_id}")
            # Follow parent links after collecting all nodes, since chunks need
            # not appear in ancestry order.
            entry = {"id": node_id, "parent": node["parent_id"],
                     "amount_cents": node["amount_cents"], "basis": node["basis"],
                     "source_id": node["source"],
                     "chunk": "site/" + chunk_path, "owner": owner,
                     "root": root}
            lookup[node_id] = entry
    if len(lookup) != manifest["counts"]["nodes"]:
        raise ValueError("Node count disagrees with manifest")
    roots = {node["id"] for node in lookup.values() if node["parent"] is None}
    if roots != set(ROOTS):
        raise ValueError(f"Unexpected tree roots: {sorted(roots)}")
    categories_by_id = {}
    for node_id, entry in sorted(lookup.items()):
        root = entry["root"]
        parent = entry["parent"]
        if parent is not None and (parent not in lookup or lookup[parent]["root"] != root):
            raise ValueError(f"Missing or cross-root parent: {node_id}")
        category = node_id
        seen = set()
        while lookup[category]["parent"] not in (None, root):
            if category in seen:
                raise ValueError(f"Cycle at {node_id}")
            seen.add(category)
            category = lookup[category]["parent"]
        if lookup[category]["parent"] is None:
            category = "_root"
        by_category[root].setdefault(category, []).append(entry)
        categories_by_id[node_id] = category

    sources = json.loads((SITE / "sources.json").read_bytes())
    # Provenance belongs to source IDs in the runtime source table. Preserve
    # that table unchanged and expose any direct URLs in the catalog metadata.
    urls = sorted({value for record in sources if isinstance(record, dict)
                   for value in record.values()
                   if isinstance(value, str) and value.startswith(("https://", "http://"))})
    catalog = {}
    planned = {}

    def add(path, origin, source=None, data=None, provenance=None):
        if path in planned:
            raise ValueError(f"Output collision: {path}")
        if data is not None and len(data) > LIMIT:
            raise ValueError(f"Output exceeds 50 MiB: {path}")
        if source is not None and source.stat().st_size > LIMIT:
            raise ValueError(f"Source exceeds 50 MiB: {source}")
        planned[path] = (source, data, origin, provenance)

    provenance = {
        "raw/people/emp_current.json": "https://data.cityofchicago.org/resource/xzkq-xp2w.json",
        "raw/people/vacancies.json": "https://data.cityofchicago.org/resource/9v3e-pcjs.json",
        "raw/people/ord2025_approp.json": "https://data.cityofchicago.org/resource/t59y-fr3k.json",
        "raw/cps/roster_12312025.xls": (
            "https://www.cps.edu/globalassets/cps-pages/about-cps/finance/"
            "employee-position-files/employeepositionroster_12312025.xls"),
    }
    for source in people:
        if source.name.startswith("pay") or source.name == "names_2025.json":
            provenance[source.relative_to(REPO).as_posix()] = (
                "https://data.cityofchicago.org/resource/dawh-m56b.json")
    for source in site_files:
        add("site/" + source.relative_to(SITE).as_posix(), "site/dist/data", source)
    for source in inputs:
        relative = source.relative_to(REPO)
        name = relative.as_posix()
        add("sources/" + name, name, source, provenance=provenance.get(name))
    for root, categories in by_category.items():
        for category, nodes in sorted(categories.items()):
            add(f"tree/{root}/{category}.json", "derived:site/chunks",
                data=encoded({"root": root, "category": category, "nodes": nodes}))
    lookup_output = {}
    for node_id, entry in sorted(lookup.items()):
        category = categories_by_id[node_id]
        lookup_output[node_id] = {"chunk": entry["chunk"], "root": entry["root"],
                                  "parent_id": entry["parent"],
                                  "tree": f"tree/{entry['root']}/{category}.json"}
    add("tree/lookup.json", "derived:site/chunks", data=encoded(lookup_output))
    add("tree/manifest.json", "derived:site/manifest.json",
        data=encoded({"roots": list(ROOTS), "nodes": len(lookup),
                      "chunk_owners": len(owners),
                      "categories": {r: sorted(v) for r, v in by_category.items()},
                      "sources": "site/sources.json"}))

    # Stage inside the sole allowed output tree. Replace files after all inputs
    # and size checks pass, removing leftovers from previous builds.
    DEST.mkdir(parents=True, exist_ok=True)
    stage = DEST / ".staging"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    try:
        for path, (source, data, origin, provenance) in sorted(planned.items()):
            target = stage / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if source is not None:
                shutil.copyfile(source, target)
            else:
                target.write_bytes(data)
            catalog[path] = {"path": path, "sha256": digest(target), "bytes": target.stat().st_size,
                             "origin": origin}
            if provenance:
                catalog[path]["provenance_url"] = provenance
        with (stage / "budget.db.gz").open("wb") as out:
            with gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0,
                               compresslevel=9) as compressed:
                with (REPO / "data/budget.db").open("rb") as database:
                    shutil.copyfileobj(database, compressed)
        db_gz = stage / "budget.db.gz"
        catalog["budget.db.gz"] = {"path": "budget.db.gz", "sha256": digest(db_gz),
                                   "bytes": db_gz.stat().st_size,
                                   "origin": "data/budget.db"}
        catalog["site/sources.json"]["provenance_urls"] = urls
        if any(item["bytes"] >= LIMIT for item in catalog.values()):
            raise ValueError("Output exceeds 50 MiB")
        (stage / "catalog.json").write_bytes(encoded({"files": [catalog[k] for k in sorted(catalog)],
                                                       "file_count": len(catalog)}))
        if (stage / "catalog.json").stat().st_size > LIMIT:
            raise ValueError("Catalog exceeds 50 MiB")
        for existing in DEST.iterdir():
            if existing == stage:
                continue
            if existing.is_dir():
                shutil.rmtree(existing)
            else:
                existing.unlink()
        for generated in stage.iterdir():
            generated.rename(DEST / generated.name)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(f"Published {len(catalog)} payloads and catalog to {DEST}")


if __name__ == "__main__":
    main()
