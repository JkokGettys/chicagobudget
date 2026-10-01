#!/usr/bin/env python3
"""Round 3, item 2e: CPS budget-only reserves, special education transportation, Public Building Commission O&M.
Sources already local and verified: data/cps_ctpf_valuation_2025.csv (CTPF valuation 6/30/2025 p.1 and Table 11 p.44), raw/pensions_debt/funds/MEABF_val_2025.txt,
data/cps_supplier_payments_fy2026_over1m.csv (CPS procurement API, FY26), raw/leaves/cps_acfr_fy25.txt Note 11, raw/cps/bb26.pdf.txt (budget book, transportation and facilities pages),
data/cps_contract_awards_fy21_27.csv (JLL Board Reports 26-0319-PR5, 26-0226-PR3). Writes data/leaves_cps.json.
Proxy allocations are labelled. No number here is invented: each is read from the file named in its source field."""
import csv, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pay = {r["vendor"]: float(r["payment_amount"]) for r in csv.DictReader(open(f"{ROOT}/data/cps_supplier_payments_fy2026_over1m.csv"))}
hcsc = pay["HEALTH CARE SERVICE CORPORATION (HCSC), A MUTUAL LEGAL RESERVE COMPANY"]; cvs = pay["CVS Pharmacy Inc DBA CAREMARKPCS HEALTH LLC"]
dental = pay["DELTA DENTAL OF ILLINOIS"]; std = pay["STANDARD INSURANCE COMPANY"]
leaves = []
# ---- CTPF levy: count x average over benefit types (valuation 6/30/2025 Table 11 p.44), allocated by benefit-dollar share
ben = [("Retirees", 23350, 64860, 1_514_469_736), ("Disabled retirees", 408, 47128, 19_228_116), ("Beneficiaries", 3399, 29749, 101_118_302)]
tot = sum(b[3] for b in ben); levy = 602_309_665
leaves.append({"match_path_contains": ["CTPF Pension Levy", "A58115"], "amount": 602_309_665, "proposed_status": "split_proxy",
  "split_basis": "PROXY. The Board levy (budget book p.35) is a contribution, not a benefit payment. Shown as the CTPF benefit types it helps pay (count x average, valuation 6/30/2025 Table 11 p.44), each allocated levy x share of annual benefit dollars. Statutory components of FY2026 required employer contributions (valuation p.1): Board required $646,234,000, additional Board $17,332,000, additional State $16,256,000, State normal cost $346,838,000, total $1,026,660,000. Employer normal cost incl. admin $278,649,630 of total normal cost $538,756,738.",
  "pieces": [{"name": f"{n}: {c:,} x ${a:,}", "count": c, "average": a, "annual_benefits": b, "contribution_share_proxy": round(levy * b / tot), "basis": "count_x_average", "source": "data/cps_ctpf_valuation_2025.csv (Table 11 p.44)"} for n, c, a, b in ben],
  "pieces_over_10m_after": [], "why_cant_go_deeper": "The school board sends one pension payment set by state law, and the teachers' pension fund then pays more than 27,000 retired teachers and families."})
# ---- ESP pension (MEABF): same device with MEABF Section 2/3 counts
leaves.append({"match_path_contains": ["A58275"], "amount": 202_791_171.06, "proposed_status": "split_proxy",
  "split_basis": "PROXY. MEABF valuation 12/31/2025: 21,874 retired members x $4,092 a month, 3,714 surviving spouses x $1,628, 119 reversionary x $411, 64 children (derived remainder); total annual benefits $1,147,424,016 (all City and CPS members). CPS employees are about 64% of active members and drive about 49% of the statutory contribution (Forecast 2027 p.22, via data/pensions_2026.json meabf_cps_share). The budget line is a reserve ($202.8M) and the budget book also says a $175M reimbursement to the City is contingent on new revenue (bb26 p.15).",
  "pieces": [{"name": "Retired members: 21,874 x $49,104", "count": 21874, "average": 49104, "basis": "count_x_average", "source": "raw/pensions_debt/funds/MEABF_val_2025.txt"}, {"name": "Surviving spouses: 3,714 x $19,536", "count": 3714, "average": 19536, "basis": "count_x_average", "source": "same"}],
  "pieces_over_10m_after": [], "why_cant_go_deeper": "This is money set aside in case the school district has to repay the City for the pensions of non-teacher staff, and nobody has decided yet if it will be paid."})
# ---- hospitalization: vendor shares of FY26 payments (HCSC medical, Caremark pharmacy, dental, life)
tot_h = hcsc + cvs + dental + std; L = 161_666_402.4
leaves.append({"match_path_contains": ["A58195"], "amount": 161_666_402.4, "proposed_status": "split_partial",
  "split_basis": f"PROXY by plan. FY26 CPS supplier payments: HCSC (medical) ${hcsc/1e6:.1f}M, CVS Caremark (prescription) ${cvs/1e6:.1f}M, Delta Dental ${dental/1e6:.1f}M, Standard Insurance (life/disability) ${std/1e6:.1f}M. The reserve is allocated by those shares (labelled proxy). FY25 ACFR Note 11: self-insured medical claims paid $703.1M, claims reserve $116.3M. Covered lives are not published.",
  "pieces": [{"name": n, "amount": round(L * v / tot_h), "basis": "proxy", "source": "data/cps_supplier_payments_fy2026_over1m.csv"} for n, v in (("Medical (HCSC) share", hcsc), ("Prescription (Caremark) share", cvs), ("Dental share", dental), ("Life and disability share", std))],
  "pieces_over_10m_after": [{"name": "Medical (HCSC) share of reserve, proxy", "amount": round(L * hcsc / tot_h)}, {"name": "Prescription (Caremark) share of reserve, proxy", "amount": round(L * cvs / tot_h)}],
  "why_cant_go_deeper": "CPS pays most health bills as they come in, so this reserve is a guess at bills that have not arrived yet, and the insurers do not publish who each claim was for."})
# ---- special ed transportation: routes and students (bb26 p.? lines 8877-8889): 1,200 routes, 14,000 students with IEPs, 20 vendors
T0 = 146_700_000
leaves.append({"match_path_contains": ["A54210"], "amount": 146_700_000, "proposed_status": "split_proxy",
  "split_basis": f"PROXY count x average from the budget book: about 1,200 routes for students with disabilities run by 20 vendors, more than 14,000 students (bb26 Student Transportation Services). ${T0/1e6:.1f}M / 1,200 routes = ${T0/1200:,.0f} per route, or ${T0/14000:,.0f} per student. The three largest bus companies are named in cps_deep.md from FY26 supplier payments (Illinois Central $29.1M, Sunrise $26.2M, Alltown $22.3M). Those are district-wide totals and may include general education routes.",
  "pieces": [{"name": "about 1,200 routes x about $122K", "count": 1200, "average": round(T0 / 1200), "basis": "count_x_average", "source": "raw/cps/bb26.pdf.txt Student Transportation Services"}, {"name": "about 14,000 students x about $10.5K", "count": 14000, "average": round(T0 / 14000), "basis": "count_x_average", "source": "same"}],
  "pieces_over_10m_after": [], "why_cant_go_deeper": "CPS pays bus companies by contract, so the public can see how many routes and students there are but not what each route cost."})
# ---- Public Building Commission O&M: JLL contract, 803 buildings
jll_paid = pay["JONES LANG LASALLE AMERICAS, INC."]
leaves.append({"match_path_contains": ["Public Building Commission O & M", "A54105"], "amount": 146_634_377, "proposed_status": "split_proxy",
  "split_basis": f"PROXY. Facility management is one contract with Jones Lang LaSalle: FY26 payments ${jll_paid/1e6:.1f}M (CPS procurement API), Board Report 26-0319-PR5 authorizes ${328_870_000/1e6:.2f}M for 7/1/2026 to 6/30/2028 and 26-0226-PR3 authorized ${299_566_000/1e6:.2f}M for the prior term. The budget book says the portfolio is 522 campuses and 803 buildings. $146,634,377 / 803 buildings = about $183K per building (equal share, not a real per-building cost).",
  "pieces": [{"name": "803 buildings x about $183K", "count": 803, "average": round(146_634_377 / 803), "basis": "count_x_average", "source": "raw/cps/bb26.pdf.txt p.? portfolio sentence; data/cps_contract_awards_fy21_27.csv"}],
  "pieces_over_10m_after": [], "why_cant_go_deeper": "One company runs the repairs and building engineering for all school buildings under one contract, and CPS does not publish what each building cost."})
meta = {"generated_by": "scripts/leaves_cps.py", "sources_fetched": [
  {"url": "local: data/cps_ctpf_valuation_2025.csv (https://www.ctpf.org/sites/files/2025-10/CTPF_FundingVal_2025_Final.pdf)", "http_status": "200 at round 2", "note": "valuation numbers"},
  {"url": "local: raw/pensions_debt/funds/MEABF_val_2025.txt", "http_status": "200 at round 2", "note": "member counts and average monthly benefits"},
  {"url": "local: raw/cps/bb26.pdf.txt (CPS FY2026 budget book)", "http_status": "200 at round 1", "note": "routes, students, 803 buildings, MEABF $175M contingent reimbursement"},
  {"url": "local: data/cps_supplier_payments_fy2026_over1m.csv (https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2026)", "http_status": "200 at round 2", "note": "vendor totals only, no budget line"}],
  "not_found": "Contingency lines (A57915 $120M, $100M, $52.9M): no Board Report names a purchase from them, so they stay unsplit. Preschool for All A54125 $88.1M: provider awards not found. Budget-only A58115 reserve $120.6M: no source beyond CTPF totals."}
json.dump({"meta": meta, "leaves": leaves}, open(f"{ROOT}/data/leaves_cps.json", "w"), indent=1)
print(len(leaves), hcsc, cvs)
