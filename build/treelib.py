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
    "paid_to_date",  # money actually paid so far this year (partial year), shown inside its budget line
    "gov_estimate",  # an estimate published by the government itself (e.g. a projection in an official report)
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


# ---- generic split files ---------------------------------------------------
def _add_piece(parent, p, default_basis, src):
    """Add one piece (dict, dollars) and its nested children under parent. Returns the node."""
    kids = p.get("children") or []
    n = parent.add(p.get("key") or p["name"], p["name"], amount=cents(p["amount"]),
                   basis=p.get("basis") or default_basis, kind=p.get("kind") or "piece",
                   count=p.get("count"), unit_amount=cents(p["unit_amount"]) if p.get("unit_amount") is not None else None,
                   unit_label=p.get("unit_label"), why=p.get("why"), note=p.get("note"),
                   source=p.get("source") or src, extra=p.get("extra"))
    if kids:
        for k in kids:
            _add_piece(n, k, p.get("basis") or default_basis, p.get("source") or src)
        s = sum(c.amount for c in n.children)
        if s < n.amount:
            n.add("other", p.get("children_residual_name", "Other / not itemised"), amount=n.amount - s,
                  basis="residual", why=p.get("children_residual_why"))
        elif s > n.amount:
            raise ValueError(f"children exceed piece {n.id}: {s/100:,.2f} > {n.amount/100:,.2f}")
    return n


def apply_split_file(path, resolve, log=print):
    """Apply a split file (format in build/SPLITS.md).

    resolve(target_dict) -> Node or None. Each split's pieces must fit inside the target
    (mode budget_split) or are shown with a visible not-yet-spent / over-budget box (mode paid_to_date).
    Returns (applied, skipped) counts. Nothing is ever scaled to fit.
    """
    data = json.load(open(path))
    applied = skipped = 0
    for sp in data.get("splits", []):
        line = resolve(sp["target"])
        tag = f"{path.split('/')[-1]} {sp['target']}"
        if line is None:
            log(f"  skip {tag}: target not found"); skipped += 1; continue
        if line.children:
            log(f"  skip {tag}: target already split ({line.id})"); skipped += 1; continue
        if sp.get("expect_amount") is not None and cents(sp["expect_amount"]) != line.amount:
            log(f"  skip {tag}: expect {sp['expect_amount']:,} but line is {line.amount/100:,.2f}"); skipped += 1; continue
        mode = sp.get("mode", "budget_split")
        if mode == "side_only":
            # facts or rough estimates that should be visible but not shown as boxes
            if sp.get("note"):
                line.note = (line.note + " " if line.note else "") + sp["note"]
            if sp.get("why"):
                # a plain-English sentence that replaces a generic or stale one (the box is not split)
                line.why = sp["why"]
            for s in sp.get("side", []) or []:
                s = dict(s)
                if "amount" in s and s["amount"] is not None:
                    s["amount"] = cents(s["amount"])
                line.side.append(s)
            applied += 1
            continue
        src = sp.get("source") or line.source
        pieces = sp["pieces"]
        tot = sum(cents(p["amount"]) for p in pieces)
        if mode == "budget_split" and tot > line.amount:
            log(f"  skip {tag}: pieces {tot/100:,.2f} exceed line {line.amount/100:,.2f}"); skipped += 1; continue
        try:
            for p in pieces:
                _add_piece(line, p, "paid_to_date" if mode == "paid_to_date" else "tied", src)
        except ValueError as e:
            line.children = []
            log(f"  skip {tag}: {e}"); skipped += 1; continue
        diff = line.amount - tot
        if diff > 0:
            r = sp.get("residual") or {}
            default = ("Budgeted but not spent yet" if mode == "paid_to_date" else "Other / not itemised")
            line.add("not-spent-yet" if mode == "paid_to_date" else "other-not-itemised", r.get("name", default),
                     amount=diff, basis="residual", why=r.get("why"), note=r.get("note"), kind="residual")
        elif diff < 0:
            o = sp.get("over") or {}
            line.add("over-budget-so-far", o.get("name", "Already spent more than the budget for this line"),
                     amount=diff, basis="adjustment", kind="adjustment",
                     note=o.get("note", "Payments so far are larger than the full-year budget line. This negative box "
                                        "keeps the boxes adding up to the budget."))
        if sp.get("note"):
            line.note = (line.note + " " if line.note else "") + sp["note"]
        for s in sp.get("side", []) or []:
            s = dict(s)
            if "amount" in s and s["amount"] is not None:
                s["amount"] = cents(s["amount"])
            line.side.append(s)
        applied += 1
    return applied, skipped


# ---- structure cleanup -----------------------------------------------------
COLLAPSIBLE = {"fund", "spend_type", "spending_type", "org_unit", "group"}
FUND_KID_NAMES = {
    "Corporate Fund": "City's main fund (Corporate Fund)",
    "Federal Grant Fund": "Federal grants",
    "State Grant Fund": "State grants",
    "Chicago O'Hare Airport Fund": "O'Hare airport money",
    "Chicago Midway Airport Fund": "Midway airport money",
    "Water Fund": "Water bills",
    "Sewer Fund": "Sewer bills",
    "Vehicle Tax Fund": "Vehicle sticker money (Vehicle Tax Fund)",
    "Motor Fuel Tax Fund": "Gas tax money (Motor Fuel Tax Fund)",
    "Library Fund": "Library money (Library Fund)",
    "Emergency Communication Fund": "911 phone fee money (Emergency Communication Fund)",
}


def friendly_fund_names(root):
    """Fund boxes become 'paid from ...' labels a kid can read; the official name stays in extra."""
    n_changed = 0
    for n in root.walk():
        if n.kind == "fund":
            off = n.extra.get("official_name") or n.name
            n.extra["official_name"] = off
            new = FUND_KID_NAMES.get(off)
            if new and n.name == off:
                n.name = f"Paid from: {new}"
                n_changed += 1
            elif n.name == off and not n.name.startswith("Paid from"):
                n.name = f"Paid from: {off}"
                n_changed += 1
    return n_changed


def merge_rounding(root, max_abs_cents=1000):
    """Merge tiny rounding boxes (|amount| <= $10, name contains 'Rounding') into one per parent."""
    merged = 0
    for n in list(root.walk()):
        small = [c for c in n.children if not c.children and abs(c.amount) <= max_abs_cents and "ounding" in c.name]
        if len(small) <= 1 and not (len(small) == 1 and len(n.children) > 1 and small[0].amount == 0):
            continue
        keep = small[0]
        keep.amount = sum(c.amount for c in small)
        keep.name = "Rounding in the printed budget"
        keep.basis = "adjustment"
        for c in small[1:]:
            n.children.remove(c)
            merged += 1
        if keep.amount == 0 and len(n.children) > 1:
            n.children.remove(keep)
            merged += 1
    return merged


def collapse_single_children(root, kinds=COLLAPSIBLE):
    """Remove pointless clicks: a structural box (fund, spend type, org unit, group) with exactly one
    child is replaced by that child. The child keeps its own name unless the parent was a spend type
    (kid-friendly), in which case the child takes the parent's name and keeps its own in extra."""
    removed = 0
    changed = True
    while changed:
        changed = False
        for n in list(root.walk()):
            if n is root or n.parent is None or n.kind not in kinds or len(n.children) != 1:
                continue
            c = n.children[0]
            if c.amount != n.amount:
                continue
            par = n.parent
            idx = par.children.index(n)
            c.parent = par
            par.children[idx] = c
            via = c.extra.setdefault("via", [])
            via.insert(0, {"kind": n.kind, "name": n.name})
            if n.kind == "spend_type":
                c.extra.setdefault("official_name", c.name)
                c.name = n.name
            c.side.extend(n.side)
            if n.note and not c.note:
                c.note = n.note
            removed += 1
            changed = True
    # re-derive ids so they still follow the path; keep the build-time id so split files and
    # side info that reference it can still be traced. Lifting a child can make two siblings share
    # a last id part (e.g. several "corporate-fund" boxes under one department): prefix the removed
    # parent's key to keep ids unique.
    def reid(node):
        seen = set()
        for ch in node.children:
            last = ch.id.rsplit('.', 1)[-1]
            if last in seen:
                via = ch.extra.get("via") or []
                pre = slug(via[0]["name"], 24) if via else "x"
                last = f"{pre}-{last}"
                k = 2
                while last in seen:
                    last = f"{pre}-{k}-{ch.id.rsplit('.', 1)[-1]}"; k += 1
            seen.add(last)
            new = f"{node.id}.{last}"
            if new != ch.id:
                ch.extra.setdefault("build_id", ch.id)
                ch.id = new
            reid(ch)
    reid(root)
    return removed


def cleanup(root, log=print):
    """Run after all splits: kid-friendly fund labels, merged rounding, no pointless single-child clicks,
    and unique names among boxes that share a parent."""
    a = friendly_fund_names(root)
    b = merge_rounding(root)
    c = collapse_single_children(root)
    d = disambiguate_siblings(root)
    log(f"cleanup: {a} fund labels, {b} rounding boxes merged, {c} single-child boxes removed, {d} same-name siblings relabelled")


# ---- unique sibling names ---------------------------------------------------
def _fund_label(n):
    fn = n.extra.get("fund_name")
    if fn:
        return "paid from: " + FUND_KID_NAMES.get(fn, fn)
    return None


def _org_unit(n):
    for v in n.extra.get("via") or []:
        if v.get("kind") == "org_unit":
            return v.get("name")
    return None


# Attributes tried in order, per kind. Each returns a short kid-readable phrase or None.
# Only attributes that differ inside a group of same-name siblings are used, and only as many as it takes
# to make every name in the group different.
_SIB_ATTRS = {
    "line": [_fund_label,
             lambda n: n.extra.get("authority_name"),
             lambda n: "fund " + str(n.extra["fund"]) if n.extra.get("fund") else None],
    "job_title": [_org_unit,
                  lambda n: "job code " + str(n.extra["title_code"]) if n.extra.get("title_code") else None],
    "piece": [lambda n: "project " + str(n.extra["grant_project_code"]) if n.extra.get("grant_project_code") else None],
    "budget_line": [lambda n: "money from: " + str(n.extra["money_comes_from"]) if n.extra.get("money_comes_from") else None,
                    lambda n: "fund " + str(n.extra["fund_code"]) if n.extra.get("fund_code") else None,
                    lambda n: "program code " + str(n.extra["program_code"]) if n.extra.get("program_code") else None,
                    lambda n: str(n.extra["fund"]) if n.extra.get("fund") else None],
    "project": [lambda n: str(n.extra["money_source"]) if n.extra.get("money_source") else None,
                lambda n: str(n.extra["project_type"]) if n.extra.get("project_type") else None,
                lambda n: "project " + str(n.extra["project_number"]) if n.extra.get("project_number") not in (None, "TBD") else None],
}


def disambiguate_siblings(root):
    """Boxes under the same parent must not share a name (a reader cannot tell them apart). Add the thing
    that differs, such as the fund that pays (\"Overtime (paid from: Water bills)\"). The old name stays in
    extra.official_name. Returns the number of boxes renamed."""
    renamed = 0
    for parent in list(root.walk()):
        groups = {}
        for ch in parent.children:
            groups.setdefault(ch.name, []).append(ch)
        for name, grp in groups.items():
            if len(grp) < 2:
                continue
            labels = {id(ch): [] for ch in grp}
            attrs = _SIB_ATTRS.get(grp[0].kind, [])
            # fund codes and the like come after friendlier attributes, so walk the list in order
            for fn in attrs + [lambda n: None]:
                if len({tuple(v) for v in labels.values()}) == len(grp):
                    break
                vals = [fn(ch) for ch in grp]
                if len({v for v in vals}) < 2:
                    continue  # does not tell them apart
                for ch, v in zip(grp, vals):
                    if v:
                        labels[id(ch)].append(v)
            taken = {c.name for c in parent.children}
            def fmt(lab):
                # merge into an existing closing bracket instead of stacking two: "Overtime (Bureau X, paid from: Y)"
                if name.endswith(")"):
                    return f"{name[:-1]}, {lab})"
                return f"{name} ({lab})"
            for i, ch in enumerate(grp, 1):
                lab = ", ".join(labels[id(ch)])
                new = fmt(lab) if lab else fmt(f"#{i}")
                if new in taken:
                    new = fmt(f"{lab}, #{i}" if lab else f"#{i}b")
                taken.add(new)
                ch.extra.setdefault("official_name", ch.name)
                ch.name = new
                renamed += 1
    return renamed


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
