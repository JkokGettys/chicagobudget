#!/usr/bin/env python3
"""Build data/splits/city/bond_series_round3.json: more series out of the "Other bonds (not printed one by one)" boxes,
using ONLY City statements already on the BondLink pages (raw/bonds). No EMMA data is used.

Run:  python3 scripts/bond_series_round3_build.py     (then build/build_all.sh; every split must show applied, 0 skipped)

What it splits (research/emma_bonds.md has the method, checks and what could NOT be done):
  GO interest   $111,605,596 -> ten Tax Levy series, interest = balance x stated coupon (term bonds or all one coupon,
                no principal due before 2030, so the 2026 window interest is exact). Labelled proxy (our arithmetic).
  Water interest $11,951,198  -> 2004 ($3,219,000) and 2016A-1 ($2,059,800), as scheduled before the May 2026 refunding.
  Water principal $44,585,000 -> 2004 ($31,035,000) and 2016A-1 ($6,295,000), same basis.
  Midway $13,312,661         -> 2014B, 2014C, 2018A from the airport consultant's printed per-series table (OS p.169).
Every amount is checked below against the source text in raw/bonds/txt before it is written.
"""
import json
import os
import re
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TXT = os.path.join(ROOT, "raw", "bonds", "txt")
OUT = os.path.join(ROOT, "data", "splits", "city", "bond_series_round3.json")
CDN = "https://bondlink-cdn.com/"


def txt(prefix):
    for f in sorted(os.listdir(TXT)):
        if f.startswith(prefix):
            return open(os.path.join(TXT, f)).read()
    raise SystemExit("missing text for " + prefix)


def must(text, needle, what):
    if needle not in text:
        raise SystemExit(f"CHECK FAILED ({what}): {needle!r} not found")


def dollars(x):
    return int(Decimal(x).quantize(Decimal(1), rounding=ROUND_HALF_UP))


WHY_BOND = "This is one bond's yearly payment to the people who lent the money, and it is already as small as the bond itself."

# ------------------------------------------------------------------ source text for checks
go26 = txt("go_2026AB_OS")
acfr = txt("acfr_fy2025")
os2009 = txt("GO_2009_A-D_OS")
os2010b = txt("GO_2010B_OS")
os2010c1 = txt("GO_2010C-1_OS")
os2011 = txt("GO_2011A&B_OS")
os2012 = txt("GO_2012A-C_OS")
os2014 = txt("GO_2014A&B_OS")
os2015c = txt("GO_2015C_OS")
os2020 = txt("GO_2020A_OS")
w2026 = txt("water_2026ABC_OS")
w2016 = txt("Water_2016A-1_and_A-2")
mid = txt("midway_2025AB_OS")

# ------------------------------------------------------------------ GO interest
GO_DOC = {"doc": "City of Chicago GO bond statements (BondLink)", "url": "https://www.cityofchicagoinvestors.com/generalobligationbonds/documents/downloads/i1398"}
# (key, name, balance, coupon %, balance table line in go_2026AB_OS Table 3, own-statement cite, sinking-fund-first-year, official name)
GO = [
    ("2009B", "GO Taxable Project and Refunding Series 2009B", 127_150_000, "6.207", "Taxable Project and Refunding Series 2009B 127,150,000",
     "GO_2009_A-D_OS.t1979RQA73.pdf p.2 (6.207% term bond due 1/1/2032) and p.15 (first sinking fund installment 2030)", 2030),
    ("2009C", "GO Taxable Project Series 2009C (Build America Bonds)", 55_435_000, "6.207", "Taxable Project Series 2009C (Build America Bonds - Direct Payment) 55,435,000",
     "GO_2009_A-D_OS.t1979RQA73.pdf p.2 (6.207% term bond due 1/1/2036) and p.16 (first sinking fund installment 2032)", 2032),
    ("2009D", "GO Taxable Project Series 2009D (Recovery Zone Bonds)", 133_180_000, "6.257", "Taxable Project Series 2009D (Recovery Zone Economic Development - Direct Payment) 133,180,000",
     "GO_2009_A-D_OS.t1979RQA73.pdf p.2 (6.257% term bond due 1/1/2040) and p.16 (first sinking fund installment 2036)", 2036),
    ("2010B", "GO Taxable Project Series 2010B (Build America Bonds)", 213_555_000, "7.517", "Taxable Project Series 2010B (Build America Bonds - Direct Payment) 213,555,000",
     "GO_2010B_OS.OYfAEh411h.pdf p.1 (7.517% term bond due 1/1/2040), p.25 (first sinking fund installment 2036) and p.65 (the statement itself prints $16,052,929 of interest every year)", 2036),
    ("2010C1", "GO Taxable Project Series 2010C-1", 125_275_000, "7.781", "Taxable Project Series 2010C-1 125,275,000",
     "GO_2010C-1_OS.YUmIUrNL6B.pdf p.1 (7.781% term bond due 1/1/2035) and p.24 (first sinking fund installment 2031)", 2031),
    ("2011B", "GO Taxable Project Series 2011B", 141_875_000, "6.034", "Taxable Project Series 2011B 141,875,000",
     "GO_2011A&B_OS.sIACMKzFVe.pdf p.2 (6.034% term bond due 1/1/2042) and p.17 (first sinking fund installment 2041)", 2041),
    ("2012B", "GO Taxable Project and Refunding Series 2012B", 151_300_000, "5.432", "Taxable Project and Refunding Series 2012B 151,300,000",
     "GO_2012A-C_OS.rbfTOIypRd.pdf p.2 (5.432% term bond due 1/1/2042) and p.17 (first sinking fund installment 2039)", 2039),
    ("2014B", "GO Taxable Project and Refunding Series 2014B", 195_735_000, "6.314", "Taxable Project and Refunding Series 2014B 195,735,000",
     "GO_2014A&B_OS.tRtjeGigSX.pdf p.4 (6.314% term bond due 1/1/2044) and p.33 (first sinking fund installment 2037)", 2037),
    ("2015C", "GO Refunding Series 2015C", 40_015_000, "5.000", "Refunding Series 2015C 40,015,000",
     "GO_2015C_OS.zT7gfsJPNw.pdf p.2 (every maturity and both term bonds are 5.000%)", None),
    ("2020A1", "GO Refunding Series 2020A-1", 283_090_000, "5.000", "Refunding Series 2020A 283,090,000",
     "GO_2020A_OS.0CmwMzPx.pdf p.2 (the 2020A maturities after 2026 are all 5.00%; the ACFR lists 2020 A-1 as 5.0%)", None),
]
# checks: balances in Table 3 of the 2026AB OS, coupons in ACFR Table 25
for key, name, bal, rate, t3, cite, sink in GO:
    must(go26, t3, f"GO {key} balance in 2026AB OS Table 3")
must(acfr, "Project Series 2010 B - 7.517%", "ACFR coupon 2010B")
must(acfr, "Project Series 2010 C-1 - 7.781%", "ACFR coupon 2010C-1")
must(acfr, "Project Series 2011 B - 6.034%", "ACFR coupon 2011B")
must(acfr, "Project Series 2012 B - 5.432%", "ACFR coupon 2012B")
must(acfr, "Project and Refunding Series 2014 B - 6.314%", "ACFR coupon 2014B")
must(acfr, "Refunding Series 2015 C - 5.0%", "ACFR coupon 2015C")
must(acfr, "Refunding Series 2020 A-1 - 5.0%", "ACFR coupon 2020A-1")
must(acfr, "Project and Refunding Series 2009 B through D - 6.207% to 6.257%", "ACFR coupon 2009B-D")
must(acfr, "315,765", "ACFR 2009B-D balance")
assert 127_150_000 + 55_435_000 + 133_180_000 == 315_765_000
must(os2010b, "16,052,929", "2010B own statement prints the annual interest")
must(os2009, "6.207% Term Bonds due January 1, 2032", "2009B cover")
must(os2009, "6.257% Term Bonds due January 1, 2040", "2009D cover")
must(os2010b, "7.517% Term Bonds due January 1, 2040", "2010B cover")
must(os2010c1, "7.781% Term Bonds due January 1, 2035", "2010C-1 cover")
must(os2011, "6.034% Term Bonds due January 1, 2042", "2011B cover")
must(os2012, "5.432% Term Bonds due January 1, 2042", "2012B cover")
must(os2014, "6.314% Term Bonds due January 1, 2044", "2014B cover")
assert dollars(Decimal(213_555_000) * Decimal("0.07517")) == 16_052_929  # the statement's own printed figure
GO_LINE_ID = "city.loans.bond-redemption-and-interest-series-fund.0510-2005-0902.other-not-itemised"
GO_LINE_AMT = 111_605_596

go_pieces, go_total = [], 0
for key, name, bal, rate, t3, cite, sink in GO:
    interest = dollars(Decimal(bal) * Decimal(rate) / 100)
    go_total += interest
    reason = (f"No principal falls due in the 2026 window (first sinking fund installment {sink}), so the year's interest is exactly the balance times the coupon."
              if sink else
              "Every maturity of this series carries the same 5% coupon, so the year's interest is the balance times 5% whichever maturities remain.")
    go_pieces.append({
        "key": f"go-{key.lower()}-interest", "name": name, "amount": interest, "basis": "proxy", "kind": "bond_series",
        "why": WHY_BOND if interest >= 10_000_000 else None,
        "note": (f"Derived, not printed: outstanding principal ${bal:,} x {rate}% = ${interest:,} (rounded to the dollar), interest for the payments Jul 1 2026 and Jan 1 2027. "
                 f"{reason} Gross of any federal subsidy. Balance: 2026AB OS Table 3 (BondLink PDF p.24), which equals the ACFR Table 25 balance at 12/31/2025. Coupon and terms: {cite}."),
        "source": {"doc": "City of Chicago GO 2026AB official statement Table 3 (balance) and the series' own statement (coupon)",
                   "url": CDN + "1338/ILChicago02a-FIN.D8Ebm0ZNE.pdf", "page": "24 (balance)", "cite": cite,
                   "acfr": "FY2025 ACFR Table 25, PDF p.252", "acfr_url": CDN + "1338/FY2025-ACFR---City-of-Chicago.0TRW97g9Y.pdf"},
        "extra": {"balance_dollars": bal, "coupon_percent": rate, "status": "derived_balance_x_coupon"},
    })
assert go_total < GO_LINE_AMT, (go_total, GO_LINE_AMT)

# ------------------------------------------------------------------ Water (fiscal 2026 payments on May 1 and Nov 1)
# 2016 statement, PDF p.29: the "Series 2000 and 2004 Bonds" column row 2026 = 39,254,000 and "2016A-1 Bonds" row 2026 = 8,354,800.
must(w2016, "2026 138,586,987 39,254,000 8,354,800 186,195,787", "2016 OS table row 2026")
must(w2016, "2027 137,861,854 40,012,250 8,353,000 186,227,104", "2016 OS table row 2027")
must(w2026, "2004 2027 64,380,000 33,345,000 31,035,000", "2026 OS p.33 2004 balances")
must(w2026, "2016A-1 2031 42,455,000 36,160,000 6,295,000", "2026 OS p.33 2016A-1 balances")
must(w2016, "2026 6,295,000 4.00% 110.700% 2.81% 167736 G35", "2016A-1 2026 maturity on cover")
# 2004: 64,380,000 outstanding before the 2026 transaction, all 5%. The 2027 maturity is 32,700,000 refunded + 645,000 tendered
# = 33,345,000 (Appendix I p.169-170). Remainder 31,035,000 matures Nov 1 2026. Identity with the 2016 table:
p2004 = 64_380_000 - (32_700_000 + 645_000)
i2004 = dollars(Decimal(64_380_000) * Decimal("0.05"))
assert p2004 == 31_035_000 and i2004 == 3_219_000
assert 5_000_000 + p2004 + i2004 == 39_254_000                  # row 2026 of the 2016 table (2000 interest 5,000,000 + 2004)
assert 5_000_000 + (32_700_000 + 645_000) + dollars(Decimal(33_345_000) * Decimal("0.05")) == 40_012_250  # row 2027
# 2016A-1: balance 42,455,000 (before) with 2027 to 2031 maturities refunded or tendered, the 2026 maturity 6,295,000 stays.
bal1 = [(6_295_000, "0.04"), (6_545_000, "0.05"), (6_870_000, "0.05"), (7_215_000, "0.05"), (7_575_000, "0.05"), (7_955_000, "0.05")]
assert sum(b for b, _ in bal1) == 42_455_000
i2016 = sum(dollars(Decimal(b) * Decimal(r)) for b, r in bal1)
assert i2016 == 2_059_800 and 6_295_000 + i2016 == 8_354_800   # equals the printed 2016A-1 column row 2026
W_P_ID = "city.loans.water-fund.0200-2005-0912.other-not-itemised"
W_I_ID = "city.loans.water-fund.0200-2005-0902.other-not-itemised"
W_P_AMT, W_I_AMT = 44_585_000, 11_951_198
W_SRC = {"doc": "Water 2016A-1 official statement (debt service table, PDF p.29) and Water 2026ABC official statement (PDF p.33 balances, p.169 Appendix I)",
         "url": CDN + "1344/Water_2016A-1_and_A-2__2nd_Lien_OS.3J2RMdP4p6.pdf", "url2": CDN + "1344/ILChicago04a-FIN.yO9Z1Tmxh.pdf"}
W_NOTE = ("As scheduled BEFORE the 2026 refunding: the November 2026 refunding and May 2026 tender remove the 2027 and later maturities of this series from the 2026 official "
          "statement's totals, but the bonds still pay interest until they are redeemed on 11/1/2026 (paid from the refunding escrow). The 2025 budget ordinance was written before that deal.")
w_p = [
    {"key": "water-2004-principal", "name": "Water Refunding Series 2004 (principal due Nov 1 2026)", "amount": p2004, "basis": "proxy", "kind": "bond_series",
     "why": WHY_BOND, "source": W_SRC,
     "note": ("Derived from printed numbers: 2004 bonds outstanding $64,380,000 before the 2026 deal, less the 2027 maturity ($32,700,000 refunded plus $645,000 tendered) "
              "= $31,035,000 left, which is the amount maturing Nov 1 2026. Check: with the 2000 bonds' $5,000,000 interest and 5% interest on $64,380,000, it reproduces the 2016 statement's printed 2026 column ($39,254,000) and 2027 column ($40,012,250) to the dollar. " + W_NOTE)},
    {"key": "water-2016a1-principal", "name": "Water Series 2016A-1 (principal due Nov 1 2026)", "amount": 6_295_000, "basis": "tied", "kind": "bond_series", "source": W_SRC,
     "note": "Printed on the 2016A-1 cover: the 2026 maturity is $6,295,000 at 4.00%. After the 2026 deal the series has exactly $6,295,000 left (2026 OS p.33), so this is all that remains. " + W_NOTE},
]
w_i = [
    {"key": "water-2004-interest", "name": "Water Refunding Series 2004 (interest)", "amount": i2004, "basis": "proxy", "kind": "bond_series", "source": W_SRC,
     "note": "Derived: 5.0% x $64,380,000 = $3,219,000 for the May 1 and Nov 1 2026 payments (the same figure the 2016 statement's table implies). " + W_NOTE},
    {"key": "water-2016a1-interest", "name": "Water Series 2016A-1 (interest)", "amount": i2016, "basis": "tied", "kind": "bond_series", "source": W_SRC,
     "note": "Printed: the 2016 statement's 2016A-1 column for 2026 is $8,354,800 (p.29), which is $6,295,000 principal plus $2,059,800 interest on $42,455,000 of bonds at 4% and 5%. " + W_NOTE},
]
assert sum(p["amount"] for p in w_p) <= W_P_AMT and sum(p["amount"] for p in w_i) <= W_I_AMT

# ------------------------------------------------------------------ Midway (calendar 2026 per the airport consultant's Table A-3, OS PDF p.169)
must(mid, "Series 2014B $ 2 5,000 $ 25,000", "Midway A-3 2014B row")
must(mid, "Series 2014C3 3,740,432 3,741,300", "Midway A-3 2014C row")
must(mid, "Series 2018A 5,349,043 5,346,763", "Midway A-3 2018A row")
MID_ID = "city.loans.chicago-midway-airport-fund.bonds.other-not-itemised"
MID_AMT = 13_312_661
MID_SRC = {"doc": "Midway 2025AB official statement, Letter of the Airport Consultant, Table A-3 'Existing and Future Debt Service' (fiscal years ending Dec 31), PDF p.169",
           "url": CDN + "1351/Official-Statement.02duRik1H.pdf", "page": "169"}
mid_p = [
    {"key": "midway-2014b", "name": "Midway 2014B (principal and interest)", "amount": 25_000, "basis": "gov_estimate", "kind": "bond_series", "source": MID_SRC,
     "note": "Printed in the airport consultant's table for fiscal 2026 (calendar year, estimate prepared with the Department of Aviation). Only $625,000 of this series is left, paid off in 2030."},
    {"key": "midway-2014c", "name": "Midway 2014C (principal and interest)", "amount": 3_741_300, "basis": "gov_estimate", "kind": "bond_series", "source": MID_SRC,
     "note": ("Printed in the airport consultant's table for fiscal 2026. VARIABLE RATE series ($124,710,000 held by PNC Bank until 7/10/2028): the table says debt service is subject to change "
              "with the rate, and the official statement assumes 3.00% for variable rate bonds (table note 5 of Table 3, OS p.60). Treat this as an estimate.")},
    {"key": "midway-2018a", "name": "Midway 2018A (principal and interest)", "amount": 5_346_763, "basis": "gov_estimate", "kind": "bond_series", "source": MID_SRC,
     "note": "Printed in the airport consultant's table for fiscal 2026. $18,235,000 is left, paid off 1/1/2029, and car rental customer facility charges are pledged to pay it."},
]
assert sum(p["amount"] for p in mid_p) == 9_113_063 and sum(p["amount"] for p in mid_p) < MID_AMT

# ------------------------------------------------------------------ write
splits = [
    {"target": {"by": "id", "id": GO_LINE_ID}, "expect_amount": GO_LINE_AMT, "mode": "budget_split", "pieces": go_pieces,
     "residual": {"name": "Rest of the property tax bonds (2015B, 2017A, 2019A and small older series)",
                  "why": "Several older bonds with mixed interest rates share this leftover. The bond papers we hold print their balances, but not what each pays in 2026, and the budget line is smaller than all of them at full interest."},
     "note": ("Ten series with one clear interest rate were taken out of the leftover. Each is outstanding balance x stated coupon. The budget line is a smaller amount than every series at full scheduled interest "
              "(for example 2019A, 2017A and 2015B alone would use more than what is left), so the leftover is a plug and may be too small. See research/emma_bonds.md.")},
    {"target": {"by": "id", "id": W_P_ID}, "expect_amount": W_P_AMT, "mode": "budget_split", "pieces": w_p,
     "residual": {"name": "Rest of the older Water bonds (mostly Series 2001, not printed in our files)",
                  "why": "Water Series 2001 ($51,180,000 left, final maturity 2030) and the WIFIA loan share this leftover, and the 2001 statement with its yearly schedule is not on the City's bond pages."}},
    {"target": {"by": "id", "id": W_I_ID}, "expect_amount": W_I_AMT, "mode": "budget_split", "pieces": w_i,
     "residual": {"name": "Rest of the older Water bonds' interest (2001, 2017, 2017-2, WIFIA loan)",
                  "why": "These series together would cost more interest than the leftover, so the budget line cannot hold all of them at full scheduled interest. The yearly figures by series are not printed in our files."},
     "side": [{"kind": "not_allocated", "label": "Series 2000 Water bonds: $100,000,000 at 5.0%, $5,000,000 interest a year, refunded 11/1/2026 (Appendix I p.169, 2016 OS table p.29). Not placed in any box because the budget line cannot be shown to include it.",
               "amount": 5_000_000, "period": "2026", "basis": "published", "source": W_SRC}]},
    {"target": {"by": "id", "id": MID_ID}, "expect_amount": MID_AMT, "mode": "budget_split", "pieces": mid_p,
     "residual": {"name": "Midway bonds: budget is higher than the bond papers (not explained)",
                  "why": "The bond papers print $9,113,063 for these three bonds, and the budget line holds $4,199,598 more. No document we hold explains the difference."},
     "note": "The consultant's table is by calendar year, while the budget lines follow the January-to-January bond year, so a few dollars can differ from research/bond_series.md."},
]
json.dump({"meta": {"author": "bonds round 3 (local statements only, no EMMA)", "built_by": "scripts/bond_series_round3_build.py",
                    "description": "Series taken out of the 'Other bonds (not printed one by one)' boxes of GO interest, Water principal and interest, and Midway, from City official statements in raw/bonds. See research/emma_bonds.md."},
           "splits": splits}, open(OUT, "w"), indent=1)
print("wrote", OUT)
print(f"GO interest: {go_total:,} of {GO_LINE_AMT:,}; leftover {GO_LINE_AMT - go_total:,}")
print(f"Water principal: {sum(p['amount'] for p in w_p):,} of {W_P_AMT:,}; leftover {W_P_AMT - sum(p['amount'] for p in w_p):,}")
print(f"Water interest: {sum(p['amount'] for p in w_i):,} of {W_I_AMT:,}; leftover {W_I_AMT - sum(p['amount'] for p in w_i):,}")
print(f"Midway: {sum(p['amount'] for p in mid_p):,} of {MID_AMT:,}; leftover {MID_AMT - sum(p['amount'] for p in mid_p):,}")
