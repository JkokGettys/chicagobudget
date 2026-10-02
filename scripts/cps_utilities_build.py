"""Launch fix 3: names the utility companies on the four big CPS utility lines.
Reads data/cps_supplier_payments_fy{2024,2025,2026}_over1m.csv (CPS procurement API, vendors paid $1M or more)
and data/cps_contract_awards_fy21_27.csv (Board Report numbers). Writes data/splits/cps/utilities.json.
Run from the repo root: python3 scripts/cps_utilities_build.py"""
import csv, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U = "cps.citywide.facilities.u11880.supplies."

def pay(year):
    out = {}
    with open(os.path.join(ROOT, "data", f"cps_supplier_payments_fy{year}_over1m.csv")) as f:
        for r in csv.DictReader(f):
            out[r["vendor"]] = float(r["payment_amount"])
    return out
P = {y: pay(y) for y in (2024, 2025, 2026)}

# line id suffix -> (expected amount, vendor key in the CSV, kid name, kind of bill, contract evidence, why, line note)
SRC = {"doc": "CPS procurement API, supplier payments FY2026 (vendors paid $1M or more; vendor totals, not tied to budget lines)",
       "url": "https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2026",
       "file": "data/cps_supplier_payments_fy2026_over1m.csv"}
AWARDS = {r["board_report"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data", "cps_contract_awards_fy21_27.csv")))}
def award(br):
    r = AWARDS[br]
    return (f"Board Report {br}: {r['project_name'].capitalize()}, up to ${float(r['authorized_amount']):,.0f}, "
            f"{r['start']} to {r['end']}")

LINES = [
 ("a53105", 43882579.0, "CONSTELLATION NEWENERGY, INC", "Constellation NewEnergy (electricity supplier)",
  "buying the electricity itself", "22-1207-PR7",
  "electricity supply (Constellation sells CPS the power). Delivery over the wires is the separate 'Electricity delivery' line."),
 ("a53115", 42227643.0, "COMMONWEALTH EDISON COMPANY  1", "Commonwealth Edison, called ComEd (electricity delivery company)",
  "delivering electricity over the wires", None,
  "electricity delivery (ComEd owns the wires). We match ComEd here because it is the local delivery company, not because a CPS document says so."),
 ("a53120", 18116321.0, "PEOPLES GAS", "Peoples Gas (gas delivery company)",
  "delivering natural gas through the pipes", None,
  "natural gas delivery (Peoples Gas owns the pipes). We match Peoples Gas here because it is the local delivery company, not because a CPS document says so."),
 ("a53125", 14863679.0, "CONSTELLATION NEWENERGY - GAS DIVISION, LLC", "Constellation NewEnergy Gas Division (natural gas supplier)",
  "buying the natural gas itself", "25-0828-PR3",
  "natural gas supply (Constellation sells CPS the gas). Delivery through the pipes is the separate 'Natural gas delivery' line."),
]

splits = []
for acct, line, vendor, kid, what, br, how in LINES:
    amt = P[2026][vendor]
    prior = [f"FY{y}: ${P[y][vendor]:,.2f}" for y in (2025, 2024) if vendor in P[y]]
    note_parts = [
        f"Plain words: CPS pays {kid.split(' (')[0]} for {what}. The box shows what CPS paid that company in fiscal year 2026 "
        f"(July 2025 to June 2026): ${amt:,.2f}. CPS publishes payments by company, not by budget line, so this is our match to the "
        f"{how} The company total can include other CPS accounts, and companies paid under $1M are not in the file, so the rest of the line is shown as not matched."]
    side = [{"kind": "vendor_payment", "label": f"{kid.split(' (')[0]}: paid FY2026, whole vendor total ${amt:,.2f}",
             "amount": amt, "period": "FY2026", "basis": "paid_to_date", "source": SRC}]
    if prior:
        side.append({"kind": "vendor_payment_prior_years",
                     "label": f"{kid.split(' (')[0]}: earlier years paid by CPS (vendor totals), " + "; ".join(prior),
                     "amount": P[2025].get(vendor), "period": "FY2025", "basis": "paid_to_date",
                     "source": {"doc": "CPS procurement API, supplier payments FY2024 and FY2025 (vendors paid $1M or more)",
                                "file": "data/cps_supplier_payments_fy2025_over1m.csv, data/cps_supplier_payments_fy2024_over1m.csv"}})
    if br:
        side.append({"kind": "contract_authority", "label": award(br), "amount": float(AWARDS[br]["authorized_amount"]),
                     "period": "contract term", "basis": "gov_estimate",
                     "source": {"doc": f"CPS Board Report {br}", "file": "data/cps_contract_awards_fy21_27.csv"}})
    splits.append({
        "target": {"by": "id", "id": U + acct}, "expect_amount": line, "mode": "paid_to_date",
        "pieces": [{"name": f"{kid}: paid in FY2026", "amount": amt, "basis": "paid_to_date", "source": SRC,
                    "note": "Vendor total paid by CPS in FY2026 under the supplier name '" + vendor.replace("  1", "") + "'. Not tied to a budget line by CPS.",
                    "why": (f"This is what CPS paid one utility company for {what} in a year. The payments are made as the bills come in, and CPS does not publish them bill by bill.")}],
        "residual": {"name": "Budgeted but not matched to a payment of $1M or more shown here",
                     "why": "Smaller payments to other companies, bills paid from other accounts, or budget that was not spent. CPS's file only lists companies paid $1M or more."},
        "over": {"name": "Paid more than this budget line (payments from other accounts)"},
        "note": " ".join(note_parts), "side": side})

out = {"meta": {"author": "launch fix 3", "built_by": "scripts/cps_utilities_build.py",
                "description": "Names the utility companies on the four large CPS utility lines (paid FY2026, vendor totals)"},
       "splits": splits}
path = os.path.join(ROOT, "data", "splits", "cps", "utilities.json")
json.dump(out, open(path, "w"), indent=1)
print(path)
for s in splits:
    p = s["pieces"][0]
    print(f"  {s['target']['id'][-6:]} line {s['expect_amount']:>13,.2f}  {p['name'][:60]:60} {p['amount']:>13,.2f}  rest {s['expect_amount']-p['amount']:>12,.2f}")
