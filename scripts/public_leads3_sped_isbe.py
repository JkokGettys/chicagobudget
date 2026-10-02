"""Public leads 3, lead 4: match CPS FY2026 supplier payments to the ISBE directory of nonpublic special
education facilities (sheet 'Non Pub Spec Ed' of the 2025-26 Directory of Educational Entities,
https://www.isbe.net/Pages/Data-Analysis-Directories.aspx). Writes raw/pl3/sped_isbe_hits.json.
Inputs (not committed, in raw/): raw/pl3/cps_supplier_2026.json (api.cps.edu GetSupplierPayments?reportyear=2026)
and raw/pl3/isbe_dir_2526.xlsx (isbe.net Download.aspx?SourceUrl=/Documents/2025-26-Directory-Ed-Entities.xlsx)."""
import json, re, re as _re, collections, openpyxl, os
ROOT = os.path.join(os.path.dirname(__file__), "..")
sup = collections.defaultdict(float)
for x in json.load(open(f"{ROOT}/raw/pl3/cps_supplier_2026.json")):
    sup[x["Name"].strip()] += x["PaymentAmount"]
wb = openpyxl.load_workbook(f"{ROOT}/raw/pl3/isbe_dir_2526.xlsx", read_only=True)
ws = [w for w in wb.worksheets if w.title.startswith("6 ")][0]
rows = list(ws.iter_rows(values_only=True)); hdr = rows[0]
data = [dict(zip(hdr, r)) for r in rows[1:]]
STOP = r"\b(inc|llc|nfp|the|corp|corporation|dba|school|schools|of|and|center|centre|for|academy|services|service|ltd|co|company|foundation|education|educational|illinois|chicago)\b"
def norm(s):
    s = re.sub(STOP, " ", s.lower()); s = re.sub(r"[^a-z0-9 ]", " ", s); return " ".join(s.split())
facs = {}
for d in data:
    facs.setdefault(norm(d["FacilityName"] or ""), []).append(d)
hits = []
for name, v in sup.items():
    for p in [name] + re.split(r"\bdba\b|\bd/b/a\b", name, flags=re.I):
        n = norm(p)
        if len(n) >= 4 and n in facs:
            f = facs[n][0]; hits.append((v, name, f["FacilityName"], f["City"], f["RecType"])); break
hits.sort(reverse=True)
for h in hits: print(f"{h[0]:>13,.2f} {h[1][:70]:70} | {h[2]} | {h[3]} | {h[4]}")
print(len(hits), round(sum(h[0] for h in hits), 2), "sheet", ws.title, "rows", len(data), collections.Counter(d["RecType"] for d in data))
json.dump(hits, open(f"{ROOT}/raw/pl3/sped_isbe_hits.json", "w"))

# ---------------------------------------------------------------------------------------------
# Second stage: write data/splits/cps/sped_isbe.json (applied to the leftover box of the private tuition line).
ALREADY = ("MENTA", "EASTER SEALS", "SHANKMAN", "COVE SCHOOL", "ELIM CHRISTIAN", "NEW HORIZON", "REDWOOD", "SHRUB OAK", "ACACIA", "SOARING EAGLE", "LAWRENCE HALL")
# Multi-service agencies and hospitals: ISBE lists a school program, but CPS payments to them are probably mostly for other services.
MULTI = ("UCAN", "ESPERANZA", "JEWISH CHILD", "THRESHOLDS", "RUSH UNIVERSITY", "ORCHARD VILLAGE", "LITTLE CITY", "FAMILY GUIDANCE", "MARYVILLE", "ANIXTER")
# Wrong or doubtful: different organization (Discovery Education, Q & A Associates), or vendor city differs from the ISBE city.
DOUBT = ("DISCOVERY EDUCATION", "Q & A", "FUSION LEARNING", "NEURORESTORATIVE", "Hoosier Care", "ALEXANDER GRAHAM BELL")
sup_city = {}
for x in json.load(open(f"{ROOT}/raw/pl3/cps_supplier_2026.json")):
    sup_city[x["Name"].strip()] = (x["City"] or "", x["State"] or "")
keep = []; dropped = []
for v, name, fac, city, rt in hits:
    u = name.upper()
    why = None
    if any(a in u for a in ALREADY): why = "already a box"
    elif any(a.upper() in u for a in MULTI): why = "multi-service agency"
    elif any(a.upper() in u for a in DOUBT): why = "doubtful match"
    else:
        al = lambda t: _re.sub(r"[^a-z]", "", t.lower().replace("heights", "hts"))[:6]
        if al(sup_city[name][0]) != al(city or "") and "SPECIALIZED EDUCATION OF ILLINOIS" not in u: why = f"city differs ({sup_city[name][0]} vs {city})"
    (dropped if why else keep).append((v, name, fac, city, why))
print("\nKEEP", len(keep), round(sum(k[0] for k in keep), 2))
for k in keep: print(f"  {k[0]:>12,.2f} {k[1][:60]} | ISBE: {k[2]}, {k[3]}")
print("DROPPED", len(dropped))
for k in dropped: print(f"  {k[0]:>12,.2f} {k[1][:60]} | {k[4]}")

import re as _re
def nice(name, fac):
    base = _re.split(r"\bdba\b", name, flags=_re.I)
    n = name.title() if name.isupper() else name
    n = _re.sub(r"\s+", " ", n).strip()
    return n if len(n) <= 70 else fac
SRC_ISBE = {"doc": "CPS procurement API supplier payments FY2026, matched by name to the ISBE 2025-26 Directory of Educational Entities, sheet 'Non Pub Spec Ed'",
            "url": "https://www.isbe.net/Pages/Data-Analysis-Directories.aspx"}
pieces = []
for v, name, fac, city, _ in sorted(keep, reverse=True):
    pieces.append({"name": f"{nice(name, fac)}: paid so far", "amount": round(v, 2), "basis": "paid_to_date", "kind": "vendor_payment", "source": SRC_ISBE,
                   "note": f"Vendor total paid by CPS in FY2026 under the name '{name}'. It is listed as '{fac}' ({city}) in the State Board's directory of nonpublic special education schools. "
                           "The total can include other CPS contracts with the same organization, and CPS does not link payments to budget lines."})
split = {"meta": {"author": "public leads 3 agent", "description": "Private special education tuition: more providers from the ISBE nonpublic special education directory, taken out of the leftover box", "built_by": "scripts/public_leads3_sped_isbe.py"},
         "splits": [{"target": {"by": "id", "id": "cps.citywide.special-education.u11674.contracts.a54305.fg114-376711-p124904-0.not-spent-yet"},
                     "expect_amount": 26603160.16, "mode": "budget_split", "pieces": pieces,
                     "residual": {"name": "Tuition budgeted but not matched to a payment shown here",
                                  "why": "CPS pays many other private schools, and the payments file does not say which budget line each payment belongs to, so this part has no provider boxes."},
                     "note": f"{len(pieces)} more private schools were found by matching CPS FY2026 payment names to the State Board of Education's directory of approved nonpublic special education schools (together ${sum(p['amount'] for p in pieces):,.2f}). Left out on purpose: agencies that run many services (UCAN, JCFS, Maryville, Rush and others), and names that did not match the same city."}]}
os.makedirs(f"{ROOT}/data/splits/cps", exist_ok=True)
json.dump(split, open(f"{ROOT}/data/splits/cps/sped_isbe.json", "w"), indent=1)
print("wrote", len(pieces), "pieces")
