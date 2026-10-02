"""Audit 2, part 3b: look for names of individuals in every text field of nodes and side_info (read-only).
Compares against data/people/*.json (local only, gitignored). A hit is a two-word match of 'first last' or 'last first'
(case-insensitive, punctuation ignored) from the City roster, the City payroll people not on the roster, and the CPS roster.
Prints counts and, for triage, only the matched bigram and the field (never the whole row).
Parks publishes no names, so there is nothing to compare."""
import json, os, re, collections
from treeaudit2_common import *

PEOPLE = os.path.join(ROOT, "data", "people")
TOK = re.compile(r"[a-z][a-z'\-]+")

def clean(s): return re.sub(r"[^a-z' \-]", " ", (s or "").lower())

def name_pairs(full, comma_last_first=True):
    """'FORD, MARIALISA T' or 'Miller, Hope' -> set of (first,last) and (last,first) strings."""
    s = (full or "").strip()
    if "," in s:
        last, rest = s.split(",", 1)
    else:
        parts = s.split(); last, rest = (parts[-1], " ".join(parts[:-1])) if len(parts) > 1 else ("", s)
    lt = TOK.findall(clean(last)); ft = TOK.findall(clean(rest))
    if not lt or not ft: return set()
    l = lt[-1]; f = ft[0]
    if len(l) < 3 or len(f) < 3: return set()
    return {f"{f} {l}", f"{l} {f}"}

def load_names():
    names = {}
    d = json.load(open(f"{PEOPLE}/city_employees_2026.json"))
    for key in ("current_employees", "paid_2025_not_matched_to_current_roster"):
        for r in d.get(key, []):
            for p in name_pairs(r.get("name")): names[p] = "city"
    d = json.load(open(f"{PEOPLE}/cps_positions_2025q4.json"))
    for r in d["positions"]:
        for p in name_pairs(r.get("name")): names.setdefault(p, "cps")
    return names

def first_name_sets():
    """Common first names and surnames from the private roster (counts only, never printed): a first name is a token that starts
    at least 20 roster names, a surname one that ends at least 3."""
    fn = collections.Counter(); sn = collections.Counter()
    d = json.load(open(f"{PEOPLE}/city_employees_2026.json"))
    for r in d.get("current_employees", []):
        s = (r.get("name") or "")
        if "," not in s: continue
        last, rest = s.split(",", 1)
        lt = TOK.findall(clean(last)); ft = TOK.findall(clean(rest))
        if lt and ft: sn[lt[-1]] += 1; fn[ft[0]] += 1
    return {k for k, v in fn.items() if v >= 20 and len(k) >= 3}, {k for k, v in sn.items() if v >= 3 and len(k) >= 3}

def person_like_payees():
    """Second check, independent of the private lists: vendors_paid rows NOT marked individual (and with no City contract number,
    the build's own business test) whose payee text looks like a private person or a couple. Heuristic, counts only, nothing printed.
    'person-like' = after dropping business words (build/payee.py ORG_TOKENS plus law-firm words), every token is a plain name and
      couple: contains '&' or 'AND' and at least two tokens are common first names from the roster ('ROSA ORTIZ & VICTOR ALVAREZ')
      single: no '&', first token a common first name and last token a common surname ('JESUS LOPEZ')."""
    import sys
    sys.path.insert(0, os.path.join(ROOT, "build"))
    import payee
    ORG = {x.rstrip(".") for x in payee.ORG_TOKENS} | {"DBA", "LLC", "INC", "CO", "MD", "AND", "JR", "SR", "II", "III", "ESQ", "PC", "P.C", "PLLC", "LIMITED", "NFP", "LABS", "LAB", "PRODUCTS", "GOVERNMENT", "DIRECT", "INSPECTOR", "GENERAL", "OFFICE", "KNOWLEDGE", "LANDSCAPES", "GLASS", "MIRRORS", "CHEMICALS", "INDUSTRY", "FACILITY", "SOLUTION", "EDISON", "REAVIS", "POGUE", "HARDIN", "WAITE", "MILSTEIN", "TOLL"}
    firsts, lasts = first_name_sets()
    c = con(); out = collections.defaultdict(lambda: [0, 0.0])
    total = hidden = 0
    for r in c.execute("select extra from side_info where kind='vendors_paid'"):
        for it in (json.loads(r["extra"]).get("items") or []):
            total += 1
            v = it["vendor"]
            if it.get("is_individual") or "name hidden" in v.lower(): hidden += 1; continue
            has_c = bool(it.get("contract"))   # payee.py treats any holder of a City contract as a business
            u = re.sub(r"\s*\d+$", "", v.upper()).strip()
            t = [x.strip(".,") for x in re.split(r"[\s,/()&]+", u) if x.strip(".,")]
            if not (2 <= len(t) <= 6) or any(x in ORG for x in t): continue
            if not all(re.fullmatch(r"[A-Z'.\-]+", x) for x in t): continue
            tl = [x.lower() for x in t]
            if ("&" in v or " AND " in u):
                if sum(1 for x in tl if x in firsts) >= 2: key = "couple (A & B Surname)"
                else: continue
            else:
                if tl[0] in firsts and tl[-1] in lasts: key = "single (First Last)"
                else: continue
            key += ", has a City contract number (payee.py keeps the name)" if has_c else ", no contract number"
            out[key][0] += 1; out[key][1] += it["amount"] / 100
    return total, hidden, out

def main():
    total, hidden, pl = person_like_payees()
    print(f"vendors_paid rows: {total:,}; individuals already hidden: {hidden:,}")
    print("rows NOT hidden that look like private persons (heuristic, names not printed):")
    for k, (n, a) in sorted(pl.items()): print(f"  {k}: {n} rows, ${a:,.0f}")
    names = load_names()
    print(f"person name patterns loaded: {len(names):,} (not printed)")
    c = con()
    hits = collections.Counter(); samples = {}
    scanned = collections.Counter()
    def scan(text, where):
        t = clean(text); toks = TOK.findall(t)
        scanned[where] += 1
        for a, b in zip(toks, toks[1:]):
            k = f"{a} {b}"
            if k in names:
                hits[(where, k)] += 1; samples.setdefault((where, k), text[:0])
    for r in c.execute("select id,name,note,why_cant_go_deeper,source,extra from nodes"):
        for col in ("name", "note", "why_cant_go_deeper", "source", "extra"):
            if r[col]: scan(r[col], f"nodes.{col}")
    for r in c.execute("select node_id,kind,label,source,extra from side_info"):
        for col in ("label", "source", "extra"):
            if r[col]: scan(r[col], f"side_info.{col}")
    print("fields scanned:", dict(scanned))
    print(f"two-word matches against person names: {len(hits)} distinct, {sum(hits.values())} occurrences")
    # triage: show matches (these are names already; the audit report must not copy them). Print a classification only.
    # Common-phrase false positives are expected (e.g. a person called 'Grant Park'). Show up to 40 for review in the terminal only.
    for (where, k), n in hits.most_common(60): print(f"  {where:22} {n:4}  '{k}' ({names[k]})")
    # triage of the roster matches by where they sit (counts only)
    tri = collections.Counter()
    for r in c.execute("select kind,name,note,source,extra from nodes"):
        for col in ("name", "note", "source", "extra"):
            if r[col] and any(f"{a} {b}" in names for a, b in zip(*(lambda t: (t, t[1:]))(TOK.findall(clean(r[col]))))): tri[("nodes", r["kind"])] += 1; break
    for r in c.execute("select kind,label,source,extra from side_info"):
        for col in ("label", "source", "extra"):
            if r[col] and any(f"{a} {b}" in names for a, b in zip(*(lambda t: (t, t[1:]))(TOK.findall(clean(r[col]))))): tri[("side_info", r["kind"])] += 1; break
    print("rows with a roster match, by table and kind:", dict(tri))
    json.dump({"person_like_payees": {k: v for k, v in pl.items()}, "match_rows_by_kind": {f"{a}|{b}": n for (a, b), n in tri.items()}, "vendors_paid_rows": total, "hidden": hidden, "n_patterns": len(names), "n_hits": len(hits), "n_occurrences": sum(hits.values()),
               "where": dict(collections.Counter(w for (w, _k) in hits))}, open(f"{OUT}/names.json", "w"), indent=1)

if __name__ == "__main__":
    main()
