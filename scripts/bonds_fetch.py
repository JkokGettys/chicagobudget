#!/usr/bin/env python3
"""List and download City of Chicago bond disclosure documents from BondLink.

BondLink issuer pages (cityofchicagoinvestors.com) embed every document of the
page in a meta tag id="__PAGE_DATA__" (attribute data-pagedata, HTML-entity
encoded JSON). Each document carries props.documents[].data.record.data.document
.uploadResponse.uri, which is a path on https://bondlink-cdn.com/ that plain curl
can fetch. The page itself needs a browser User-Agent.

Usage:
  python3 scripts/bonds_fetch.py list [issuer ...]      # print documents
  python3 scripts/bonds_fetch.py get                    # download the documents this project parses
  python3 scripts/bonds_fetch.py get <issuer> <substring-of-viewName-or-uri> [...]

Downloads go to raw/bonds/ (gitignored). Existing files are kept.
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw" / "bonds"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
BASE = "https://www.cityofchicagoinvestors.com"
CDN = "https://bondlink-cdn.com/"

ISSUERS = {
    "ohare": "/ohareairportbonds/documents/downloads/i1411",
    "midway": "/midwayairportbonds/documents/downloads/i1414",
    "water": "/waterbonds/documents/downloads/i1407",
    "wastewater": "/wastewaterbonds/documents/downloads/i1408",
    "go": "/generalobligationbonds/documents/downloads/i1398",
    "city": "/city-of-chicago-il/documents/downloads/i125",
}

# (issuer, uri, local file name). Chosen as the most recent statement of each credit
# that prints a debt service table for all outstanding bonds, plus the ones used
# for per-series cross-checks.
WANTED = [
    ("ohare", "1348/ILChicago07a-FIN.1Lay3BJv8.pdf", "ohare_2026CD_OS.pdf"),
    ("ohare", "1348/ILChicago06a-FIN.MLCK3FoI1.pdf", "ohare_2026B_OS.pdf"),
    ("ohare", "1348/O-Hare-International-Airport-Financial-Statement-2025.0sROg23GQ.pdf", "ohare_FS2025.pdf"),
    ("midway", "1351/Official-Statement.02duRik1H.pdf", "midway_2025AB_OS.pdf"),
    ("midway", "1351/Midway-International-Airport-Financial-Statement-2025.4TGhWWzsT.pdf", "midway_FS2025.pdf"),
    ("water", "1344/ILChicago04a-FIN.yO9Z1Tmxh.pdf", "water_2026ABC_OS.pdf"),
    ("water", "1344/Supplement-to-OS-2026.07.24.E7XaunPxG.pdf", "water_2026_supplement.pdf"),
    ("water", "1344/Water-Fund-Financial-Statement-2025.DkesDt8Gu.pdf", "water_FS2025.pdf"),
    ("wastewater", "1345/OS.5X3PYWIM0.pdf", "wastewater_2024B_OS.pdf"),
    ("wastewater", "1345/Sewer-Fund-Financial-Statements-2025.vcXRD2uoM.pdf", "sewer_FS2025.pdf"),
    ("go", "1338/ILChicago02a-FIN.D8Ebm0ZNE.pdf", "go_2026AB_OS.pdf"),
    ("go", "1338/OS.GE3zX31VR.pdf", "go_2025AE_OS.pdf"),
    ("go", "1338/OS.Uxunte2ez.pdf", "go_2025FG_OS.pdf"),
    ("go", "1338/FY2025-ACFR---City-of-Chicago.0TRW97g9Y.pdf", "acfr_fy2025.pdf"),
]


def curl(url, out=None):
    cmd = ["curl", "-sL", "--fail", "-A", UA, "--retry", "3", url]
    if out:
        cmd += ["-o", str(out)]
        subprocess.run(cmd, check=True)
        return None
    return subprocess.run(cmd, check=True, capture_output=True).stdout.decode("utf-8", "replace")


def list_documents(issuer):
    """Return a list of dicts: date, category, uri, name, size."""
    page = curl(BASE + ISSUERS[issuer])
    m = re.search(r'id="__PAGE_DATA__"[^>]*data-pagedata="([^"]*)"', page)
    if not m:
        m = re.search(r'data-pagedata="([^"]*)"[^>]*id="__PAGE_DATA__"', page)
    if not m:
        raise RuntimeError("no __PAGE_DATA__ on %s page" % issuer)
    data = json.loads(html.unescape(m.group(1)))
    out = []
    for item in data["props"]["documents"]:
        rec = item["data"]["record"]["data"]
        doc = rec["document"]
        up = doc["uploadResponse"]
        out.append({
            "date": doc["mediaDate"]["date"],
            "category": rec["category"]["name"],
            "uri": up["uri"],
            "name": up.get("viewName"),
            "size": up.get("fileSize"),
        })
    return out


def download(uri, name):
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / name
    if dest.exists() and dest.stat().st_size > 0:
        print("keep", dest.name)
        return dest
    curl(CDN + uri, dest)
    head = dest.read_bytes()[:5]
    if head != b"%PDF-":
        dest.unlink()
        raise RuntimeError("not a PDF: " + uri)
    print("got ", dest.name, dest.stat().st_size)
    return dest


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "list"
    if cmd == "list":
        for iss in (argv[2:] or ISSUERS):
            print("=====", iss)
            for d in list_documents(iss):
                print(d["date"], "|", d["category"][:24], "|", d["uri"], "|", (d["name"] or "")[:110])
    elif cmd == "manifest":
        # map every local PDF name to its CDN url, for citations
        RAW.mkdir(parents=True, exist_ok=True)
        m = {}
        for iss in ISSUERS:
            for d in list_documents(iss):
                m[Path(d["uri"]).name] = {"url": CDN + d["uri"], "title": d["name"], "date": d["date"], "issuer": iss}
        for iss, uri, name in WANTED:
            m[name] = {"url": CDN + uri, "title": name, "issuer": iss}
        (RAW / "manifest.json").write_text(json.dumps(m, indent=1))
        print("manifest entries", len(m))
    elif cmd == "get" and len(argv) == 2:
        for iss, uri, name in WANTED:
            download(uri, name)
    elif cmd == "get":
        iss, needles = argv[2], argv[3:]
        for d in list_documents(iss):
            if any(n.lower() in (d["uri"] + " " + (d["name"] or "")).lower() for n in needles):
                download(d["uri"], Path(d["uri"]).name)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
