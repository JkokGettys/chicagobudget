"""Build data/splits/city/paid_to_date.json: vendor "paid so far" boxes under City non-salary budget lines.

Input : data/city_vendors_items_2026ytd.json (made by scripts/contracts_build.py from the deduplicated payments
        raw/contracts/payments_2026ytd_dedup.csv, Jan 1 to 09/28/2026), the built tree raw/paidtodate/baseline_city_tree.json
        (copy of build/out/city_tree.json made before this split file existed), and the 2026 ordinance lines.
Output: data/splits/city/paid_to_date.json (mode "paid_to_date", see build/SPLITS.md)
Run   : python3 scripts/paidtodate_build.py        (needs build/out/city_tree.json from `python3 build/city_tree.py`)

THE MATCHING PROBLEM. A payment carries a department, a contract and a vendor, but no fund and no account.
A budget line is (fund, department, authority, account). So a payment is placed on a line only when a rule below
leaves exactly ONE line. Everything else stays side info on the department box (already there).

Rules (applied in this order, each item goes to at most one line):
  R0  Scope. Only families PROF IT TELECOM DELEGATE CONSTR FACILITY WASTE RENTAL UTIL FUEL MATERIALS EQUIP.
      Not placed: BENEFITS, LEGAL, DEVLOAN, OTHER_VENDOR (not named in the task, and their lines are judgments,
      loans, health claims), Finance General (dept 99, whose payments are pensions, banks, insurers).
      Items typed VEHICLES/HEAVY EQUIPMENT whose family came out as FUEL or UTIL are not placed: the family
      keyword rule read "diesel" or "electrical" in a vehicle or repair-parts contract, so the family is wrong.
  R1  Unique line. The department has exactly one positive budget line whose account belongs to the item's family.
  R2  Program code in the contract description (delegate agencies). Descriptions such as "DFSS-CORP-HL-RRP",
      "CDPH-VIOLNCE PREV", "MOPD-CDBG-HOMEMOD", "BACP-CORP-NBDC" carry a funding source (CORP = Corporate Fund
      0100, CDBG = 925E, ARP = GA00) and a program. A table below maps (department, funding token, program) to the
      line's fund, authority and account. Only mappings where the line name says the same thing as the code are in it.
  R3  Account by what the contract is (PROF always account 0140, the main professional services account, 98% of
      the family; electricity 0331, natural gas 0322 by vendor and description words; pavement work 0163),
      then fund by the airport named in the description (O'Hare = fund 0740, Midway = fund 0610; both named or
      none named = not placed). Then the line must be unique.
  R4  Authority hint where one bureau is named for the work: waste in Streets and Sanitation goes to the line of
      the Bureau of Sanitation.
      Aviation contracts whose description says "Federal" (not "Non-Federal") are not placed: they are probably
      charged to an FAA grant line, not to the airport fund.
  Guard. If the payments assigned to one line add up to more than 2x the line, the match is evidently wrong
      (the money is probably paid from another line), so nothing is placed on that line.
Duplicates: the dedup CSV still has 1,014 pairs ($202M) that differ only in how the vendor name is spelled. They are
removed first (alias_duplicate_corrections). Run python3 scripts/payments_dedupe.py fix upstream to drop this step.
Individuals: build/payee.py is_business() exactly as build/city_tree.py (one decision per payee name, a payee with
a contract anywhere is a business, City employee roster = people). Individuals are pooled into one piece.
Under a line, vendors of $1M or more are listed one by one, the rest are grouped as "Other vendors (N)".
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "build"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import contracts_build as cb  # noqa: E402  (account_family, vendor_key; main() is guarded)
from payee import is_business, people_by_description  # noqa: E402

P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
BASELINE = P("raw/paidtodate/baseline_city_tree.json")
OUT = P("data/splits/city/paid_to_date.json")
SCOPE = {"PROF", "IT", "TELECOM", "DELEGATE", "CONSTR", "FACILITY", "WASTE", "RENTAL", "UTIL", "FUEL", "MATERIALS", "EQUIP"}
INDIVIDUAL_FLOOR = 1_000_000_00   # vendors at or above $1M (in cents) are listed one by one
GUARD = 2.0
HIDDEN = "Individual (name hidden)"

# ---------------------------------------------------------------- R2 table
# description prefix -> funding token -> program word(s) -> (fund, authority, account); authority None = any
FUND_OF_TOKEN = {"CORP": "0100", "ARP": "GA00", "CDBG": "925E"}
# (dept, regex on description) -> (fund, authority, account). Checked in order, first match wins.
PROGRAM_RULES = [
    # DFSS (50): the second and third code words are the funding source and the program
    ("50", r"DFSS-CORP-HL\b", ("0100", "2005", "9263")),            # Homeless Services (Corporate Fund)
    ("50", r"DFSS-CORP-YS-SYEP", ("0100", "2005", "9259")),         # Youth Employment
    ("50", r"DFSS-CORP-YS-OST", ("0100", "2005", "9260")),          # After School Programs
    ("50", r"DFSS-CORP-GBV", ("0100", "2005", "9299")),             # Gender Based Violence Services
    ("50", r"DFSS-ECBG-CS", ("925S", "2962", "0135")),              # ISBE Early Childhood Block Grant
    ("50", r"DFSS-HHS-CS-CEL", ("925F", "2860", "0135")),           # HHS Head Start
    ("50", r"DFSS-IDHS-HL", ("925S", "2942", "0135")),              # IDHS Emergency and Transitional Housing
    ("50", r"DFSS-IDOA-SS", ("925S", "2904", "0135")),              # IDOA Area Plan on Aging (home delivered meals)
    ("50", r"DFSS-ESG-HL", ("925F", "2944", "0135")),               # HUD Emergency Solutions Grants
    # Public Health (41)
    ("41", r"CDPH-VIOLNCE", ("0100", "1005", "9254")),              # Violence Reduction Program
    ("41", r"CDPH-RW-PA", ("925F", "2731", "0135")),                # Ryan White Part A = HIV Emergency Relief Project Grants
    ("41", r"HOPWA", ("925F", "2932", "0135")),                     # Housing Opportunities for People with AIDS
    ("41", r"CDPH-STI.*REPRO|REPRO HEALTH", ("0100", "1005", "9296")),  # Reproductive Health Initiative
    # Disabilities (48), Business Affairs (70), Housing (21), Planning (54): the funding token picks the fund
    ("48", r"MOPD-CDBG-HOMEMOD", ("925E", "2525", "0135")),         # CDBG Rehabilitation, Home Modification
    ("48", r"MOPD-CORP-", ("0100", "2005", "0135")),
    ("70", r"BACP-CORP-", ("0100", "2005", "0135")),
    ("70", r"BACP-070-ARP", ("GA00", "290H", "0135")),
    ("21", r"DOH-CORP-", ("0100", "2010", "0135")),
    ("54", r"DPD-CORP-", ("0100", "2005", "0135")),
]
PROGRAM_RULES = [(d, re.compile(rx, re.I), t) for d, rx, t in PROGRAM_RULES]

ELEC = re.compile(r"ELECTRICITY|ELECTRIC SUPPLY|COMED|COMMONWEALTH|CONSTELLATION", re.I)
GAS = re.compile(r"NATURAL GAS|PEOPLES GAS|NICOR|MANSFIELD", re.I)
PAVE = re.compile(r"PAVEMENT|PAVING|STRIPING|RUNWAY|TAXIWAY|RAMP REPLACEMENT", re.I)
OHARE = re.compile(r"O.?HARE|ORD\b", re.I)
MIDWAY = re.compile(r"MIDWAY", re.I)
AUTHORITY_HINT = {("81", "WASTE"): "Sanitation"}


def alias_duplicate_corrections(ven):
    """The shared dedupe rule (scripts/payments_dedupe.py) keys on voucher + amount + date + vendor_name + contract.
    The same payment also sits in the file twice when the two copies spell the vendor differently (for example
    "F.H. PASCHEN, S.N. NIELSEN" and "F.H. PASCHEN S.N. NIELSEN", or two vendor records on one contract): 1,014 pairs,
    one with a department and one blank, same voucher, amount, check date and contract. Same evidence as the rule
    in research/payments_dedupe.md (every pair is one filled plus one blank department, or both blank). We remove
    the blank-department copy (or the second one if both are blank) from the items before placing them.
    Returns (items edited in place, dollars removed, pairs, pairs not found)."""
    import pandas as pd
    df = pd.read_csv(P("raw/contracts/payments_2026ytd_dedup.csv"), dtype=str)
    df["amt"] = df["amount"].astype(float)
    key = ["voucher_number", "amt", "check_date", "contract_number"]
    df = df[df.contract_number != "DV"].copy()
    nv = df.groupby(key).vendor_name.transform("nunique")
    cnt = df.groupby(key).vendor_name.transform("size")
    dup = df[(nv > 1) & (cnt == 2)].copy()
    dup["has_dept"] = dup.department_name.notna()
    dup["order"] = range(len(dup))
    drop = dup.sort_values(["has_dept", "order"], ascending=[True, False]).groupby(key).head(1)
    index = collections.defaultdict(list)
    for d, dd in ven["departments"].items():
        for fam, rows in dd["families"].items():
            for v in rows:
                index[(str(v[1]), cb.vendor_key(v[0]))].append(v)
    removed = 0.0
    missing = 0
    for r in drop.itertuples(index=False):
        cands = [v for v in index.get((str(r.contract_number), cb.vendor_key(r.vendor_name)), []) if v[2] >= r.amt - 0.005]
        if not cands:
            missing += 1
            continue
        v = max(cands, key=lambda v: v[2])
        v[2] = round(v[2] - r.amt, 2)
        v[3] = max(0, v[3] - 1)
        removed += r.amt
    return removed, len(drop), missing


def load_lines():
    rows = json.load(open(BASELINE))["rows"]
    lines = []
    for r in rows:
        if r["kind"] != "line" or not r["id"].startswith("city.") or not r["extra"]:
            continue
        e = json.loads(r["extra"])
        if "account" not in e or r["amount_cents"] <= 0:
            continue
        kind, fam = cb.account_family(e["account"])
        lines.append({"id": r["id"], "fund": e["fund"], "dept": e["dept_number"].lstrip("0") or "0", "authority": e["authority"],
                      "authority_name": e.get("authority_name", ""), "account": e["account"], "kind": kind, "family": fam,
                      "amount": r["amount_cents"], "is_leaf": bool(r["is_leaf"]), "name": e.get("official_name", "")})
    return lines


def place(item, lines_by):
    """Return (line, rule) or (None, reason)."""
    d, fam, ven, con, amt, desc, ctype = item["dept"], item["family"], item["vendor"], item["contract"], item["amount"], item["desc"], item["ctype"]
    if d == "99" or d not in {l["dept"] for l in lines_by["all"]}:
        return None, "department has no budget lines here (Finance General or unknown)"
    if fam not in SCOPE:
        return None, "family not in scope"
    if fam in ("FUEL", "UTIL") and ctype == "VEHICLES/HEAVY EQUIPMENT (CAPITAL)":
        return None, "family misread from keywords"
    text = f"{ven} {desc or ''}"
    # R2 program code
    if fam == "DELEGATE":
        for dd, rx, (fund, auth, acct) in PROGRAM_RULES:
            if dd == d and rx.search(desc or ""):
                hit = [l for l in lines_by["dept"][d] if l["fund"] == fund and l["account"] == acct and (auth is None or l["authority"] == auth)]
                if len(hit) == 1:
                    return hit[0], "R2 program code"
                return None, "R2 code matched but line not unique"
    cands = [l for l in lines_by["dept_family"].get((d, fam), [])]
    # R3 narrowing by what the contract is
    if fam == "PROF":
        cands = [l for l in cands if l["account"] == "0140"]
    elif fam == "UTIL":
        if ctype not in ("COMPTROLLER-OTHER", None):
            return None, "UTIL on a commodity contract (family misread)"
        if ELEC.search(text):
            cands = [l for l in cands if l["account"] == "0331"]
        elif GAS.search(text):
            cands = [l for l in cands if l["account"] == "0322"]
        else:
            return None, "UTIL kind not identified"
    elif fam == "FACILITY" and PAVE.search(desc or ""):
        cands = [l for l in cands if l["account"] == "0163"]
    # Aviation: a contract described as federally funded is probably charged to an FAA grant line, not the airport fund
    if d == "85" and re.search(r"(?<!NON-)(?<!NON )FEDERAL", desc or "", re.I) and fam in ("PROF", "FACILITY"):
        return None, "aviation contract marked federal (may be charged to a grant line)"
    # fund by airport named in the description
    funds = {l["fund"] for l in cands}
    if d == "85" and len(cands) > 1:
        o, m = bool(OHARE.search(text)), bool(MIDWAY.search(text))
        if o and not m:
            cands = [l for l in cands if l["fund"] == "0740"]
        elif m and not o:
            cands = [l for l in cands if l["fund"] == "0610"]
        else:
            return None, "airport not identified"
    # R4 authority hint
    if len(cands) > 1 and (d, fam) in AUTHORITY_HINT:
        cands = [l for l in cands if AUTHORITY_HINT[(d, fam)] in l["authority_name"]]
    if len(cands) == 1:
        return cands[0], "R1 unique line" if len(lines_by["dept_family"].get((d, fam), [])) == 1 else "R3/R4 narrowed to one line"
    return None, f"{len(cands)} candidate lines"


def full_descriptions():
    """contract number -> full description of its latest revision (rsxa-ify5). The items file cuts descriptions at 90
    characters, so words such as "O'Hare" or "Federal" late in the text were invisible to the matching rules."""
    import csv
    by = {}
    with open(P("raw/contracts/contracts_all.csv"), newline="") as f:
        for r in csv.DictReader(f):
            try:
                rv = int(r["revision_number"])
            except (TypeError, ValueError):
                rv = -1
            k = r["purchase_order_contract_number"]
            if k not in by or rv >= by[k][0]:
                by[k] = (rv, r["purchase_order_description"] or "")
    return {k: v[1] for k, v in by.items()}


def main():
    ven = json.load(open(P("data/city_vendors_items_2026ytd.json")))
    label = ven["meta"]["label"]
    rem, npairs, nmiss = alias_duplicate_corrections(ven)
    FULL = full_descriptions() if os.path.exists(P("raw/contracts/contracts_all.csv")) else {}
    print(f"removed {npairs} same-voucher pairs spelled with two vendor names: ${rem:,.2f} ({nmiss} pairs not found in items)")
    emp_path = P("data/people/city_employees_2026.json")
    pp = json.load(open(emp_path)) if os.path.exists(emp_path) else {"current_employees": []}
    emp = {e["name"].upper().strip() for e in pp["current_employees"] if e.get("name")}
    has_contract = collections.defaultdict(bool)
    for dd in ven["departments"].values():
        for rows in dd["families"].values():
            for v in rows:
                has_contract[(v[0] or "").upper().strip()] |= bool(v[1])
    emp = emp | people_by_description(
        (v[0], v[4]) for dd in ven["departments"].values() for rows in dd["families"].values() for v in rows)
    biz = {nm: is_business(nm, hc, emp) for nm, hc in has_contract.items()}

    lines = load_lines()
    lines_by = {"all": lines, "dept": collections.defaultdict(list), "dept_family": collections.defaultdict(list)}
    for l in lines:
        lines_by["dept"][l["dept"]].append(l)
        if l["kind"] == "vendor":
            lines_by["dept_family"][(l["dept"], l["family"])].append(l)
    by_id = {l["id"]: l for l in lines}

    assigned = collections.defaultdict(list)
    unplaced = collections.Counter()
    placed_rules = collections.Counter()
    tot_items = 0
    for d, dd in ven["departments"].items():
        for fam, rows in dd["families"].items():
            for v in rows:
                name = (v[0] or "").upper().strip()
                desc = v[4] or ""
                fd = FULL.get(str(v[1]), "")
                if len(desc) >= 85 and fd.startswith(desc[:80]):
                    desc = fd   # the items file truncated it
                item = {"dept": d.lstrip("0") or "0", "family": fam, "vendor": v[0] or "", "contract": v[1], "amount": round(v[2] * 100),
                        "payments": v[3], "desc": desc, "ctype": v[5], "biz": biz.get(name, False)}
                tot_items += item["amount"]
                if item["amount"] <= 0:
                    unplaced["non-positive net"] += item["amount"]
                    continue
                line, why = place(item, lines_by)
                if line is None:
                    unplaced[why] += item["amount"]
                else:
                    item["rule"] = why
                    assigned[line["id"]].append(item)

    # guard
    dropped = []
    for lid in list(assigned):
        s = sum(i["amount"] for i in assigned[lid])
        if s > GUARD * by_id[lid]["amount"]:
            dropped.append((lid, s, by_id[lid]["amount"]))
            for i in assigned[lid]:
                unplaced["guard: paid > 2x the line"] += i["amount"]
            del assigned[lid]

    splits = []
    for lid, items in sorted(assigned.items(), key=lambda kv: -sum(i["amount"] for i in kv[1])):
        l = by_id[lid]
        if not l["is_leaf"]:
            for i in items:
                unplaced["line already split by a built-in split"] += i["amount"]
            continue
        splits.append(make_split(l, items))

    # unplaced totals only count scope families for a clear picture
    placed = sum(s["_placed"] for s in splits)
    for s in splits:
        s.pop("_placed", None)
    json.dump({"meta": {"author": "paid-to-date agent", "built_by": "scripts/paidtodate_build.py",
                        "description": "Vendor payments so far (" + label + ") as boxes under the City budget lines they can be matched to. "
                                       "Rules are in the header of scripts/paidtodate_build.py. Payments carry no fund or account, so "
                                       "only unambiguous matches are placed."},
               "splits": splits}, open(OUT, "w"), indent=1)
    print(f"lines with paid-to-date boxes: {len(splits)}")
    print(f"placed ${placed/100:,.2f} of ${tot_items/100:,.2f} in the items file")
    print("dropped by guard:", [(i, round(s / 1e8, 1), round(a / 1e8, 1)) for i, s, a in dropped])
    for k, v in unplaced.most_common(12):
        print(f"  unplaced {v/1e8:8.1f}M  {k}")
    return splits


def vendor_pieces(items, line_amount_for_why=None):
    """Group items into vendor pieces (dicts, dollars). Returns (pieces, individuals_piece or None)."""
    ven = collections.defaultdict(list)
    ind = []
    for it in items:
        if not it["biz"]:
            ind.append(it)
        else:
            ven[cb.vendor_key(it["vendor"])].append(it)
    WHY = "This is what one company has been paid so far this year. The City's payment records list it as one amount, and we could not find a public record that splits it further."
    WHY_C = "This is what one company has been paid so far this year on one contract, and the payment records do not show smaller pieces."
    pieces = []
    for k, its in ven.items():
        tot = sum(i["amount"] for i in its)
        display = max(its, key=lambda i: i["amount"])["vendor"]
        pc = {"name": display.strip(), "amount": tot / 100, "basis": "paid_to_date", "kind": "vendor"}
        if len(its) == 1:
            i = its[0]
            pc["note"] = (f"Contract {i['contract']}: " if i["contract"] else "Paid by direct voucher (no contract). ") + clean(i["desc"]) + f" ({i['payments']} payments)"
            pc["extra"] = {"contract": i["contract"], "payments": i["payments"]}
            if tot >= 1_000_000_000:
                pc["why"] = WHY_C
        else:
            pc["note"] = f"{len(its)} contracts, {sum(i['payments'] for i in its)} payments"
            pc["extra"] = {"contracts": len(its)}
            kids = []
            for i in sorted(its, key=lambda i: -i["amount"]):
                kid = {"name": (f"Contract {i['contract']}" if i["contract"] else "Direct vouchers (no contract)") + (": " + clean(i["desc"], 70) if i["desc"] else ""),
                       "amount": i["amount"] / 100, "basis": "paid_to_date", "kind": "contract",
                       "note": f"{i['payments']} payments", "extra": {"contract": i["contract"], "payments": i["payments"]}}
                if i["amount"] >= 1_000_000_000:
                    kid["why"] = WHY_C
                kids.append(kid)
            pc["children"] = kids
        pc["_c"] = tot
        pieces.append(pc)
    pieces.sort(key=lambda p: -p["_c"])
    ind_piece = None
    if ind:
        tot = sum(i["amount"] for i in ind)
        n = len(ind)
        ind_piece = {"name": HIDDEN if n == 1 else f"Payments to {n} individuals (names hidden)", "amount": tot / 100,
                     "basis": "paid_to_date", "kind": "individuals", "count": n, "unit_label": "individuals",
                     "note": f"{sum(i['payments'] for i in ind)} payments to people, refunds, small grants or sole practitioners. Names are hidden to protect privacy.",
                     "_c": tot}
        if tot >= 1_000_000_000:
            ind_piece["why"] = "These are payments to individual people, whose names we hide, and each person is paid a small amount."
    return pieces, ind_piece


def clean(s, n=140):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[: n - 1] + "…" if len(s) > n else s


def make_split(line, items):
    pieces, ind_piece = vendor_pieces(items)
    top = [p for p in pieces if p["_c"] >= INDIVIDUAL_FLOOR]
    rest = [p for p in pieces if p["_c"] < INDIVIDUAL_FLOOR]
    out = list(top)
    if rest:
        tot = sum(p["_c"] for p in rest)
        # The id is "other-vendors" with no count, so deep links survive a refresh of the payments.
        # The count stays in the name and in extra.n_vendors.
        out.append({"key": "other-vendors", "name": f"Other vendors ({len(rest)})", "amount": tot / 100, "basis": "paid_to_date",
                    "kind": "vendor_group", "extra": {"n_vendors": len(rest)},
                    "children": rest, "children_residual_name": "Other / not itemised",
                    "note": f"Vendors paid under $1 million each so far, largest first."})
    if ind_piece:
        out.append(ind_piece)
    placed = sum(items_["amount"] for items_ in items)

    def strip(p):
        p.pop("_c", None)
        for c in p.get("children", []) or []:
            strip(c)
    for p in out:
        strip(p)
    # exact cents: every parent equals the sum of its children
    def fix(p):
        kids = p.get("children")
        if kids:
            for c in kids:
                fix(c)
            p["amount"] = round(sum(round(c["amount"] * 100) for c in kids)) / 100
    for p in out:
        fix(p)
    rules = sorted({i["rule"] for i in items})
    return {"_placed": placed,
            "target": {"by": "ordinance_line", "fund": line["fund"], "dept": line["dept"], "authority": line["authority"], "account": line["account"]},
            "expect_amount": line["amount"] / 100, "mode": "paid_to_date", "pieces": out,
            "source": {"dataset": "s4vu-giwb", "name": "City of Chicago Payments (deduplicated, checks Jan 1 to 09/28/2026)",
                       "url": "https://data.cityofchicago.org/d/s4vu-giwb", "note": "research/payments_dedupe.md"},
            "residual": {"name": "Budgeted but not spent yet",
                         "why": "This is budget money the City has set aside for this line but has not paid out yet this year (payments run to 09/28/2026)."},
            "over": {"name": "Already spent more than the budget for this line",
                     "note": "Payments so far on contracts matched to this line are larger than the full-year budget line. Payments carry no fund or account, "
                             "so the match is by department, contract type and program code, and may include money charged to other lines."},
            "note": "Vendor payments so far (checks Jan 1 to 09/28/2026, partial year) matched to this line by: " + "; ".join(rules) +
                    ". Payments have a department and a contract but no fund or account, so only unambiguous matches are shown. Names of individual people are hidden."}


if __name__ == "__main__":
    main()
