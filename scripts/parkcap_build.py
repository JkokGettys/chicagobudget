#!/usr/bin/env python3
"""parkcap_build.py: assemble per-project capital dollars for the Chicago Park District -> data/parks_capital_projects.json

Run order: parkcap_fetch.py, parkcap_schedules.py (OCR of MWBE schedules), then this script.
Nothing is estimated. Every dollar below is copied from a cited public record or derived by a stated rule:
  tif_cip_lines      City TIF Projections 2025-2034 (Socrata fpsv-qjg3), lines that are Park District projects. Per-year amounts.
  tif_iga_approvals  City TIF agreements list (Socrata mex4-ppfc), developer = Chicago Park District: approved TIF amount and total project cost.
  board_awards       Board of Commissioners actions (Legistar): amounts printed in the title, plus the contract price implied by the
                     MWBE Schedule A of the bid (see parkcap_schedules.py; labelled implied, not an audited award).
  bonfire_contracts  Bonfire public contracts library: stated contract value for capital contracts.
  featured           Park District web pages and the 2026 budget narrative (stated project budgets).
  grants             IDNR OSLAD announcements, USAspending (recipient Chicago Park District), aldermanic menu lines for the District.
Join key: Park District park number, matched to data/parks_2026.json park nodes (unit_code) and the capital layer cap24_3.
"""
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "parkcap")
G = os.path.join(ROOT, "raw", "grants")
OUT = os.path.join(ROOT, "data", "parks_capital_projects.json")

P = json.load(open(os.path.join(ROOT, "data", "parks_2026.json")))
CAP = json.load(open(os.path.join(ROOT, "raw", "parks", "cap24_projects.json")))
LAYER = json.load(open(os.path.join(RAW, "chicago_parks_layer.json")))["features"]

# ---------------------------------------------------------------- park directory
budget_nodes = {}  # park_no -> node


def walk(n):
    if n.get("type") == "park":
        budget_nodes[int(n["unit_code"])] = n
    for c in n.get("children", []):
        walk(c)


walk(P["tree"])

names = {}  # park_no -> set of names
for f in LAYER:
    a = f["attributes"]
    if a["PARK_NO"] is not None:
        names.setdefault(int(a["PARK_NO"]), set()).add(a["PARK"] or "")
for c in CAP:
    if c.get("PARK_NO") is not None:
        names.setdefault(int(c["PARK_NO"]), set()).add(c["PARK_NAME"] or "")
for k, n in budget_nodes.items():
    names.setdefault(k, set()).add(n["name"])

STOP = {"park", "playground", "field", "fieldhouse", "house", "the", "of", "and", "pool", "sports", "center", "community", "cultural", "plaza"}


def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("&", " and "))


def keys_for(nm):
    out = set()
    base = re.sub(r"\(.*?\)", "", nm).strip()
    for part in [base] + re.findall(r"\((.*?)\)", nm):
        t = " ".join(w for w in norm(part).split() if w not in STOP)
        if len(t) >= 4:
            out.add(t)
    return out


KEYMAP = collections.defaultdict(set)  # key phrase -> park numbers
for pn, ns in names.items():
    if pn >= 1000 and pn not in budget_nodes:
        pass
    for nm in ns:
        if nm.upper().startswith("PARK NO"):
            continue
        for k in keys_for(nm):
            KEYMAP[k].add(pn)

# Hand-verified overrides, checked against park names/addresses in the Chicago_Parks layer and the cap24 capital layer.
# fragment (lowercase, matched as substring of the record text) -> park number. None = deliberately unjoined (ambiguous or multi-park).
TEXT_OVERRIDE = {
    "near north park athletic field": None,   # name-key matched an unrelated park called 'Athletic Field'
    "humbolt park batting cages": 219,        # sic in source, Humboldt
    "gomper park field house": 40,            # sic, Gompers
    "chicago park district headquarters": 596, "hq/park": 596, "4800 s western": 596,
    "clark (john) pool": 1026, "wilson (frank) playground": 145, "park women's park": 550, "chicago women's": 550,
    "morgan park sports center": 577, "greenbaum park": 132,   # Greenebaum (Henry) is park 132
    "garfield park conservatory": 204, "garfield park bandstand": 204,
}
# Board of Commissioners items: matter id -> park number (None = several parks or not a single park). Contractor names polluted name matching.
BOARD_PARK = {
    6381: None, 6360: 19, 6318: 478, 6246: None, 6228: 8, 6175: 218, 6116: 596, 6117: 230, 5964: 204, 5966: 478, 5968: 598, 5911: 236,
    5890: 275, 5891: 131, 5899: 1001, 5883: 1268, 5851: 1002, 5823: 122, 5802: 204, 5759: 204, 5688: None, 5670: 236, 5671: 1051,
    5643: 175, 5603: 19, 5594: 478, 5569: 108, 5568: 185, 4507: 596, 5536: 275, 5522: 1268, 4468: 596, 4458: 123, 4295: 244,
    4279: None, 4188: 596, 4166: None, 3988: 244,
}


def resolve(text):
    """Return (park_no, how). Overrides first, then explicit 'Park 0122' / 'Park 599' / 'Park #598', then unique name phrase."""
    t = text
    for frag, pn in TEXT_OVERRIDE.items():
        if frag in t.lower():
            return pn, "hand-verified override" if pn else "deliberately unjoined"
    m = re.search(r"\bpark\s*(?:no\.?|#)?\s*0*(\d{1,4})\b", t, re.I)
    if m and int(m.group(1)) in names and not re.search(r"park\s*\d+\s*(st|nd|rd|th)\b", t, re.I):
        return int(m.group(1)), "park number in text"
    tn = " " + norm(t) + " "
    hits = {}
    for k, pns in KEYMAP.items():
        if " " + k + " " in tn:
            for pn in pns:
                hits[pn] = max(hits.get(pn, 0), len(k))
    if not hits:
        return None, "no match"
    best = max(hits.values())
    top = [pn for pn, l in hits.items() if l == best]
    if len(top) == 1:
        return top[0], "unique name match"
    # prefer a park that has a budget node and capital projects
    cand = [pn for pn in top if pn in budget_nodes]
    if len(cand) == 1:
        return cand[0], "name match, disambiguated by budget park list"
    return None, "ambiguous " + ",".join(map(str, sorted(top)))


def parkinfo(pn):
    if pn is None:
        return {"park_no": None}
    nm = sorted(names.get(pn, []), key=len)
    bn = budget_nodes.get(pn)
    return {"park_no": pn, "park_name": (bn["name"] if bn else (nm[0] if nm else None)),
            "in_budget_park_list": bool(bn), "budget_node_id": bn["id"] if bn else None}


def money(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


records = {}

# ---------------------------------------------------------------- 1. TIF projections (fpsv-qjg3)
tif_lines = []
pat = re.compile(r"^(IGA|Parks?)\s*-|^IGA\b|^CPD\b", re.I)  # lines the City labels as Park District IGAs or Parks
skip = re.compile(r"CDOT|ADA Polling|CPS|CTA|\bRDA\b|AIS|DPD|MSAC|2FM|Study|Hanson|Madison Community Plaza|Northside College", re.I)
for x in json.load(open(os.path.join(G, "ds_fpsv-qjg3.json"))):
    t = x["line_item_description"]
    cat = x["category_description"]
    if cat.startswith("Transfers"):
        continue  # inter-TIF transfers are offsetting pairs, excluded to avoid double counting
    if not (pat.search(t) or re.match(r"Parks? - ", t)) or skip.search(t):
        continue
        continue
    yrs = {str(y): abs(money(x.get("_" + str(y)))) for y in range(2025, 2035)}
    s2630 = sum(yrs[str(y)] for y in range(2026, 2031))
    pn, how = resolve(t)
    tif_lines.append({"tif_district": x["tif_district_name"], "tif_district_id": x["tif_district_id"], "category": cat, "line": t,
                      "by_year": yrs, "total_2026_2030": s2630, "total_2026_2034": sum(yrs[str(y)] for y in range(2026, 2035)),
                      "park_join": how, **parkinfo(pn)})

# ---------------------------------------------------------------- 2. TIF IGA approvals (mex4-ppfc)
tif_iga = []
for x in json.load(open(os.path.join(G, "ds_mex4-ppfc.json"))):
    if "park district" not in (x.get("developer") or "").lower():
        continue
    pn, how = resolve(x["project_name"])
    tif_iga.append({"id": x["id"], "tif_district": x["tif_district"], "project": x["project_name"], "cdc_date": (x.get("cdc_date") or "")[:10],
                    "coc_date": (x.get("coc_date") or "")[:10] or None, "approved_tif": money(x.get("approved_amount")),
                    "total_project_cost": money(x.get("total_project_cost")) or None, "park_join": how, **parkinfo(pn)})

# ---------------------------------------------------------------- 3. Board awards (Legistar)
matters = {m["MatterId"]: m for m in json.load(open(os.path.join(RAW, "matters_all.json")))}
sched = json.load(open(os.path.join(RAW, "schedules_implied.json")))
board = []
cap_title = re.compile(r"construct|renovat|reconstruct|rehabilit|restoration|improvement|development|fieldhouse|field house|design|"
                       r"architect|engineering|HVAC|ADA|roof|turf|playground|shoreline|revetment|track", re.I)
not_cap = re.compile(r"CHAPTER|SETTLEMENT|NAME |SUPPLY|MAINTENANCE|FLORAL|LANDSCAP|JANITORIAL|CELLULAR|VIDEO|POOL CHEM|EXTENSION OPTION|"
                     r"MANAGEMENT AND OPERATION|CONCESSION|TREE INVENTORY|BONDS|BOND ANTICIPATION|REFUNDING|PLANTING", re.I)
for mid, m in matters.items():
    if m["MatterTypeName"] != "Action Item" or (m["MatterIntroDate"] or "") < "2018":
        continue
    title = " ".join((m["MatterTitle"] or "").split())
    if not cap_title.search(title) or not_cap.search(title):
        continue
    amt = re.search(r"(?:NTE|NOT TO EXCEED)?\s*\$\s?([\d,]+(?:\.\d\d)?)", title)
    s = sched.get(str(mid), {})
    if not amt and "implied_price" not in s:
        continue
    if mid in BOARD_PARK:
        pn, how = BOARD_PARK[mid], ("hand-verified from title" if BOARD_PARK[mid] else "several parks / not a single park")
    else:
        pn, how = None, "not joined (new item, add to BOARD_PARK)"
    kind = "change order" if re.search(r"CHANGE ORDER|MODIFICATION", title, re.I) else ("design/engineering" if re.search(r"DESIGN|ARCHITECT|ENGINEERING", title, re.I) else "construction/other")
    rec = {"matter_id": mid, "file": m["MatterFile"], "date": (m["MatterAgendaDate"] or m["MatterIntroDate"] or "")[:10], "title": title, "kind": kind,
           "amount_in_title": money(amt.group(1).replace(",", "")) if amt else None,
           "implied_price_from_mwbe_schedule": s.get("implied_price"), "implied_pairs_used": s.get("pairs_used"),
           "legistar_url": f"https://chicagoparkdistrict.legistar.com/LegislationDetail.aspx?ID={mid}&GUID={m['MatterGuid']}",
           "schedule_pdf": s.get("attachment"), "park_join": how, **parkinfo(pn)}
    board.append(rec)

# ---------------------------------------------------------------- 4. Bonfire capital contracts
bf = json.load(open(os.path.join(RAW, "bonfire_details.json")))
bonf = []
bcap = re.compile(r"renovation|construction|improvements|development|park \d+|park #|field house|fieldhouse|thorium|sheet pile|children's garden|campus", re.I)
for cid, v in bf.items():
    d = v["publicContractDetails"]
    name = d["Name"]
    if not bcap.search(name) or re.search(r"customer service|maintenance|management and operation|landscape maint|supply|floral|P-23001 General|permit", name, re.I):
        continue
    vals = [money(k["Value"]) for k in v["publicContractKeyValues"] if k["Key"] == "Value" and money(k["Value"]) > 0]
    if not vals:
        continue
    kv = {k["Key"]: k["Value"] for k in v["publicContractKeyValues"]}
    pn, how = resolve(name)
    start = None
    for t in v["publicContractTerms"].values():
        for r in t:
            if r.get("StartDate"):
                start = start or r["StartDate"][:10]
    bonf.append({"contract_id": cid, "name": name, "vendor": v["vendor"]["VendorContactOrganizationName"], "value": max(vals),
                 "spec": kv.get("Specification Number"), "term_start": start,
                 "url": f"https://chicagoparkdistrict.bonfirehub.com/portal/?tab=publicContracts (internalApi/publicContracts/{cid})",
                 "park_join": how, **parkinfo(pn)})

# ---------------------------------------------------------------- 5. Aldermanic menu lines for the Park District (2026)
menu = []
cur = None
for l in "\n".join(json.load(open(os.path.join(G, "menu_q2_2026.json")))).split("\n"):
    mw = re.match(r"Ward: (\d+)", l)
    if mw:
        cur = int(mw.group(1))
    m2 = re.match(r"Chicago Park District \(2026\)\s+(.*?)\s+\$([\d,]+\.\d\d)$", l)
    if m2:
        menu.append({"ward": cur, "location": m2.group(1), "amount": money(m2.group(2).replace(",", ""))})

# ---------------------------------------------------------------- 6. Stated project budgets (web + budget narrative)
FEAT = "https://www.chicagoparkdistrict.com/featured-capital-projects"
BUD = "2026 Budget Appropriations PDF pp69-72 (printed 63-66), https://files.chicagoparkdistrict.com/2025-12/2026%20Budget%20Appropriations.pdf"
featured = []


def feat(project, amount, basis, source, park_text=None, pn=None, status=None, funding=None):
    if pn is None and park_text:
        pn, how = resolve(park_text)
    featured.append({"project": project, "amount": amount, "basis": basis, "source": source, "status": status, "funding": funding, **parkinfo(pn)})


# completed, with stated total budget (historic, outside the 2026-2030 plan)
for proj, amt, ptxt, pn in [("ComEd Recreation Center, Addams Park (complete 2020)", 25_000_000, "Addams", None),
                            ("Ford Calumet Environmental Center, Big Marsh (complete 2021)", 7_800_000, None, 564),
                            ("Dr. Conrad Worrill Track and Field Center, Gately Park (complete 2020)", 56_000_000, "Gately", None),
                            ("The 606 Bloomingdale Trail Park (complete 2015)", 91_000_000, None, None),
                            ("Lakefront Trail Separation (complete 2018)", 16_000_000, None, None),
                            ("Chicago River Boat Houses (complete 2013-2016)", 24_000_000, None, None),
                            ("Maggie Daley Park (complete 2015)", 60_000_000, "Maggie Daley", None),
                            ("La Villita Park (complete 2014)", 19_000_000, "La Villita", None),
                            ("Brighton Park campus, new park and HQ, Park 596 (complete 2023)", 64_000_000, None, 596)]:
    feat(proj, amt, "stated project budget, completed", FEAT, ptxt, pn, "complete", None)
cgt = [("Abbott", "Track and Field - major renovation", 400), ("Austin Town Hall", "Gym Floor - replacement", 300),
       ("Carver Park", "Playground and Site Improvements - new", 250), ("Columbus Park", "Gym Floor - replacement", 300),
       ("Davis Square", "Water Playground - major rehab", 250), ("Foster", "Water Playground - major rehab", 250),
       ("Franklin", "Site Improvements - benches, picnic tables, baseball field rehab", 200),
       ("Grand Crossing", "Playground and Site Improvements - new", 250), ("Jackson", "Burnham Building - major renovation", 500),
       ("LaFollette Park", "Locker Room and Balcony Seat - renovations", 500), ("Lindblom Park", "Track - major renovation", 250),
       ("Kelly (Edward) Park", "Sports Fields Improvements", 200), ("Park No. 608- CDF", "Framework Plan", 500),
       ("Senka", "Site Improvements - paving, drainage, turf recarpet", 400),
       ("South Shore Cultural Center", "Interior Finishes and Exterior Pathway", 250), ("Washington", "Ballfield Improvements", 200)]
# Park numbers checked against the Chicago_Parks layer. 'Foster' could be Foster (J. Frank) 26 or Austin Foster 285; 26 chosen because the
# capital layer shows active work there. 'Jackson' = Jackson (Andrew) 19 because the Burnham Building is in Jackson Park. 'Washington' = 21.
CGT_PARK = {"Abbott": 259, "Austin Town Hall": 207, "Carver Park": 255, "Columbus Park": 209, "Davis Square": 14, "Foster": 26,
            "Franklin": 202, "Grand Crossing": 15, "Jackson": 19, "LaFollette Park": 201, "Lindblom Park": 243,
            "Kelly (Edward) Park": 260, "Park No. 608- CDF": 608, "Senka": 309, "South Shore Cultural Center": 429, "Washington": 21}
CGT_NAME = {"Abbott": "ABBOTT (ROBERT)", "Austin Town Hall": "AUSTIN TOWN HALL", "Carver Park": "CARVER (GEORGE WASHINGTON)", "Columbus Park": "COLUMBUS",
            "Davis Square": "DAVIS SQUARE", "Foster": "FOSTER (STEPHEN)", "Franklin": "FRANKLIN (JOHN HOPE)", "Grand Crossing": "GRAND CROSSING",
            "Jackson": "JACKSON (ANDREW)", "LaFollette Park": "LAFOLLETTE", "Lindblom Park": "LINDBLOM", "Kelly (Edward) Park": "KELLY (EDWARD)",
            "Senka": "SENKA", "South Shore Cultural Center": "SOUTH SHORE CULTURAL", "Washington": "WASHINGTON (GEORGE)"}
# resolve Chicago Grows Together parks by matching the capital-layer / park-layer names (hand-checked list printed in the report)
cgt_rows = []
for pk, proj, k in cgt:
    pn = CGT_PARK.get(pk)
    if pn is None:
        want = CGT_NAME.get(pk)
        cands = [n for n, ns in names.items() if any(want and norm(want).strip() == norm(x).strip() or (want and norm(x).strip().startswith(norm(want).strip())) for x in ns)]
        pn = cands[0] if len(cands) == 1 else None
    cgt_rows.append({"park_label": pk, "project": proj, "amount": k * 1000, "ambiguous_candidates": None if pn else [], **parkinfo(pn)})
featured.append({"project": "Chicago Grows Together (16 parks, TIF surplus)", "amount": sum(r["amount"] for r in cgt_rows),
                 "basis": "sum of 16 stated project investments", "source": FEAT, "status": "active", "funding": "TIF surplus", "park_no": None,
                 "items": cgt_rows})
feat("Stay Cool Together fieldhouse air conditioning pilot (2026)", 1_000_000, "stated 2026 investment", FEAT, None, None, "active", "TIF surplus")
feat("Cragin Park new fieldhouse", 7_600_000, "stated: $7.1M TIF plus $0.5M federal HUD grant", BUD, None, 131, "under construction", "TIF $7.1M + HUD $0.5M")
feat("Kells Park new fieldhouse", 18_500_000, "stated: $17M TIF plus $1.5M state grant", BUD, None, 1040, "final design, complete 2027", "TIF $17M + State $1.5M")
feat("Shoreline protection: Calumet Park, Montrose Beach, Oakwood Beach (3 projects)", 8_000_000, "stated as 'over $8 million' combined estimate (lower bound)", BUD, None, None, "final design, build 2026", None)
feat("Replacement of aged utility infrastructure (lead service lines, electrical), 2026", 6_000_000, "stated as 'nearly $6 million' (upper bound text)", BUD, None, None, "2026", None)
feat("Moran Park new fieldhouse (TIF IGA)", 9_000_000, "TIF IGA approved amount (see tif_iga_approvals)", BUD, "Moran", None, "planned", "TIF + State DCEO")

# ---------------------------------------------------------------- 7. Grants
grants = [
    {"source": "IDNR OSLAD announcement 2024-01-30", "recipient": "Chicago Park District", "amount": 700000, "project": "not named in list",
     "url": "https://capitolnewsillinois.com/wp-content/uploads/2024/04/OSLAD-LIST.pdf"},
    {"source": "IDNR OSLAD announcement 2024-12-16", "recipient": "Chicago Park District", "amount": 1000000, "project": "not named in list",
     "url": "https://www.illinois.gov/content/dam/soi/en/web/illinois/iisnewsattachments/30748-121624-dnr-oslad-grants-announced.pdf.pdf"},
    {"source": "IDNR OSLAD announcement 2026-01-09", "recipient": "Chicago Park District", "amount": 600000, "project": "Northerly Island park development (asterisk = economically distressed set-aside)",
     "url": "https://www.illinois.gov/content/dam/soi/en/web/illinois/iisnewsattachments/32088-011426-01092026-idnr-oslad-park-grants-awarded.pdf.pdf",
     **parkinfo(resolve("Northerly Island")[0])},
]
usa = json.load(open(os.path.join(RAW, "usa", "usa_cpd_awards.json")))
fed = []
for a in usa:
    if a["_kind"] == "contract":
        continue
    fed.append({"award_id": a["Award ID"], "amount": a["Award Amount"], "agency": a["Awarding Sub Agency"], "start": a.get("Start Date"),
                "description": (a["Description"] or "")[:200], "url": f"https://www.usaspending.gov/search/?hash=&q={a['Award ID']}"})
fed.sort(key=lambda z: -z["amount"])

# ---------------------------------------------------------------- 8. Attribution to the 2026-2030 CIP
cip = P["beyond_operating"]["capital"]["cip_2026_2030_category_level"]["rows"]
tif_26_30 = sum(r["total_2026_2030"] for r in tif_lines)
tif_by_year = {str(y): sum(r["by_year"][str(y)] for r in tif_lines) for y in range(2025, 2031)}
tif_join = [r for r in tif_lines if r["park_no"]]
menu_total = sum(m["amount"] for m in menu)
cgt_total = sum(r["amount"] for r in cgt_rows)

# named project entities: TIF CIP lines with money in 2026-2030
named_tif = [r for r in tif_lines if r["total_2026_2030"] > 0]


def bucket(vals):
    return {"n": len(vals), "under_1M": sum(1 for v in vals if v < 1e6), "from_1M_to_10M": sum(1 for v in vals if 1e6 <= v < 1e7),
            "10M_and_over": sum(1 for v in vals if v >= 1e7), "sum": sum(vals)}


tif_b = bucket([r["total_2026_2030"] for r in named_tif])
tif26 = [r for r in tif_lines if r["by_year"]["2026"] > 0]
tif26_b = bucket([r["by_year"]["2026"] for r in tif26])
iga_recent = [r for r in tif_iga if r["cdc_date"] >= "2021-01-01"]
iga_b = bucket([r["approved_tif"] for r in iga_recent])
iga_cost_b = bucket([r["total_project_cost"] or r["approved_tif"] for r in iga_recent])
award_vals = [(r["amount_in_title"] if r["kind"] == "change order" and r["amount_in_title"] else (r["implied_price_from_mwbe_schedule"] or r["amount_in_title"])) for r in board]
award_b = bucket([v for v in award_vals if v])
bf_b = bucket([r["value"] for r in bonf])

# park-level entity table: largest single stated figure per park among 2026-2030 TIF lines (sum of lines), IGA total cost (2021+),
# award price (2022+), featured budgets (active)
ent = collections.defaultdict(dict)
for r in named_tif:
    if r["park_no"]:
        ent[r["park_no"]]["tif_lines_2026_2030"] = ent[r["park_no"]].get("tif_lines_2026_2030", 0) + r["total_2026_2030"]
for r in iga_recent:
    if r["park_no"]:
        ent[r["park_no"]]["largest_tif_iga_project_cost_since_2021"] = max(ent[r["park_no"]].get("largest_tif_iga_project_cost_since_2021", 0), r["total_project_cost"] or r["approved_tif"])
for r, v in zip(board, award_vals):
    if r["park_no"] and v and r["date"] >= "2022":
        ent[r["park_no"]]["largest_board_award_since_2022"] = max(ent[r["park_no"]].get("largest_board_award_since_2022", 0), v)
park_entities = []
for pn, d in sorted(ent.items()):
    best = max(d.values())
    park_entities.append({**parkinfo(pn), **d, "largest_single_figure": best})
pe_b = bucket([e["largest_single_figure"] for e in park_entities])

# 2026 slice
y26_tif = tif_by_year["2026"]
# ---------------------------------------------------------------- 9. per-park index and coverage of the capital-map project list
by_park = collections.defaultdict(lambda: {"tif_cip_lines": [], "tif_iga": [], "board": [], "bonfire": [], "featured": []})
for r in tif_lines:
    if r["park_no"]:
        by_park[r["park_no"]]["tif_cip_lines"].append({"line": r["line"], "by_year": r["by_year"], "total_2026_2030": r["total_2026_2030"]})
for r in tif_iga:
    if r["park_no"]:
        by_park[r["park_no"]]["tif_iga"].append({"project": r["project"], "cdc_date": r["cdc_date"], "approved_tif": r["approved_tif"], "total_project_cost": r["total_project_cost"]})
for r, v in zip(board, award_vals):
    if r["park_no"]:
        by_park[r["park_no"]]["board"].append({"date": r["date"], "title": r["title"][:140], "kind": r["kind"], "amount": v, "amount_basis": "title" if (r["kind"] == "change order" and r["amount_in_title"]) or not r["implied_price_from_mwbe_schedule"] else "implied from MWBE schedule", "url": r["legistar_url"]})
for r in bonf:
    if r["park_no"]:
        by_park[r["park_no"]]["bonfire"].append({"name": r["name"], "vendor": r["vendor"], "value": r["value"]})
for f in featured:
    for it in (f.get("items") or [f]):
        if it.get("park_no"):
            by_park[it["park_no"]]["featured"].append({"project": it.get("project"), "amount": it["amount"], "status": f.get("status")})
for pn, d in by_park.items():
    d.update(parkinfo(pn))
    d["tif_2026_2030"] = sum(x["total_2026_2030"] for x in d["tif_cip_lines"])
    d["tif_2026"] = sum(x["by_year"]["2026"] for x in d["tif_cip_lines"])
    d["active_map_projects"] = sum(1 for c in CAP if c.get("PARK_NO") == pn and c["STATUS_1"] != "COMPLETE")

active = [c for c in CAP if c["STATUS_1"] != "COMPLETE"]
parks_with_tif = {pn for pn, d in by_park.items() if d["tif_cip_lines"] and d["tif_2026_2030"] > 0}
parks_with_any = set(by_park)
parks_recent = set(parks_with_tif)
parks_recent |= {r["park_no"] for r in tif_iga if r["park_no"] and r["cdc_date"] >= "2021-01-01"}
parks_recent |= {r["park_no"] for r in board if r["park_no"] and r["date"] >= "2022-01-01"}
parks_recent |= {r["park_no"] for r in bonf if r["park_no"] and (r["term_start"] or "") >= "2019-01-01"}
parks_recent |= {it["park_no"] for f in featured for it in (f.get("items") or [f]) if it.get("park_no") and f.get("status") in ("active", "under construction", "planned") or (it.get("park_no") and f.get("status", "").startswith("final") )}
coverage = {
    "capital_map_projects_total": len(CAP), "active_or_pending_projects": len(active),
    "active_projects_at_a_park_with_TIF_dollars_2026_2030": sum(1 for c in active if c.get("PARK_NO") in parks_with_tif),
    "active_projects_at_a_park_with_any_dollar_record_since_2021": sum(1 for c in active if c.get("PARK_NO") in parks_recent),
    "active_projects_at_a_park_with_any_dollar_record_any_year": sum(1 for c in active if c.get("PARK_NO") in parks_with_any),
    "parks_with_dollar_record_since_2021": len(parks_recent),
    "parks_with_TIF_dollars_2026_2030": len(parks_with_tif), "parks_with_any_dollar_record": len(parks_with_any),
    "note": "Dollars are tied to a park (and a named project), not to individual map rows. Map rows have no cost, and the map scope text rarely matches a funding line name.",
}
named_26 = {"tif_cip_lines_2026": y26_tif, "ordinance_capital_appropriation_2026": P["beyond_operating"]["capital"]["ordinance_capital_appropriations_2026_total"],
            "cip_district_money_2026": cip["Total Sources"]["y2026"]}

out = {
    "meta": {
        "entity": "Chicago Park District", "built_for": "FY2026 budget explorer", "no_estimates": True,
        "note": ("The District does not publish per-project dollars for its 2026-2030 CIP ($681.4M) or a project list with dollars on its capital map "
                 "(ArcGIS layer cap24_3 has no cost field). This file assembles the project-level dollars that ARE public: City TIF projections and agreements, "
                 "Board of Commissioners actions and MWBE bid schedules, Bonfire contract values, stated project budgets, OSLAD and federal awards."),
        "sources": {
            "capital_map_layer": "https://services7.arcgis.com/HpTF5nhGpVZolZvo/arcgis/rest/services/cap24_3/FeatureServer/0 (fields: Project_No, PARK_NAME, PARK_NO, Scope, Ward, Region_1, SUB_PROGRA, STATUS_1, YEAR_COMPL; no dollars)",
            "tif_projections": "https://data.cityofchicago.org/resource/fpsv-qjg3 (TIF Projections 2025-2034, published 2025-10-15)",
            "tif_agreements": "https://data.cityofchicago.org/resource/mex4-ppfc",
            "legistar_api": "https://webapi.legistar.com/v1/chicagoparkdistrict/matters ; https://chicagoparkdistrict.legistar.com",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/portal/?tab=publicContracts",
            "featured_projects_page": FEAT,
            "budget_pdf": "https://files.chicagoparkdistrict.com/2025-12/2026%20Budget%20Appropriations.pdf",
            "usaspending": "https://api.usaspending.gov/api/v2/search/spending_by_award/ (recipient 'CHICAGO PARK DISTRICT')",
            "oslad": "IDNR press releases listed under grants",
            "older_cips": "https://www.chicagoparkdistrict.com/capital-improvement-plan (2015-2019 to 2021-2025; category level only)",
        },
        "implied_price_rule": ("MWBE Schedule A lists each M/WBE subcontractor's dollars and percent of the contract. dollars / (percent/100) is the contract price the bidder used. "
                               "Median of agreeing pairs (within 4%), at least 2 pairs. Checks: Garfield Park children's garden schedule implies $9,169,249 vs Bonfire $8,581,000 + board change order $587,633 = $9,168,633; "
                               "Park 596 change-order schedule implies $68.4M vs Bonfire $64.5M + $4.0M change order = $68.5M. It is the bid, not an audited award."),
    },
    "cip_2026_2030_totals": {"total_sources": cip["Total Sources"], "by_source": {k: cip[k] for k in cip if k not in ("Total Sources", "Total Uses") and k not in ("Acquisition and Development", "Facility Rehabilitation", "Site Improvements", "Technology, Vehicles & Equipment")},
                             "by_use": {k: cip[k] for k in ("Acquisition and Development", "Facility Rehabilitation", "Site Improvements", "Technology, Vehicles & Equipment")}},
    "attribution": {
        "cip_total_2026_2030": cip["Total Sources"]["total_2026_2030"],
        "tif_cip_line_total_2026_2030": tif_26_30,
        "tif_cip_line_total_by_year": tif_by_year,
        "cip_tif_line": cip["Tax Increment Financing Funds"]["outside_funding_2026_2030"],
        "tif_share_of_cip_tif_line": tif_26_30 / cip["Tax Increment Financing Funds"]["outside_funding_2026_2030"],
        "tif_share_of_total_cip": tif_26_30 / cip["Total Sources"]["total_2026_2030"],
        "tif_lines_joined_to_park_number": {"lines": len(tif_join), "of": len(tif_lines), "dollars_2026_2030": sum(r["total_2026_2030"] for r in tif_join)},
        "named_state_federal_private_in_budget_narrative": {"Kells Park state grant": 1_500_000, "Cragin Park federal HUD": 500_000},
        "named_in_budget_narrative_total": 2_000_000,
        "aldermanic_menu_2026_park_district_lines": {"n": len(menu), "total": menu_total, "cip_city_grant_line": cip["City Grant Funds"]["outside_funding_2026_2030"]},
        "chicago_grows_together_total": cgt_total,
        "ordinance_capital_appropriation_2026": P["beyond_operating"]["capital"]["ordinance_capital_appropriations_2026_total"],
        "cip_district_money_2026": cip["Total Sources"]["y2026"],
        "go_bond_reimbursement_resolution_2026_max": 40_000_000,
    },
    "size_buckets": {
        "tif_cip_lines_2026_2030 (projects = TIF projection lines with money in 2026-2030)": tif_b,
        "tif_cip_lines_2026_only (amount in the 2026 column)": tif26_b,
        "tif_iga_approved_amount_cdc_since_2021": iga_b,
        "tif_iga_total_project_cost_cdc_since_2021": iga_cost_b,
        "board_awards_and_change_orders_2018_on": award_b,
        "bonfire_capital_contracts": bf_b,
        "park_level_largest_single_figure": pe_b,
    },
    "tif_cip_lines": sorted(tif_lines, key=lambda r: -r["total_2026_2030"]),
    "tif_iga_approvals": sorted(tif_iga, key=lambda r: r["cdc_date"], reverse=True),
    "board_awards": sorted(board, key=lambda r: r["date"], reverse=True),
    "bonfire_capital_contracts": sorted(bonf, key=lambda r: -r["value"]),
    "featured_project_budgets": featured,
    "aldermanic_menu_park_district_2026": menu,
    "grants_state_oslad": grants,
    "grants_federal_usaspending": fed,
    "coverage": coverage,
    "named_2026": named_26,
    "by_park": {str(k): v for k, v in sorted(by_park.items())},
    "park_entities": park_entities,
    "unmatched": {"tif_cip_lines": [r["line"] for r in tif_lines if not r["park_no"]],
                  "tif_iga": [r["project"] for r in tif_iga if not r["park_no"]],
                  "board": [r["title"][:100] for r in board if not r["park_no"]],
                  "bonfire": [r["name"] for r in bonf if not r["park_no"]]},
}
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps({k: out[k] for k in ("attribution", "size_buckets")}, indent=1, default=str))
print({k: len(v) for k, v in out["unmatched"].items()}, len(tif_lines), len(tif_iga), len(board), len(bonf))
