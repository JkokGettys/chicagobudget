"""Shared helpers for tree audit 2. Read-only: works on raw/treeaudit2/budget_snapshot.db
(a copy of data/budget.db taken right after build/build_all.sh on 2026-10-02).
The previous audit's snapshot (raw/treeaudit/budget_snapshot.db) is read only for the 'previous' columns."""
import json, os, sqlite3, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "raw", "treeaudit2", "budget_snapshot.db")
DB_PREV = os.path.join(ROOT, "raw", "treeaudit", "budget_snapshot.db")
OUT = os.path.join(ROOT, "raw", "treeaudit2")
M = 100_000_000  # $1M in cents
GOVS = ["city", "cps", "parks"]
BASES = ["budget", "tied", "gov_estimate", "proxy", "paid_to_date", "residual", "adjustment"]

def con(path=None):
    c = sqlite3.connect(f"file:{path or DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c

def root_of(node_id):
    return node_id.split(".")[0]

def load_nodes(path=None):
    return [dict(r) for r in con(path).execute("select * from nodes")]

def bucket(r):
    """Same rule as treelib.depth_report: a count x rate leaf whose unit is under $1M counts as under $1M."""
    a = abs(r["amount_cents"])
    if r["count"] and r["unit_amount_cents"] is not None and abs(r["unit_amount_cents"]) < M:
        return "lt1m"
    if a < M: return "lt1m"
    if a < 10 * M: return "1m_10m"
    return "ge10m"

def usd(c, d=1):
    return f"${c/100/1e6:,.{d}f}M"

def path_names(by_id, node_id, skip_root=True):
    names = []
    n = by_id.get(node_id)
    while n:
        names.append(n["name"])
        n = by_id.get(n["parent_id"]) if n["parent_id"] else None
    names.reverse()
    return " > ".join(names[1:] if skip_root else names)

def children_map(rows):
    kids = collections.defaultdict(list)
    for r in rows:
        if r["parent_id"]: kids[r["parent_id"]].append(r)
    return kids
