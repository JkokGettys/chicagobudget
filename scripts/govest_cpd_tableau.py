#!/usr/bin/env python3
"""Fetch the public tables behind the CPD Overtime Dashboard (Tableau, analytics.chicagopolice.org) into
raw/govest/cpd_dashboard_<sheet>.json. Uses startSession/viewing + bootstrapSession and decodes the
dataSegments. Public dashboard, no names. Needs: python3 requests."""
import json, os, re, sys, requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "raw", "govest")
BASE = "https://analytics.chicagopolice.org"
WB = "PublicOvertimeSpendingDraft"
H = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/124"}
SHEETS = {"DistrictBudgets": "District Budgets", "BudgetandSpendingptI": "Budget and Spending pt I",
          "BudgetandSpendingptII": "Budget and Spending pt II"}


def parse_chunks(t):
    """Tableau bootstrap response: '<len>;<json><len>;<json>' repeated."""
    out, i = [], 0
    while i < len(t):
        j = t.index(";", i)
        n = int(t[i:j]); out.append(json.loads(t[j + 1:j + 1 + n])); i = j + 1 + n
    return out


def fetch(view, sheet):
    s = requests.Session()
    s.get(f"{BASE}/views/{WB}/{view}", params={":embed": "y", ":showVizHome": "no"}, headers=H)
    d = {"renderMapsClientSide": "true", "isBrowserRendering": "true", "browserRenderingThreshold": "100",
         "formatDataValueLocally": "false", "clientNum": "", "navType": "Nav", "navSrc": "Top", "devicePixelRatio": "1",
         "clientRenderPixelLimit": "25000000", "sheet_id": sheet, "filterTileSize": "200", "locale": "en_US",
         "language": "en", "verboseMode": "false", ":session_feature_flags": "{}", "keychain_version": "1"}
    r = s.post(f"{BASE}/vizql/w/{WB}/v/{view}/startSession/viewing", data=d, headers=H)
    cfg = r.json()
    sid, root = cfg["sessionid"], cfg["vizql_root"]
    r2 = s.post(f"{BASE}{root}/bootstrapSession/sessions/{sid}", data={"sheet_id": sheet}, headers=H)
    chunks = parse_chunks(r2.text)
    return cfg, chunks


if __name__ == "__main__":
    for view, sheet in SHEETS.items():
        cfg, chunks = fetch(view, sheet)
        path = os.path.join(OUT, f"cpd_dashboard_{view}.json")
        json.dump({"cfg_keys": list(cfg.keys()), "chunks": chunks}, open(path, "w"))
        print(view, len(chunks), os.path.getsize(path))
