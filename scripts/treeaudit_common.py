"""Shared helpers for the tree audit. Read-only: works on raw/treeaudit/budget_snapshot.db."""
import json, os, sqlite3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "raw", "treeaudit", "budget_snapshot.db")
OUT = os.path.join(ROOT, "raw", "treeaudit")
M = 100_000_000  # $1M in cents
ROOTS = ["city", "cps", "parks", "city-twice"]

def con():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c

def root_of(node_id):
    return node_id.split(".")[0]

def load_nodes(c=None):
    c = c or con()
    rows = [dict(r) for r in c.execute("select * from nodes")]
    return rows

def bucket(r):
    """Same rule as treelib.depth_report: count x rate leaf with unit < $1M counts as < $1M."""
    a = abs(r["amount_cents"])
    if r["count"] and r["unit_amount_cents"] is not None and abs(r["unit_amount_cents"]) < M:
        return "lt1m"
    if a < M:
        return "lt1m"
    if a < 10 * M:
        return "1m_10m"
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
