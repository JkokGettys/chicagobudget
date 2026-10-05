#!/usr/bin/env python3
"""Verify or package the pinned gitignored raw inputs, with path-safe ZIP extraction."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'build/inputs.sha256'
PUBLIC_SOURCES = ROOT / 'data/public/2026/sources'
ROSTERS = ('data/people/city_employees_2026.json',
           'data/people/cps_positions_2025q4.json',
           'data/people/parks_positions.json')


def entries():
    for line in MANIFEST.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        digest, relative = line.split('  ', 1)
        path = Path(relative)
        if not relative.startswith('raw/') or path.is_absolute() or '..' in path.parts:
            raise ValueError(f'unsafe manifest path: {relative}')
        yield digest, relative


def verify():
    missing = []
    for digest, relative in entries():
        path = ROOT / relative
        if not path.is_file():
            missing.append(relative)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'checksum mismatch: {relative}')
    return missing


def restore_published(missing):
    """Recover pinned raw inputs from the checked-in, byte-preserving snapshot."""
    expected = dict((relative, digest) for digest, relative in entries())
    for relative in missing:
        source = PUBLIC_SOURCES / relative
        if not source.is_file():
            raise ValueError(f'published input is missing: {relative}')
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected[relative]:
            raise ValueError(f'published input checksum mismatch: {relative}')
    for relative in missing:
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PUBLIC_SOURCES / relative, destination)


def restore_rosters():
    """Restore reviewed public roster inputs and verify catalog hashes first."""
    missing = [relative for relative in ROSTERS if not (ROOT / relative).is_file()]
    if not missing:
        return
    catalog = ROOT / 'data/public/2026/catalog.json'
    entries_by_path = {item['path']: item for item in json.loads(catalog.read_text())['files']}
    for relative in missing:
        source = PUBLIC_SOURCES / relative
        entry = entries_by_path.get('sources/' + relative)
        if not source.is_file() or entry is None or entry['origin'] != relative:
            raise ValueError(f'published roster is missing: {relative}')
        if source.stat().st_size != entry['bytes'] or hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'published roster checksum mismatch: {relative}')
    for relative in missing:
        destination = ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PUBLIC_SOURCES / relative, destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['verify', 'package', 'fetch'])
    parser.add_argument('--archive', default='raw-inputs-2026-10.zip')
    parser.add_argument('--url', default=os.environ.get('CHICAGO_BUDGET_INPUTS_URL'))
    args = parser.parse_args()
    missing = verify()
    if args.action == 'fetch' and missing:
        if not args.url:
            restore_published(missing)
        else:
            if not args.url.startswith('https://'):
                parser.error('release URL must use HTTPS')
            archive = ROOT / 'build' / args.archive
            urllib.request.urlretrieve(args.url, archive)
            expected = (ROOT / 'build/inputs-archive.sha256').read_text().split()[0]
            if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
                raise ValueError('release ZIP checksum mismatch')
            with zipfile.ZipFile(archive) as z:
                allowed = {p for _, p in entries()}
                if set(z.namelist()) != allowed:
                    raise ValueError('release ZIP file list differs from manifest')
                for item in z.infolist():
                    target = ROOT / item.filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(item) as src, target.open('wb') as dest:
                        shutil.copyfileobj(src, dest)
        missing = verify()
    if missing:
        raise SystemExit('missing raw inputs: ' + ', '.join(missing))
    if args.action == 'fetch':
        restore_rosters()
    if args.action == 'package':
        archive = ROOT / 'build' / args.archive
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for _, relative in entries():
                z.write(ROOT / relative, relative)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (ROOT / 'build/inputs-archive.sha256').write_text(f'{digest}  {archive.name}\n')
        print(f'{archive}: sha256 {digest}')
    print(f'{args.action}: {len(list(entries()))} inputs verified')


if __name__ == '__main__':
    main()
