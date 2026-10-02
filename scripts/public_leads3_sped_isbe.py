"""Public leads 3, lead 4: match CPS FY2026 supplier payments to the ISBE directory of nonpublic special
education facilities (sheet 'Non Pub Spec Ed' of the 2025-26 Directory of Educational Entities,
https://www.isbe.net/Pages/Data-Analysis-Directories.aspx). Writes raw/pl3/sped_isbe_hits.json.
Inputs (not committed, in raw/): raw/pl3/cps_supplier_2026.json (api.cps.edu GetSupplierPayments?reportyear=2026)
and raw/pl3/isbe_dir_2526.xlsx (isbe.net Download.aspx?SourceUrl=/Documents/2025-26-Directory-Ed-Entities.xlsx)."""
import json, re, collections, openpyxl, os
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
