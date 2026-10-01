"""Shared tree library for the Chicago budget tree.

Every box on the eventual site is a Node. Amounts are stored in integer CENTS so
that "parent == sum of children" can be checked exactly (CPS has cents).

Rules (enforced by check()):
  * a node with children has amount == sum(children amounts), exactly
  * every node has a basis and a source (inherited from parent if not set)
  * leaves >= $10M carry why_cant_go_deeper
  * side info (actual payments, vacancies...) lives in node.side, never in amount

Typical use:
    root = Node("city", "City of Chicago", gov="city")
    dept = root.add("police", "Chicago Police Department", amount=..., source=SRC)
    split(dept_line, pieces)   # attach detail; difference becomes a visible "other" child
"""
import json
import re
import sqlite3

BASES = {
    "budget",      # amount printed in the adopted budget (ordinance / budget book)
    "tied",        # a split that ties to the budget line exactly (e.g. positions x rate)
    "proxy",       # an estimate: count x average, share of dollars from another year
    "residual",    # budget line minus the itemised pieces ("other / not itemised")
    "adjustment",  # budgeted offsets: turnover, savings, the unexplained OBM deduction
}
TEN_M = 10_000_000_00  # $10M in cents


def cents(x):
    """Dollars (int, float or numeric string) -> integer cents, rounded half away from zero."""
    if isinstance(x, str):
        x = x.replace(",", "").replace("$", "").strip()
        neg = x.startswith("(") and x.endswith(")")
        x = x.strip("()")
        v = float(x)
        v = -v if neg else v
    else:
        v = float(x)
    c = round(abs(v) * 100)
    return int(c if v >= 0 else -c)


def slug(s, maxlen=48):
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return s[:maxlen] or "x"


class Node:
    __slots__ = ("id", "name", "gov", "kind", "amount", "basis", "source", "note",
                 "why", "tier", "count", "unit_amount", "unit_label", "children",
                 "parent", "side", "extra", "sort")

    def __init__(self, id, name, gov=None, kind=None, amount=None, basis=None, source=None,
                 note=None, why=None, tier=None, count=None, unit_amount=None,
                 unit_label=None, extra=None, sort=None):
        self.id = id
        self.name = name
        self.gov = gov
        self.kind = kind
        self.amount = amount          # cents; None for pure containers (computed by rollup)
        self.basis = basis
        self.source = source          # dict: {dataset|doc, url, page, note}
        self.note = note
        self.why = why                # why_cant_go_deeper
        self.tier = tier
        self.count = count
        self.unit_amount = unit_amount  # cents
        self.unit_label = unit_label    # e.g. "positions", "hours", "retirees"
        self.children = []
        self.parent = None
        self.side = []                # list of dicts: {kind,label,amount(cents),period,basis,source}
        self.extra = extra or {}
        self.sort = sort

    # ---- building -------------------------------------------------------
    def add(self, key, name, **kw):
        """Add (or return existing) child with id parent.id + '.' + slug(key)."""
        cid = f"{self.id}.{slug(key)}"
        for c in self.children:
            if c.id == cid:
                if kw.get("amount") is not None:
                    c.amount = (c.amount or 0) + kw["amount"]
                return c
        kw.setdefault("gov", self.gov)
        n = Node(cid, name, **kw)
        n.parent = self
        self.children.append(n)
        return n

    def adopt(self, node):
        node.parent = self
        self.children.append(node)
        return node

    def find(self, pred):
        out = []
        stack = [self]
        while stack:
            n = stack.pop()
            if pred(n):
                out.append(n)
            stack.extend(n.children)
        return out

    def walk(self):
        stack = [self]
        while stack:
            n = stack.pop()
            yield n
            stack.extend(reversed(n.children))

    def rollup(self):
        """Fill container amounts bottom-up. Leaves must have amounts."""
        if not self.children:
            if self.amount is None:
                raise ValueError(f"leaf without amount: {self.id}")
            return self.amount
        s = sum(c.rollup() for c in self.children)
        if self.amount is None:
            self.amount = s
        return self.amount

    def eff(self, attr):
        n = self
        while n is not None:
            v = getattr(n, attr)
            if v:
                return v
            n = n.parent
        return None


def split(line, pieces, residual_name="Other / not itemised", residual_note=None,
          residual_why=None, residual_basis="residual", allow_over=False):
    """Attach detail pieces under `line` without changing line.amount.

    pieces: list of dicts with key, name, amount (cents) and any Node kwargs.
    If the pieces sum to less than the line, a visible residual child is added.
    If they sum to more, raise (or, with allow_over, scale nothing and add a negative
    'difference' child so the mismatch is visible, never hidden).
    Returns the list of created children.
    """
    if line.amount is None:
        raise ValueError(f"split target has no amount: {line.id}")
    made = []
    for p in pieces:
        p = dict(p)
        key = p.pop("key")
        name = p.pop("name")
        made.append(line.add(key, name, **p))
    tot = sum(c.amount for c in line.children)
    diff = line.amount - tot
    if diff != 0:
        if diff < 0 and not allow_over:
            raise ValueError(f"pieces exceed line {line.id}: line {line.amount/100:,.2f} "
                             f"pieces {tot/100:,.2f}")
        name = residual_name if diff > 0 else "Difference: detail sources exceed the budget line"
        made.append(line.add("other-not-itemised" if diff > 0 else "difference",
                             name, amount=diff, basis=residual_basis if diff > 0 else "adjustment",
                             note=residual_note, why=residual_why))
    return made


# ---- checks ---------------------------------------------------------------
def check(root, expected_total_cents=None, people_names=None, verbose=True):
    """Return list of problems (empty == pass)."""
    problems = []
    ids = set()
    root.rollup()
    for n in root.walk():
        if n.id in ids:
            problems.append(f"duplicate id {n.id}")
        ids.add(n.id)
        if n.children:
            s = sum(c.amount for c in n.children)
            if s != n.amount:
                problems.append(f"sum mismatch {n.id}: node {n.amount/100:,.2f} kids {s/100:,.2f}")
        if not n.eff("basis"):
            problems.append(f"no basis {n.id}")
        elif n.basis and n.basis not in BASES:
            problems.append(f"bad basis {n.basis} at {n.id}")
        if not n.eff("source"):
            problems.append(f"no source {n.id}")
        if not n.children and abs(n.amount) >= TEN_M and not n.why and n.eff("basis") != "adjustment":
            problems.append(f"leaf >= $10M without why: {n.id} ({n.amount/100:,.0f})")
        for s in n.side:
            if "amount" in s and not isinstance(s["amount"], int):
                problems.append(f"side amount not cents at {n.id}")
    if expected_total_cents is not None and root.amount != expected_total_cents:
        problems.append(f"root total {root.amount/100:,.2f} != expected {expected_total_cents/100:,.2f}")
    if people_names:
        blob = json.dumps(to_rows(root), default=str).upper()
        hits = [nm for nm in people_names if nm and len(nm) > 6 and nm in blob]
        if hits:
            problems.append(f"{len(hits)} employee names found in tree, e.g. {hits[:3]}")
    if verbose:
        print(f"[check] {root.id}: {len(ids):,} nodes, total ${root.amount/100:,.2f}, "
              f"{len(problems)} problems")
        for p in problems[:25]:
            print("   -", p)
    return problems


def depth_report(root):
    """Share of dollars by size of the leaf the user ends on (absolute value)."""
    buckets = {"lt1m": 0, "1m_10m": 0, "ge10m": 0}
    for n in root.walk():
        if n.children:
            continue
        a = abs(n.amount)
        if n.count and n.unit_amount is not None and abs(n.unit_amount) < 1_000_000_00:
            buckets["lt1m"] += a          # count x average leaf: each unit is < $1M
        elif a < 1_000_000_00:
            buckets["lt1m"] += a
        elif a < TEN_M:
            buckets["1m_10m"] += a
        else:
            buckets["ge10m"] += a
    tot = sum(buckets.values()) or 1
    return {k: round(v / tot, 4) for k, v in buckets.items()} | {"abs_total": tot / 100}


# ---- export ---------------------------------------------------------------
def to_rows(root):
    rows = []
    for i, n in enumerate(root.walk()):
        rows.append({
            "id": n.id, "parent_id": n.parent.id if n.parent else None, "gov": n.gov,
            "kind": n.kind, "name": n.name, "amount_cents": n.amount,
            "basis": n.eff("basis"), "tier": n.tier, "count": n.count,
            "unit_amount_cents": n.unit_amount, "unit_label": n.unit_label,
            "why_cant_go_deeper": n.why, "note": n.note,
            "source": json.dumps(n.eff("source")) if n.eff("source") else None,
            "is_leaf": 0 if n.children else 1, "n_children": len(n.children),
            "depth": n.id.count("."), "sort": n.sort if n.sort is not None else i,
            "extra": json.dumps(n.extra) if n.extra else None,
        })
    return rows


def side_rows(root):
    out = []
    for n in root.walk():
        for s in n.side:
            out.append({"node_id": n.id, "kind": s.get("kind"), "label": s.get("label"),
                        "amount_cents": s.get("amount"), "period": s.get("period"),
                        "basis": s.get("basis"), "source": json.dumps(s.get("source")),
                        "extra": json.dumps({k: v for k, v in s.items() if k not in
                                             ("kind", "label", "amount", "period", "basis", "source")})})
    return out


SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY, parent_id TEXT, gov TEXT, kind TEXT, name TEXT,
  amount_cents INTEGER NOT NULL, basis TEXT, tier TEXT, count REAL,
  unit_amount_cents INTEGER, unit_label TEXT, why_cant_go_deeper TEXT, note TEXT,
  source TEXT, is_leaf INTEGER, n_children INTEGER, depth INTEGER, sort INTEGER, extra TEXT);
CREATE INDEX IF NOT EXISTS ix_nodes_parent ON nodes(parent_id);
CREATE INDEX IF NOT EXISTS ix_nodes_gov ON nodes(gov);
CREATE TABLE IF NOT EXISTS side_info (
  node_id TEXT, kind TEXT, label TEXT, amount_cents INTEGER, period TEXT, basis TEXT,
  source TEXT, extra TEXT);
CREATE INDEX IF NOT EXISTS ix_side_node ON side_info(node_id);
CREATE TABLE IF NOT EXISTS checks (gov TEXT, run_at TEXT, n_nodes INTEGER, total_cents INTEGER,
  expected_cents INTEGER, problems INTEGER, depth TEXT);
"""


def save_json(root, path):
    with open(path, "w") as f:
        json.dump({"rows": to_rows(root), "side": side_rows(root)}, f)


def load_into_db(db_path, gov, rows, side, check_row=None):
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    con.execute("DELETE FROM nodes WHERE gov=?", (gov,))
    con.execute("DELETE FROM side_info WHERE node_id LIKE ?", (gov + "%",))
    cols = list(rows[0].keys())
    con.executemany(f"INSERT INTO nodes ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                    [tuple(r[c] for c in cols) for r in rows])
    if side:
        scols = list(side[0].keys())
        con.executemany(f"INSERT INTO side_info ({','.join(scols)}) VALUES ({','.join('?'*len(scols))})",
                        [tuple(r[c] for c in scols) for r in side])
    if check_row:
        con.execute("INSERT INTO checks VALUES (?,?,?,?,?,?,?)", check_row)
    con.commit()
    con.close()
