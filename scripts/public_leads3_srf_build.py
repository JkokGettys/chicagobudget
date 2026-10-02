"""Public leads 3, lead 2: Illinois EPA state revolving fund loans of the Water and Sewer funds. Writes
data/splits/city/iepa_loans.json (side info only, no new boxes: no per-loan 2026 payment is published).
Sources (held in raw/bonds/, not committed):
  Water: 2026ABC Official Statement p.34 (loan table, balances as of 2026-04-01, $457,541,223) and p.36 (2026 IEPA subordinate debt service $42,045,045).
    https://bondlink-cdn.com/1344/ILChicago04a-FIN.yO9Z1Tmxh.pdf
  Sewer: FY2025 Sewer Fund financial statements pp.41-42 (22 loans, balances 2025-12-31, $462,292K) and Wastewater 2024B Official Statement p.24 (2026 IEPA debt service $32,533,630).
    https://bondlink-cdn.com/1345/Sewer-Fund-Financial-Statements-2025.vcXRD2uoM.pdf , https://bondlink-cdn.com/1345/OS.5X3PYWIM0.pdf"""
import json, os, re, datetime as dt
ROOT = os.path.join(os.path.dirname(__file__), "..")
W_OS = {"doc": "Water 2026ABC Official Statement (City of Chicago, Dept of Water Management)", "url": "https://bondlink-cdn.com/1344/ILChicago04a-FIN.yO9Z1Tmxh.pdf", "page": "34 and 36"}
S_FS = {"doc": "City of Chicago Sewer Fund Financial Statements 2025, note 4", "url": "https://bondlink-cdn.com/1345/Sewer-Fund-Financial-Statements-2025.vcXRD2uoM.pdf", "page": "41-42"}
S_OS = {"doc": "Wastewater Transmission 2024B Official Statement", "url": "https://bondlink-cdn.com/1345/OS.5X3PYWIM0.pdf", "page": "24"}
txt = open(f"{ROOT}/raw/bonds/txt/water_2026ABC_OS.txt").read()
i = txt.find("SUBORDINATE LIEN OBLIGATIONS OUTSTANDING"); blk = txt[i:i + 3000]
wl = [(m.group(1), m.group(2), float(m.group(3)), int(m.group(4).replace(",", ""))) for m in re.finditer(r"(L17-\d+) (\d+/\d+/\d{4}) ([\d.]+) ([\d,]+)", blk)]
assert len(wl) == 24 and sum(x[3] for x in wl) == 457541223, (len(wl), sum(x[3] for x in wl))
st = open(f"{ROOT}/raw/bonds/txt/sewer_FS2025.txt").read().split("\n")[1070:1135]
st = " ".join(st)
sl = []
for m in re.finditer(r"\$?([\d,]+) Illinois Environmental Protection Agency Loan Agreement,?[ .]*signed ([A-Za-z]+ \d+,? ?\d{4}),? due through (\d{4}); (?:interest at ([\d.]+)%)[ .…]*\$?\s*([\d,]+)", st):
    sl.append((int(m.group(1).replace(",", "")) * 1000, m.group(2), int(m.group(3)), float(m.group(4)), int(m.group(5).replace(",", "")) * 1000))
assert len(sl) == 22 and sum(x[4] for x in sl) == 462292000, (len(sl), sum(x[4] for x in sl))

def usd(c): return f"${c:,.0f}"
w_items = [{"kind": "iepa_loan", "label": f"IEPA loan {a}: final maturity {b}, interest rate {c}%, principal still owed on 2026-04-01", "amount": d, "period": "2026-04-01", "basis": "gov_estimate", "source": W_OS} for a, b, c, d in wl]
s_items = [{"kind": "iepa_loan", "label": f"IEPA loan signed {b}: original amount {usd(a)} (rounded to thousands), due through {c}, interest rate {d}%, principal still owed on 2025-12-31", "amount": e, "period": "2025-12-31", "basis": "gov_estimate", "source": S_FS} for a, b, c, d, e in sl]
NOTE = ("The City's bond papers list every state (Illinois EPA) loan with its rate, last year and balance, but no paper prints each loan's payment for 2026, so the line is not split into loans. ")
splits = [
  {"target": {"by": "id", "id": "city.loans.water-fund.0200-2005-0944"}, "expect_amount": 39667255, "mode": "side_only",
   "note": NOTE + "The 2026 Water bond statement prints one number for all 24 state loans together: $42,045,045 of principal and interest in 2026. That is larger than this line because it includes interest, which is budgeted on the next line.",
   "side": [{"kind": "iepa_aggregate", "label": "All Water IEPA loans together: principal plus interest due in fiscal 2026 (Water 2026ABC OS p.36, 'Outstanding Subordinate Lien Obligations Debt Service')", "amount": 42045045, "period": "2026", "basis": "gov_estimate", "source": W_OS},
            {"kind": "iepa_aggregate", "label": "Total principal still owed on 24 fully drawn Water IEPA loans on 2026-04-01 (the City also signed $73.5M of further IEPA loans still being drawn)", "amount": 457541223, "period": "2026-04-01", "basis": "gov_estimate", "source": W_OS}] + w_items},
  {"target": {"by": "id", "id": "city.loans.water-fund.0200-2005-0943"}, "expect_amount": 14135049, "mode": "side_only",
   "note": NOTE + "Interest here also covers the federal WIFIA loan (4.38%, $141.3M drawn at the end of 2025) and the PNC credit line, not only state loans. See the principal line for the loan-by-loan table.",
   "side": [{"kind": "iepa_aggregate", "label": "All Water IEPA loans together: principal plus interest due in fiscal 2026 (Water 2026ABC OS p.36)", "amount": 42045045, "period": "2026", "basis": "gov_estimate", "source": W_OS}]},
  {"target": {"by": "id", "id": "city.loans.sewer-fund.0314-2005-0944"}, "expect_amount": 32626175, "mode": "side_only",
   "note": NOTE + "The 2024 Sewer bond statement prints one number for state loans in 2026: $32,533,630 of principal and interest, for loans closed by mid 2024. The two Sewer loan lines in the budget add to $44,361,561, which is more, probably because loans closed after mid 2024 (the City had signed $166.5M more) are not in that table. The audited 2025 statement lists 22 loans (below).",
   "side": [{"kind": "iepa_aggregate", "label": "All Sewer IEPA loans together (loans closed by 2024-07-01): principal plus interest due in fiscal 2026 (Wastewater 2024B OS p.24)", "amount": 32533630, "period": "2026", "basis": "gov_estimate", "source": S_OS},
            {"kind": "iepa_aggregate", "label": "Total principal still owed on 22 Sewer IEPA loans on 2025-12-31 (audited, thousands of dollars)", "amount": 462292000, "period": "2025-12-31", "basis": "gov_estimate", "source": S_FS}] + s_items},
  {"target": {"by": "id", "id": "city.loans.sewer-fund.0314-2005-0943"}, "expect_amount": 11735386, "mode": "side_only",
   "note": NOTE + "See the principal line for the loan-by-loan table. Interest rates run from 0% to 2.5%.",
   "side": [{"kind": "iepa_aggregate", "label": "All Sewer IEPA loans together: principal plus interest due in fiscal 2026 (Wastewater 2024B OS p.24)", "amount": 32533630, "period": "2026", "basis": "gov_estimate", "source": S_OS}]},
]
json.dump({"meta": {"author": "public leads 3 agent", "description": "Illinois EPA loan tables (rates, maturities, balances) and published 2026 totals as side info on Water and Sewer loan lines", "built_by": "scripts/public_leads3_srf_build.py"}, "splits": splits}, open(f"{ROOT}/data/splits/city/iepa_loans.json", "w"), indent=1)
print("wrote", len(splits), "water loans", len(wl), "sewer loans", len(sl))
