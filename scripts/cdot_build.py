#!/usr/bin/env python3
"""CDOT project-level split file: data/splits/city/cdot_projects.json  (format: build/SPLITS.md)

Inputs (all cached under raw/, which is gitignored; rebuild the cache with scripts/cdot_etip_fetch.py):
  raw/cdot/tip3488/*.json           CMAP eTIP, TIP 2026-2030 plan cycle, all 108 CDOT-led projects (fund table by phase and fund source, FY2026 column)
  raw/contracts/midyear_grants.csv  City Mid-Year Grants 925 ledger (dataset iyu8-jkf8), extracts 2025-06-01 and 2026-05-31
  raw/grants/usaspending_chicago_awards.json   USASpending prime awards to the City (State/Lake award IL-2016-002)
  raw/contracts/contracts_all.csv, payments_*_dedup.csv   State/Lake construction contract and payments (side facts)
  data/city_capital_2026.json       City CIP 2025-2029 (State/Lake project 40492, side fact)

Rules: every piece amount is a number found in a source. Nothing is scaled. Pieces on a line never exceed the line
(the script asserts it). Matching a TIP project to an ordinance line is by fund type (federal highway versus state)
and is stated in each note. Run: python3 scripts/cdot_build.py
"""
import csv, glob, json, os, re, sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "splits", "city", "cdot_projects.json")
TIP_DIR = os.path.join(ROOT, "raw", "cdot", "tip3488")
T10 = 10_000_000

ETIP_URL = "https://cmap.ecointeractive.com/"
LEDGER_URL = "https://data.cityofchicago.org/resource/iyu8-jkf8"
USA_URL = "https://www.usaspending.gov/award/ASST_NON_IL-2016-002_069"

# ---------------------------------------------------------------- helpers
def money(s):
    return Decimal(s.replace("$", "").replace(",", "")) if s else Decimal(0)


def dol(d):
    """Decimal dollars -> float with cents (the builder converts to integer cents)."""
    return float(Decimal(d).quantize(Decimal("0.01")))


def nice(s):
    s = re.sub(r"\s+", " ", s.strip())
    # The portal's ledger has a lost dash stored as the character U+00BF ("IMPROVEMENTS ¿ 2021"). Use a plain hyphen.
    s = s.replace(" \u00bf ", " - ").replace("\u00bf", "-")
    s = s.replace("MOBIILITY", "MOBILITY").replace("IMPROVMENTS", "IMPROVEMENTS")
    s = s.title()
    s = re.sub(r"\b(\d+)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), s)
    s = re.sub(r"\b(Ii|Iii)\b", lambda m: m.group(1).upper(), s)
    for w in ("Cta", "Bnsf", "Brc", "Create", "Gs09", "Gs11", "Atms", "Icc", "Idot", "Opc", "Ada", "Dceo", "Ewing"):
        s = re.sub(r"\b%s\b" % w, w.upper() if w != "Ewing" else w, s)
    return s.rstrip(" #-").strip()


def why_money(amount, text):
    return text if abs(amount) >= T10 else None


# ---------------------------------------------------------------- TIP (CMAP eTIP, plan cycle 3488 = TIP 2026-2030)
def load_tip():
    projs = []
    for f in sorted(glob.glob(os.path.join(TIP_DIR, "*.json"))):
        d = json.load(open(f))
        cols = [c["title"] for c in d["fundTable"]["columns"]]
        i26 = cols.index("FY2026")
        ctl = {c["name"]: c["data"] for c in d["controls"]}
        rows, cur = [], None
        for r in d["fundTable"]["rows"]:
            v = [x["data"] for x in r["rowData"]]
            if v[0].startswith("Total") or not v[1]:
                continue
            cur = v[0] or cur
            rows.append({"phase": cur, "fund": v[1], "fy2026": money(v[i26]), "total": money(v[-1])})
        projs.append({"id": d["externalId"], "title": d["title"].split(": ", 1)[1], "projectId": d["projectId"],
                      "rows": rows, "ctl": ctl, "file": os.path.basename(f)})
    return projs


# TIP fund-source categories (CMAP eTIP filter list, "Federal Highway" and "State" categories)
FED_HWY = {"STP - Locally Prgmd", "TAP - Locally Prgmd", "CMAQ", "STP - Regional Redistribution", "STP - Shared Fund",
           "Natl Hwy Freight Pgm"}
STATE = {"State Match - Chicago", "IL Funds", "Local Project Funding"}   # Rebuild Illinois is handled on its own line


def tip_src(p, note):
    return {"doc": "CMAP eTIP, Transportation Improvement Program 2026-2030, project %s, fund table, column FY2026" % p["id"],
            "url": ETIP_URL, "page": "Projects tab, search TIP ID %s" % p["id"], "note": note}


def tip_children(p, funds):
    kids = []
    for r in p["rows"]:
        if r["fund"] in funds and r["fy2026"] > 0:
            kids.append({"key": "%s-%s-%s" % (p["id"], r["phase"], r["fund"]),
                         "name": "%s, %s" % (r["phase"], r["fund"]), "amount": dol(r["fy2026"]), "basis": "gov_estimate"})
    # merge duplicates with the same name (a project can list one fund twice in a phase)
    merged = {}
    for k in kids:
        if k["name"] in merged:
            merged[k["name"]]["amount"] = dol(Decimal(str(merged[k["name"]]["amount"])) + Decimal(str(k["amount"])))
        else:
            merged[k["name"]] = k
    return list(merged.values())


def tip_pieces(projs, funds, why_text, note):
    pcs = []
    for p in projs:
        kids = tip_children(p, funds)
        tot = sum(Decimal(str(k["amount"])) for k in kids)
        if tot <= 0:
            continue
        for k in kids:
            if k["amount"] >= T10:
                k["why"] = why_text
        piece = {"key": p["id"], "name": "%s: %s" % (p["id"], p["title"]), "amount": dol(tot), "basis": "gov_estimate",
                 "source": tip_src(p, note),
                 "note": "%s. Completion year %s. Lead agency %s." % (p["ctl"].get("Project Description") or "No description", p["ctl"].get("Completion Year"), p["ctl"].get("Lead Agency")),
                 "extra": {"tip_id": p["id"], "etip_project_id": p["projectId"], "tip_document": p["ctl"].get("TIP Document")},
                 "children": kids}
        if len(kids) == 1:
            piece["children"] = []
            if piece["amount"] >= T10:
                piece["why"] = why_text
        pcs.append(piece)
    pcs.sort(key=lambda x: -x["amount"])
    return pcs


# ---------------------------------------------------------------- Mid-Year Grants ledger
def load_ledger():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "raw", "contracts", "midyear_grants.csv"))))
    return rows


def cdot(rows):
    return [r for r in rows if r["department_code"] == "D84"]


def unspent(r):
    """Budget minus expended to date (encumbrances count as unspent), never below zero, exact cents."""
    return max(Decimal(0), Decimal(r["budget"] or 0) - Decimal(r["expended_project_to_date"] or 0))


def ledger_pieces(rows, why_text, extract_note):
    """One piece per grant project code. Amount = sum of unspent budget over its ledger rows."""
    by = {}
    for r in rows:
        u = unspent(r)
        if u <= 0:
            continue
        k = r["grant_project_code"]
        g = by.setdefault(k, {"unspent": Decimal(0), "budget": Decimal(0), "expended": Decimal(0), "enc": Decimal(0),
                              "names": [], "funds": set(), "rows": 0, "extract": set()})
        g["unspent"] += u
        g["budget"] += Decimal(r["budget"] or 0)
        g["expended"] += Decimal(r["expended_project_to_date"] or 0)
        g["enc"] += Decimal(r["encumbrances"] or 0)
        g["names"].append((Decimal(r["budget"] or 0), r["grant_project_description"]))
        g["funds"].add(r["fund_code"])
        g["rows"] += 1
        g["extract"].add(r["data_extract_as_of_date"][:10])
    pcs = []
    for k, g in by.items():
        name = nice(max(g["names"])[1])
        amt = dol(g["unspent"])
        pcs.append({"key": "ledger-" + k, "name": name, "amount": amt, "basis": "gov_estimate",
                    "source": {"doc": "City Mid-Year Grants 925 ledger, extract %s" % ", ".join(sorted(g["extract"])), "url": LEDGER_URL,
                               "note": extract_note},
                    "note": "Grant project code %s, fund codes %s, %d ledger row(s). Unspent = budget %s minus expended to date %s (money on order but not yet paid still counts as unspent)."
                            % (k, ", ".join(sorted(g["funds"])), g["rows"], f"${g['budget']:,.0f}", f"${g['expended']:,.0f}"),
                    "extra": {"grant_project_code": k, "fund_codes": sorted(g["funds"]), "ledger_budget": dol(g["budget"]),
                              "expended_to_date": dol(g["expended"]), "encumbered": dol(g["enc"])},
                    "why": why_text if amt >= T10 else None})
    pcs.sort(key=lambda x: -x["amount"])
    return pcs


def check(sp, label):
    line = Decimal(str(sp["expect_amount"]))
    tot = sum(Decimal(str(p["amount"])) for p in sp["pieces"])
    assert tot <= line, f"{label}: pieces {tot} exceed line {line}"
    for p in sp["pieces"]:
        ks = sum(Decimal(str(k["amount"])) for k in p.get("children", []))
        assert ks <= Decimal(str(p["amount"])), f"{label}: children exceed piece {p['name']}"
    print(f"  {label}: line ${line:,.2f}  pieces ${tot:,.2f} ({len(sp['pieces'])})  not itemised ${line - tot:,.2f}  ({tot / line:.1%})")



# lines handled elsewhere in this file or by other agents (airports are dept 85 and are skipped)
DONE_AUTH = {("925F", "84", "281S"), ("925F", "84", "281U"), ("925S", "84", "280E"), ("925S", "84", "280Q")}
# ledger fund codes for CDOT lines whose grant has no federal ALN in Summary G
FUND_RULE = {("925S", "84", "280M"): {"F0W24"}, ("925L", "84", "281T"): {"FG413", "F0W03", "F0W01", "F0M09"}}


def other_reserves(led_all, done):
    """Reserve Balance (909A) lines other than airports and the four CDOT lines above.
    A ledger row is placed on a line when department and grant (ALN, or fund code for CDOT lines) match and the row maps to ONE line
    (using the ledger's composite fund code when several lines share a department and ALN). Rows that could be on several lines,
    and lines whose matched projects add up to more than the reserve, are listed as side facts and not boxes."""
    ra = json.load(open(os.path.join(ROOT, "data", "city_grants_2026.json")))["reserve_attribution"]["lines"]
    rows = [r for r in led_all if r["data_extract_as_of_date"].startswith("2026")]
    cands = {}      # row id -> list of line indexes
    lines = []
    for l in ra:
        if l["dept_number"] == "085" or not l.get("named_items"):
            continue
        key = (l["fund_code"], l["dept_number"].lstrip("0"), l["authority_code"])
        if key in DONE_AUTH:
            continue
        lines.append((key, l))
    def match(l, key, r):
        if r["department_code"] != "D" + key[1].zfill(2):
            return False
        if key in FUND_RULE:
            return r["fund_code"] in FUND_RULE[key]
        return bool(l.get("aln")) and r["aln_code"] == l["aln"]
    for i, (key, l) in enumerate(lines):
        for r in rows:
            if match(l, key, r):
                cands.setdefault(r["record_id"], []).append(i)
    assigned = {}
    ambiguous = {}
    for r in rows:
        c = cands.get(r["record_id"], [])
        if len(c) == 1:
            assigned[r["record_id"]] = c[0]
        elif len(c) > 1:
            comp = r["composite_fund_code"][1:] if r["composite_fund_code"] else ""
            ok = [i for i in c if lines[i][0][0] == comp]
            if len(ok) == 1:
                assigned[r["record_id"]] = ok[0]
            else:
                ambiguous[r["record_id"]] = c
    out = []
    for i, (key, l) in enumerate(lines):
        res = Decimal(str(l["reserve_amount"]))
        mine = [r for r in rows if assigned.get(r["record_id"]) == i and unspent(r) > 0]
        amb = [r for r in rows if r["record_id"] in ambiguous and i in ambiguous[r["record_id"]] and unspent(r) > 0]
        tot = sum(unspent(r) for r in mine)
        sidec = lambda r, why: {"kind": "ledger_project", "label": "%s (project %s, fund %s, ledger record %s): %s" % (nice(r["grant_project_description"]), r["grant_project_code"], r["fund_code"], r["record_id"], why),
                                "amount": dol(unspent(r)), "period": "ledger 2026-05-31", "basis": "gov_estimate",
                                "source": {"doc": "City Mid-Year Grants 925 ledger, extract 2026-05-31", "url": LEDGER_URL}}
        tgt = {"by": "ordinance_line", "fund": key[0], "dept": key[1], "authority": key[2], "account": "909A"}
        gname = l["grant_name"]
        side = [sidec(r, "unspent budget, could belong to more than one reserve line of this grant, so not placed") for r in amb]
        if mine and tot <= res:
            why = "This is the part of one named grant project that the City has been promised but has not spent yet."
            pcs = ledger_pieces(mine, why, "Extract as of 2026-05-31. Grant: %s." % gname)
            sp = {"target": tgt, "expect_amount": dol(res), "mode": "budget_split", "pieces": pcs,
                  "residual": {"name": "Reserve not matched to a project in the City's grant ledger"},
                  "note": "Named projects come from the City's Mid-Year Grants ledger (department and grant %s), amount = budget minus spent so far. The ledger is dated 2026-05-31 and the reserve about Aug 2025, so these are caps, not exact shares of the reserve." % (l.get("aln") or "fund codes"),
                  "side": side}
            check(sp, "%s %s %s 909A" % key); out.append(sp)
        elif mine or amb:
            side = [sidec(r, "unspent budget") for r in mine] + side
            if mine:
                note = "Matched ledger projects add up to $%s, which is more than this $%s reserve, so they are shown as facts and not as boxes (we cannot say which part of each project this reserve covers)." % (f"{tot:,.0f}", f"{res:,.0f}")
            else:
                note = "Ledger projects for this grant could sit on more than one reserve line, so they are shown as facts and not as boxes."
            sp = {"target": tgt, "expect_amount": dol(res), "mode": "side_only", "note": note, "side": side}
            print("  side only %s %s %s 909A: reserve $%s, matched $%s, ambiguous rows %d" % (key + (f"{res:,.0f}", f"{tot:,.0f}", len(amb))))
            out.append(sp)
    return out


# Chicago-sponsored local-system projects in IDOT's FY2026 Annual Highway Improvement Program (district 1, local construction and local engineering)
AHP_NBRS = ["1-22003-0000", "1-22304-0000", "1-21283-0000", "1-22369-0000", "1-22473-0000", "1-22379-0000", "1-21951-0010", "1-22302-0002",
            "1-22821-0000", "1-22305-0000", "1-22306-0000", "1-22307-0000", "1-22308-0000", "1-21759-0000", "1-21760-0000", "1-22537-0000",
            "1-22539-0000", "1-22368-0000", "1-22463-0000"]


def ahp_side():
    """Read each project number from raw/grants_tree/idot_fy26_ahp.txt: location, funds, cost and PDF page. Amounts are IDOT's 'Estimated Cost'."""
    path = os.path.join(ROOT, "raw", "grants_tree", "idot_fy26_ahp.txt")
    lines = open(path).read().split("\n")
    page, pg = None, {}
    for i, l in enumerate(lines):
        m = re.match(r"=====PAGE (\d+)=====", l)
        if m:
            page = int(m.group(1))
        pg[i] = page
    out = []
    for nbr in AHP_NBRS:
        for i, l in enumerate(lines):
            if l.rstrip().endswith(nbr):
                m = re.search(r"\s([A-Z, ]*?)\s?([\d,]{6,})\s+([A-Z][A-Z /().#-]+?)\s+" + re.escape(nbr), l)
                if not m:
                    continue
                cost = Decimal(m.group(2).replace(",", ""))
                label = l[:m.start(2)].strip()
                out.append({"kind": "idot_ahp_project", "label": "IDOT FY2026 Annual Highway Improvement Program, Chicago local project %s: %s (%s)" % (nbr, label, m.group(3).strip().title()),
                            "amount": dol(cost), "period": "IDOT FY2026 (Jul 2025 to Jun 2026)", "basis": "gov_estimate",
                            "source": {"doc": "IDOT FY 2026 Annual Highway Improvement Program (Combined, final 09/23/25)", "url": "https://idot.illinois.gov/content/dam/soi/en/web/idot/documents/transportation-system/maps---charts/proposed-improvements/fy2026/FY26_Annual_Highway_Program_Combined_Final_092325.pdf",
                                       "page": "PDF page %d (printed page 1 - %d), District 1" % (pg[i], pg[i] - 20)}})
                break
        else:
            print("  AHP project not found", nbr)
    return out

# ---------------------------------------------------------------- build
def main():
    if not os.path.isdir(TIP_DIR) or len(os.listdir(TIP_DIR)) < 100:
        sys.exit("raw/cdot/tip3488 missing: run  python3 scripts/cdot_etip_fetch.py 3488 16811 cdot")
    tip = load_tip()
    led_all = load_ledger()
    led = cdot(led_all)
    splits = []

    # ---- 1. 925F 281S 0540: federal highway construction ($451,646,229)
    fed_total = sum(r["fy2026"] for p in tip for r in p["rows"] if r["fund"] in FED_HWY)
    why_fed = "This is federal road, bridge or trail money that the regional plan (the TIP) lists for this one job in 2026, and the job is paid in a few big chunks."
    pcs = tip_pieces(tip, FED_HWY, why_fed, "FFY2026 programmed federal highway funds (STP, TAP, CMAQ, NHFP) in the TIP, not the City's own budget number")
    other_fed = [(p, r) for p in tip for r in p["rows"] if r["fund"] in ("Other - Federal", "Community Project Funding") and r["fy2026"] > 0]
    side = [{"kind": "tip_federal_not_placed", "label": "%s %s: %s, %s (federal money in the TIP that is not federal-highway type, so not placed on this line)" % (p["id"], p["title"], r["phase"], r["fund"]),
             "amount": dol(r["fy2026"]), "period": "FFY2026", "basis": "gov_estimate", "source": tip_src(p, "FFY2026 column")} for p, r in other_fed]
    side.append({"kind": "cdot_stp_program", "label": "CDOT's own FFY2026 STP-L program (updated 02/10/2026): 92nd St Bridge $10.0M, Arterial Resurfacing $12.17M, Bridge and Viaduct Painting #11 $2.48M, Canal St Harrison to Taylor $40.12M, Signal Controller Modernization #1 $4.0M, Bridge Inspection $8.0M",
                 "amount": 76775306, "period": "FFY2026", "basis": "gov_estimate",
                 "source": {"doc": "CDOT FFY 2024-2029 STP Program, updated 02/10/2026", "url": "https://cmap.illinois.gov/wp-content/uploads/CDOT_2025-2029-STP-Program-20260210.pdf", "page": 1}})
    side.extend(ahp_side())
    MYP = "https://capitolnewsillinois.com/wp-content/uploads/2025/10/MYP_FY2026-31_Final_1025_BothLists-1.pdf"
    side.append({"kind": "federal_award_to_idot", "label": "Federal Bridge Investment Program grant 693JJ22440000Y17FILJ498286 for the Calumet River bridges (92nd/Ewing, 95th, 100th, 106th Streets). The federal money is awarded to IDOT, not the City: $144,000,000 obligated, $145,500,000 non-federal match, $289,500,000 total, $34,274 spent. IDOT's FY2026 program shows these bridges as discretionary-grant (DG) projects: Ewing Ave $100,000,000 and 95th St $43,000,000. We cannot tell how much of it runs through the City's 925F line, so it is not a box.",
                 "amount": 144000000, "period": "signed 2024-08-29", "basis": "gov_estimate",
                 "source": {"doc": "USASpending.gov award 693JJ22440000Y17FILJ498286 (API /api/v2/awards/ASST_NON_693JJ22440000Y17FILJ498286_069/, checked 2026-10-02)", "url": "https://www.usaspending.gov/award/ASST_NON_693JJ22440000Y17FILJ498286_069"}})
    side.append({"kind": "gap_views", "label": "Three public views of 2026 federal road money for Chicago do not add to this line: the City ordinance line $451,646,229 (anticipated 2026 grant $452,121,000 per Summary G), the CMAP TIP federal-highway funds programmed in FFY2026 $233,519,343 (boxes above), and federal-type Chicago local projects in IDOT's FY2026 annual program $291,533,000 (19 projects, of which $143,000,000 is two Calumet River bridge projects that IDOT labels discretionary grant (DG), which fits the Bridge Investment Program grant above, awarded to IDOT). The remainder is shown as not itemised.",
                 "amount": 218126886, "period": "2026", "basis": "gov_estimate",
                 "source": {"doc": "City 2026 Budget Recommendations Summary G p. 606 (PDF 615); CMAP eTIP; IDOT FY2026 Annual Highway Improvement Program", "url": "https://idot.illinois.gov/content/dam/soi/en/web/idot/documents/transportation-system/maps---charts/proposed-improvements/fy2026/FY26_Annual_Highway_Program_Combined_Final_092325.pdf"}})
    for lbl, amt, pgn in (("Jeffrey Dr / Marquette Dr / South Shore Dr (US 41) construction and construction engineering, years 2027-2031 ($52,000,000 + $8,000,000)", 60000000, 336),
                          ("100th St bridge over the Calumet River, superstructure replacement, years 2027-2031", 39193000, 339),
                          ("California Ave bridge over the Sanitary and Ship Canal, years 2027-2031 ($26,601,000 + $117,000)", 26718000, 343),
                          ("Ogden Ave Pulaski to Western reconstruction, years 2027-2031", 19858000, 353)):
        side.append({"kind": "idot_myp_future", "label": "IDOT Multi-Year Program FY2026-2031, District 1 local highways, Chicago: %s (a later year, not 2026)" % lbl, "amount": amt, "period": "2027-2031", "basis": "gov_estimate",
                     "source": {"doc": "IDOT FY 2026-2031 Proposed Highway & Multimodal Improvement Program (October 2025), District 1 local project list", "url": MYP, "page": "PDF page %d (file identical to the IDOT publication)" % pgn}})
    sp = {"target": {"by": "ordinance_line", "fund": "925F", "dept": "84", "authority": "281S", "account": "0540"},
          "expect_amount": 451646229.0, "mode": "budget_split", "pieces": pcs,
          "residual": {"name": "Federal highway money with no project in the regional plan for 2026",
                       "why": "The City budgeted much more federal road money than the regional plan lists for 2026, and no public list says which jobs the rest will pay for."},
          "note": "Projects are the CMAP TIP 2026-2030 entries led by CDOT, with federal-highway funds (STP, TAP, CMAQ, freight) programmed in federal fiscal year 2026 (Oct 2025 to Sep 2026). That year is not the City's calendar 2026, and the TIP does not say which City budget line each fund pays through, so the match is by fund type.",
          "side": side}
    check(sp, "925F 281S 0540"); splits.append(sp)
    fed_placed = sum(Decimal(str(p["amount"])) for p in pcs)
    assert fed_placed == fed_total

    # ---- 2. 925S 280E 0540: IDOT state funds, construction ($117,368,000)
    state_rows = [(p, r) for p in tip for r in p["rows"] if r["fund"] in STATE and r["fy2026"] > 0]
    state_total = sum(r["fy2026"] for _, r in state_rows)
    cal = next(p for p in tip if p["id"] == "01-24-0017")
    cal_state = tip_children(cal, {"State Match - Chicago"})
    why_st = "This is state money for the Calumet River bridge rebuilds (92nd, 95th, 100th and 106th Streets), and the bridge work is paid in a few very large chunks."
    for k in cal_state:
        k["why"] = why_st
    cal_amt = sum(Decimal(str(k["amount"])) for k in cal_state)
    pc = {"key": cal["id"], "name": "%s: %s" % (cal["id"], cal["title"]), "amount": dol(cal_amt), "basis": "proxy",
          "source": tip_src(cal, "FFY2026 State Match - Chicago, construction and construction engineering"),
          "note": cal["ctl"].get("Project Description"), "extra": {"tip_id": cal["id"], "etip_project_id": cal["projectId"]},
          "children": [dict(k, basis="proxy") for k in cal_state]}
    side2 = []
    for p, r in sorted(state_rows, key=lambda x: -x[1]["fy2026"]):
        if p["id"] == cal["id"]:
            continue
        side2.append({"kind": "tip_state_not_placed", "label": "%s %s: %s, %s" % (p["id"], p["title"], r["phase"], r["fund"]),
                      "amount": dol(r["fy2026"]), "period": "FFY2026", "basis": "gov_estimate", "source": tip_src(p, "FFY2026 column")})
    sp = {"target": {"by": "ordinance_line", "fund": "925S", "dept": "84", "authority": "280E", "account": "0540"},
          "expect_amount": 117368000.0, "mode": "budget_split", "pieces": [pc],
          "residual": {"name": "State road money with no project named in the regional plan for 2026",
                       "why": "The regional plan lists only one project big enough to fit this state line, and it does not say which jobs the rest of the line will pay for."},
          "note": "The CMAP TIP programs $%s of state-type money (State Match - Chicago, IL Funds, Local Project Funding) for CDOT projects in federal fiscal year 2026. That is more than this line, so the other projects are shown as side facts, not boxes. Calumet River Bridges alone is $%s of State Match and is the one project that fits inside the line. The amounts are the TIP's own numbers (gov_estimate), but which project to place on this line is our choice (basis proxy), because the TIP does not say which budget line a state fund pays through." % (f"{state_total:,.0f}", f"{cal_amt:,.0f}"),
          "side": side2}
    check(sp, "925S 280E 0540"); splits.append(sp)

    # ---- 2b. 925S 280Q 0540: Rebuild Illinois construction ($9,500,000)
    ar = next(p for p in tip if p["id"] == "01-20-0003")
    ar_ri = tip_children(ar, {"Rebuild Illinois"})
    ar_amt = sum(Decimal(str(k["amount"])) for k in ar_ri)
    can = next(p for p in tip if p["id"] == "01-12-0012")
    can_ri = [r for r in can["rows"] if r["fund"] == "Rebuild Illinois" and r["fy2026"] > 0]
    sp = {"target": {"by": "ordinance_line", "fund": "925S", "dept": "84", "authority": "280Q", "account": "0540"},
          "expect_amount": 9500000.0, "mode": "budget_split",
          "pieces": [{"key": ar["id"], "name": "%s: %s" % (ar["id"], ar["title"]), "amount": dol(ar_amt), "basis": "proxy",
                      "source": tip_src(ar, "FFY2026 Rebuild Illinois, construction"), "note": ar["ctl"].get("Project Description"),
                      "extra": {"tip_id": ar["id"], "etip_project_id": ar["projectId"]}, "children": [dict(k, basis="proxy") for k in ar_ri]}],
          "residual": {"name": "Rebuild Illinois money with no project named in the regional plan for 2026"},
          "note": "The TIP lists $15.8M of Rebuild Illinois money in FFY2026 (this resurfacing project $9.3M and Canal Street viaduct construction engineering $6.5M). Only the resurfacing fits inside this $9.5M line, so Canal Street is a side fact. Match is by fund type.",
          "side": [{"kind": "tip_state_not_placed", "label": "%s %s: %s, Rebuild Illinois" % (can["id"], can["title"], r["phase"]), "amount": dol(r["fy2026"]),
                    "period": "FFY2026", "basis": "gov_estimate", "source": tip_src(can, "FFY2026 column")} for r in can_ri]}
    check(sp, "925S 280Q 0540"); splits.append(sp)

    # ---- 2c. 925F 281K 0140 Safe Streets and Roads for All ($20,928,000)
    og = next(p for p in tip if p["id"] == "01-22-0043")
    nv = next(p for p in tip if p["id"] == "01-23-0005")
    og_ss = [r for r in og["rows"] if r["fund"] == "Safe Streets and Roads for All"][0]
    nv_ss = [r for r in nv["rows"] if r["fund"] == "Safe Streets and Roads for All"][0]
    sp = {"target": {"by": "ordinance_line", "fund": "925F", "dept": "84", "authority": "281K", "account": "0140"},
          "expect_amount": 20928000.0, "mode": "budget_split",
          "pieces": [{"key": og["id"], "name": "%s: %s" % (og["id"], og["title"]), "amount": dol(og_ss["total"]), "basis": "gov_estimate",
                      "source": tip_src(og, "Construction, Safe Streets and Roads for All, $%s, programmed in FFY2027 (not FFY2026)" % f"{og_ss['total']:,.0f}"),
                      "note": "The TIP programs $20,927,748 of Safe Streets and Roads for All money for this project, $252 below this $20,928,000 line. The TIP puts it in FFY2027 (Oct 2026 to Sep 2027), while the City budgets the grant in 2026, so the timing differs by a year. The line is the only Safe Streets grant in the 2026 ordinance, and this is the larger of the two Safe Streets projects in the TIP. Description: %s" % og["ctl"].get("Project Description"),
                      "extra": {"tip_id": og["id"], "etip_project_id": og["projectId"]},
                      "why": "This is one federal safety grant that the regional plan assigns to rebuilding Ogden Avenue from Pulaski to Roosevelt, and it is paid when the road work is bid."}],
          "residual": {"name": "Difference between the line and the TIP amount"},
          "note": "Match by amount: the TIP's Safe Streets money for Ogden Avenue is within $252 of this line. The TIP also lists $20,010,000 of Safe Streets money for North Avenue, Kostner to Kedzie (project 01-23-0005, FFY2027), which does not fit inside this line and is a side fact.",
          "side": [{"kind": "tip_federal_not_placed", "label": "%s %s: %s, Safe Streets and Roads for All (FFY2027)" % (nv["id"], nv["title"], nv_ss["phase"]), "amount": dol(nv_ss["total"]), "period": "FFY2027", "basis": "gov_estimate", "source": tip_src(nv, "FFY2027 column")}]}
    check(sp, "925F 281K 0140"); splits.append(sp)

    # ---- 2d. lines with no public project list (notes only, so a reader sees why the box stops here)
    ped = next(p for p in tip if p["id"] == "01-20-0006")
    splits.append({"target": {"by": "ordinance_line", "fund": "925F", "dept": "84", "authority": "281U", "account": "0540"}, "expect_amount": 10000000.0, "mode": "side_only",
                   "note": "This is the 2026 anticipated federal transit formula grant ($10,000,000, Summary G p. 606). No public list says which jobs it will pay for. The only CDOT-led transit-type project the TIP programs in FFY2026 is the Pedway reconstruction and wayfinding job, $3,236,583 of CMAQ money, and CMAQ money is not always federal transit money, so it is shown as a fact, not a box. The State/Lake station has no TIP money in FFY2026.",
                   "side": [{"kind": "tip_federal_not_placed", "label": "%s %s: Construction, CMAQ" % (ped["id"], ped["title"]), "amount": 3236583.0, "period": "FFY2026", "basis": "gov_estimate", "source": tip_src(ped, "FFY2026 column")}]})
    splits.append({"target": {"by": "ordinance_line", "fund": "925S", "dept": "84", "authority": "280M", "account": "0540"}, "expect_amount": 23600000.0, "mode": "side_only",
                   "note": "This is the 2026 anticipated State of Illinois (DCEO) road grant ($23,600,000, Summary G p. 606). The City's grant ledger shows DCEO road projects only as small ward-level jobs (lighting, alleys, sidewalks, 25 records, $16.2M budget in total), and the CMAP TIP has no DCEO fund source for CDOT projects. No public list says which jobs this new money will pay for."})

    # ---- 3. 925S 280E 909A reserve ($124,113,000): ledger projects paid by IDOT funds F0L98 and F0W23, 2026-05-31 extract
    why_res = "This is the part of one named road or bridge job's state grant that the City has been promised but has not spent yet."
    rows = [r for r in led if r["data_extract_as_of_date"].startswith("2026") and r["fund_code"] == "F0L98"]
    pcs = ledger_pieces(rows, why_res, "Extract as of 2026-05-31. Reserve is carryover cut about Aug 1 2025, so timing differs by about 10 months. Fund F0L98 IDOT Transportation Funds. The Illinois Competitive Freight Program (F0W23, ALN 20.205, federal freight money) is left out here because it is federal highway money counted on the FHWA reserve line.")
    sp = {"target": {"by": "ordinance_line", "fund": "925S", "dept": "84", "authority": "280E", "account": "909A"},
          "expect_amount": 124113000.0, "mode": "budget_split", "pieces": pcs,
          "residual": {"name": "State grant money with no project in the City's grant ledger",
                       "why": "The ledger lists named jobs for most of this money, and the rest has not been matched to a job in any public list. Part of it may be state money for jobs that are not yet in the ledger."},
          "note": "Named jobs come from the City's Mid-Year Grants ledger (state fund F0L98 IDOT Transportation Funds), amount = budget minus spent so far. The ledger was cut 2026-05-31 and the reserve about Aug 2025, so these are caps, not exact shares of the reserve."}
    check(sp, "925S 280E 909A"); splits.append(sp)

    # ---- 4. 925S 280Q 909A reserve ($117,880,000): Rebuild Illinois F0W32
    rows = [r for r in led if r["data_extract_as_of_date"].startswith("2026") and r["fund_code"] == "F0W32"]
    pcs = ledger_pieces(rows, why_res, "Extract as of 2026-05-31. Fund F0W32 Rebuild Illinois.")
    sp = {"target": {"by": "ordinance_line", "fund": "925S", "dept": "84", "authority": "280Q", "account": "909A"},
          "expect_amount": 117880000.0, "mode": "budget_split", "pieces": pcs,
          "residual": {"name": "Rebuild Illinois money with no project in the City's grant ledger",
                       "why": "The ledger names jobs for about half of this money, and the rest has not been matched to a job in any public list."},
          "note": "Named jobs come from the City's Mid-Year Grants ledger (fund F0W32 Rebuild Illinois), amount = budget minus spent so far, extract 2026-05-31. Caps, not exact shares of the reserve."}
    check(sp, "925S 280Q 909A"); splits.append(sp)

    # ---- 5. children of the existing FHWA 20.205 reserve piece ($121,122,530)
    why_h = "This is the part of one named road or bridge job's federal grant that the City has been promised but has not spent yet."
    new = [r for r in led if r["data_extract_as_of_date"].startswith("2026") and r["aln_code"] == "20.205"]
    old = [r for r in led if r["data_extract_as_of_date"].startswith("2025") and r["aln_code"] == "20.205"]
    new_codes = {r["grant_project_code"] for r in new}
    old_only = [r for r in old if r["grant_project_code"] not in new_codes]
    print("  FHWA reserve: 2026 rows", len(new), "2025-only rows", len(old_only), "old rows whose project code is also in 2026:", len(old) - len(old_only))
    pcs = ledger_pieces(new + old_only, why_h, "ALN 20.205 rows of the 2026-05-31 extract, plus rows of the 2025-06-01 extract whose project is not in the 2026 extract. Both extracts are in the existing $121.1M cap.")
    sp = {"target": {"by": "id", "id": "city.infrastructure-services.chicago-department-of-transportation.grant-money-not-yet-assigned-to-projects.925f-federal-grant-fund.925f-281s-909a.0-named-projects-unspent-budget"},
          "expect_amount": 121122530.0, "mode": "budget_split", "pieces": pcs,
          "residual": {"name": "Rounding between the two ledger extracts"},
          "note": "Split of the existing $121.1M cap into the named projects behind it (ledger rows with federal highway ALN 20.205)."}
    check(sp, "FHWA reserve child"); splits.append(sp)

    # ---- 6. children of the existing State/Lake piece ($329,801,213)
    # Facts behind the notes below come from scripts/state_lake_stp_check.py (see research/state_lake_stp.md).
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import state_lake_stp_check as slc
    slf = slc.facts()
    assert slf["dec2024"] == slf["old_budget"] == 102140573.0, "old ledger record is no longer the Dec 2024 FTA obligation"
    assert slf["jan2025_new"] + slf["jan2025_deob"] == 0 and slf["cum_after_jan2025"] == slf["cum_after_dec2024"], "Jan 2025 swap is no longer net zero"
    assert slf["fy2023_stp"] == slf["new_stp_budget"] == 34080000.0, "newer STP record is no longer the FY2023 tranche"
    assert abs(slf["ledger_plus_missing"] - slf["award_obligated"]) <= 1, "ledger plus the three missing obligations no longer equals the award"
    sl = [r for r in led if r["grant_project_code"] == "D1209"]
    lk = {}
    for r in sl:
        u = unspent(r)
        if u <= 0:
            continue
        src = {"F0W02": "Congestion Mitigation and Air Quality money", "F0W16": "Surface Transportation Program money", "FG665": "Carbon Reduction Program money", "FG624": "Community Project Funding"}[r["fund_code"]]
        via = " (direct FTA grant)" if "DIRECT" in r["grant_agency"] else ""
        key = (src + via, r["data_extract_as_of_date"][:10])
        g = lk.setdefault(key, {"u": Decimal(0), "b": Decimal(0), "e": Decimal(0), "rec": []})
        g["u"] += u; g["b"] += Decimal(r["budget"]); g["e"] += Decimal(r["expended_project_to_date"] or 0); g["rec"].append(r["record_id"])
    why_sl = "This is federal money already promised for the one State/Lake station rebuild, and it pays the main construction contract in large monthly chunks."
    pcs = []
    for (name, ext), g in sorted(lk.items(), key=lambda x: -x[1]["u"]):
        amt = dol(g["u"])
        pcs.append({"key": "sl-" + re.sub(r"\W+", "-", name.lower()) + "-" + ext, "name": "%s, not spent yet (ledger extract %s)" % (name, ext), "amount": amt, "basis": "gov_estimate",
                    "source": {"doc": "City Mid-Year Grants 925 ledger, extract %s, project D1209 State/Lake Loop Elevated" % ext, "url": LEDGER_URL},
                    "note": "Unspent = budget %s minus expended to date %s. Ledger record(s): %s.%s" % (f"${g['b']:,.0f}", f"${g['e']:,.0f}", ", ".join(g["rec"]),
                    (" This record is only in the older 2025-06-01 extract (nothing spent then, fully on order), and the newer 2026-05-31 extract has no record for it. "
                    "It is not a copy of the other Surface Transportation Program box or of any other box here. It is a separate federal obligation of $%s that the FTA recorded in December 2024 (USASpending) and never reversed: "
                    "the January 2025 de-obligations ($%s) were obligated again the same month, so the net change was zero. It equals CDOT's own FFY2024 STP programming for State/Lake ($77,140,573 plus $25,000,000 redistribution) to the dollar. "
                    "The other STP box is the unspent part of an earlier $%s obligation from FY2023. The FTA records in the 2026 ledger match obligations on this award (for example $34,080,000 from two FY2023 obligations, $65,430,000 from FY2024 and $15,000,000 from August 2025), and the 2026 ledger plus three obligations it does not list "
                    "(this one, $%s of STP and $%s more from August 2025, which we read as CMAQ) comes to the award to within $1. What the public records cannot show is how much of this $%s has been spent since June 2025, "
"so the box is the most that could still be unspent. Details: research/state_lake_stp.md." % (
                        f"{slf['old_budget']:,.0f}", f"{-slf['jan2025_deob']:,.0f}", f"{slf['new_stp_budget']:,.0f}",
                        f"{slf['aug2025_stp']:,.0f}", f"{slf['aug2025_cmaq']:,.0f}", f"{slf['old_budget']:,.0f}")) if ext.startswith("2025") else ""),
                    "extra": {"ledger_records": g["rec"]}, "why": why_sl if amt >= T10 else None})
    # contract and payment facts
    def pay_sum(fn, contract):
        n, s = 0, Decimal(0)
        for r in csv.DictReader(open(os.path.join(ROOT, "raw", "contracts", fn))):
            if r["contract_number"] == contract:
                n += 1; s += Decimal(r["amount"])
        return n, s
    n25, s25 = pay_sum("payments_2025_dedup.csv", "283596")
    n26, s26 = pay_sum("payments_2026ytd_dedup.csv", "283596")
    cip = next(p for p in json.load(open(os.path.join(ROOT, "data", "city_capital_2026.json")))["projects"] if p["cip_id"] == "40492")
    usa = next(a for a in json.load(open(os.path.join(ROOT, "raw", "grants", "usaspending_chicago_awards.json"))) if a["Award ID"] == "IL-2016-002")
    cs = lambda doc, url=None, page=None, note=None: {"doc": doc, "url": url, "page": page, "note": note}
    side = [
        {"kind": "project_cost", "label": "Reported total project cost (CDOT spokesperson: more than 90 percent federally funded). Up from $180M estimated in 2021 and $75M in 2017", "amount": 444000000, "period": "2025-12", "basis": "gov_estimate",
         "source": cs("Chicago Sun-Times, 2025-12-04", "https://chicago.suntimes.com/transportation/2025/12/04/state-lake-cta-station-closing-construction")},
        {"kind": "contract_award", "label": "Construction contract 283596 (F.H. Paschen S.N. Nielsen & Associates), original award 2025-01-15", "amount": 444347400, "period": "2025", "basis": "tied",
         "source": cs("City Vendor, Contract and Payment Search, contract 283596", "https://webapps1.chicago.gov/vcsearch/city/contracts/283596")},
        {"kind": "contract_award", "label": "Same contract, modification 2 approved 2026-06-30 (current award $548,215,560)", "amount": 103868160, "period": "2026", "basis": "tied",
         "source": cs("City Vendor, Contract and Payment Search, contract 283596", "https://webapps1.chicago.gov/vcsearch/city/contracts/283596")},
        {"kind": "paid_to_date", "label": "Paid to the construction contractor in calendar 2025 (%d payments)" % n25, "amount": dol(s25), "period": "2025", "basis": "paid_to_date",
         "source": cs("City payments dataset (s4vu-giwb), contract 283596", "https://data.cityofchicago.org/resource/s4vu-giwb")},
        {"kind": "paid_to_date", "label": "Paid to the construction contractor in 2026 so far (%d payments)" % n26, "amount": dol(s26), "period": "2026 to 09/28", "basis": "paid_to_date",
         "source": cs("City payments dataset (s4vu-giwb), contract 283596", "https://data.cityofchicago.org/resource/s4vu-giwb")},
        {"kind": "cip_total", "label": "City CIP 2025-2029 project 40492 State/Lake CTA Station, all funds, all years (federal 0W02 $167.4M, 0W16 $221.2M, 0997 $16.0M, city bonds $91.0M)", "amount": cip["total"]["total"], "period": "multi-year", "basis": "gov_estimate",
         "source": cs("City of Chicago 2025-2029 Capital Improvement Program", "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CIP/City%20of%202025-2029%20CIP.pdf", cip["pdf_page"])},
        {"kind": "tip_total", "label": "CMAP TIP 01-02-0030 State/Lake Station, total programmed (all prior years, none in FY2026): CMAQ $178.9M incl. $11.0M engineering, STP-L $196.2M, STP Shared $25.0M, Carbon Reduction $15.0M, Community Project $1.0M, local $65.8M", "amount": 481925718, "period": "multi-year", "basis": "gov_estimate",
         "source": cs("CMAP eTIP TIP 2026-2030, project 01-02-0030", ETIP_URL)},
        {"kind": "stp_programmed", "label": "CDOT STP-L program: State/Lake construction FFY2024 $77,140,573 + $25,000,000 redistribution, FFY2025 $68,552,719 + $16,447,281 redistribution", "amount": 187140573, "period": "FFY2024-2025", "basis": "gov_estimate",
         "source": cs("CDOT FFY 2024-2029 STP Program, updated 02/10/2026", "https://cmap.illinois.gov/wp-content/uploads/CDOT_2025-2029-STP-Program-20260210.pdf", 1)},
        {"kind": "federal_obligations", "label": "FTA award IL-2016-002 obligations by FTA fiscal year (USASpending award funding history, checked 2026-10-02): 2017 to 2021 $5,000,000, 2023 $88,009,999, 2024 $65,430,000, 2025 $250,180,573, total $408,620,572 (the award page shows $414,620,572, so $6.0M is not in the account-level history). Includes a $102,140,573 obligation in FTA month 3 of 2025, the same amount as the old ledger record, and later de-obligations of $55,300,000 and $9,774,524 offset by new obligations", "amount": 408620572, "period": "2017-2025", "basis": "gov_estimate",
         "source": cs("USASpending.gov, award funding history for IL-2016-002", "https://api.usaspending.gov/api/v2/awards/funding/ (award ASST_NON_IL-2016-002_069)")},
        {"kind": "federal_award", "label": "FTA award IL-2016-002 obligated (USASpending, Aug 2025 snapshot). Unspent = obligation minus outlays $84.8M", "amount": dol(Decimal(str(usa["Award Amount"]))), "period": "1999-10 to 2031-03", "basis": "gov_estimate",
         "source": cs("USASpending.gov award IL-2016-002", USA_URL)},
        {"kind": "bid_allowance", "label": "Bid book Schedule of Prices, City-fixed allowances inside the construction contract: track flagging operations $3,500,000 and track access occurrences $3,500,000 (items 1 and 2), disposal of regulated substances $250,000 (item 5), utility service work $250,000 (item 11). Together $7,500,000 of the contract", "amount": 7500000, "period": "bid 2024", "basis": "gov_estimate",
         "source": cs("Spec 1269715 Book 2, Schedule of Prices", "https://www.chicago.gov/content/dam/city/depts/dps/ContractAdministration/Specs/2024/Spec1269715_Book2.pdf", "PDF pages 22 and 23 (printed pages 19 and 20)")},
        {"kind": "bid_scope", "label": "The same Schedule of Prices has 15 work items: 4 allowances above, then lump sums (bidder's price, not published) for mobilization, civil, structural, architectural, plumbing, mechanical, electrical, communications, track work, traction power, and signal and train control work. The winning bid's price for each lump sum is not in any public file we could reach (the City bid-tabulation search returned no record for specification 1269715).", "period": "bid 2024", "basis": "gov_estimate",
         "source": cs("Spec 1269715 Book 2, Schedule of Prices", "https://www.chicago.gov/content/dam/city/depts/dps/ContractAdministration/Specs/2024/Spec1269715_Book2.pdf", "PDF pages 22 and 23")},
        {"kind": "gap", "label": "No public cost breakdown of the $444M by part (station, track, utilities) was found beyond the allowances above. CTA and CDOT pages give only the total.", "period": "", "basis": "gov_estimate",
         "source": cs("Spec 1269715 Book 2", "https://www.chicago.gov/content/dam/city/depts/dps/ContractAdministration/Specs/2024/Spec1269715_Book2.pdf")},
    ]
    sp = {"target": {"by": "id", "id": "city.infrastructure-services.chicago-department-of-transportation.grant-money-not-yet-assigned-to-projects.925f-federal-grant-fund.925f-281u-909a.0-state-lake-loop-elevated-station-one-na"},
          "expect_amount": 329801213.0, "mode": "budget_split", "pieces": pcs,
          "residual": {"name": "Rest of the federal award not shown by funding source in the City ledger",
                       "why": "The federal award is bigger than the amounts the City ledger lists by funding source, and no public record splits the rest into station, track or utility work."},
          "note": "The cap is the federal award IL-2016-002 (obligated minus outlays). The City ledger shows part of it by funding source, and the rest is shown as not itemised.",
          "side": side}
    check(sp, "State/Lake child"); splits.append(sp)


    # ---- 7. other (non-airport) 909A Reserve Balance lines: named ledger projects, one line per ledger row
    splits.extend(other_reserves(led_all, splits))

    meta = {"author": "cdot agent", "built_by": "scripts/cdot_build.py",
            "description": "CDOT project-level pieces: CMAP TIP 2026-2030 FFY2026 programmed amounts for the federal and state construction lines, City Mid-Year Grants ledger projects for the IDOT, Rebuild Illinois and FHWA reserves, and the State/Lake funding sources with contract facts."}
    json.dump({"meta": meta, "splits": splits}, open(OUT, "w"), indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
