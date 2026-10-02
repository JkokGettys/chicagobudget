#!/usr/bin/env python3
"""Build data/splits/city/bond_series_round4.json: O'Hare older-bond INTEREST split by series.

Run:  python3 scripts/bond_series_round4_build.py     (then build/build_all.sh; split must show applied, 0 skipped)

Method (research/emma_bonds.md): for each of 2016D, 2016E, 2017A, 2017C and 2018C, take the maturity table on the series' own
official statement cover (raw/bonds), remove what the Dec 2025 tender (2025CD OS Appendix H) and the Jan 1 2027 refunding
(2026CD OS Appendix H) took out, and check that the rest equals the balance the 2026CD OS prints on p.64 (to the dollar,
all six tie). Interest for the bond year (Jan 2 2026 to Jan 1 2027) is then balance x coupon, because every remaining
bond is outstanding for the whole year. Interest is DERIVED, not printed. Series 2016G is included, its balance tying only after BOTH the 2026B refunding (2026B OS Appendix H p.329) and the 2026CD refunding are taken off.

The O'Hare principal box is NOT split: the same series' Jan 1 2027 maturities come to more than that box (see the note).
"""
import json
import os
from decimal import Decimal as D, ROUND_HALF_UP

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TXT = os.path.join(ROOT, "raw", "bonds", "txt")
OUT = os.path.join(ROOT, "data", "splits", "city", "bond_series_round4.json")
CDN = "https://bondlink-cdn.com/1348/"


def txt(prefix):
    for f in sorted(os.listdir(TXT)):
        if f.startswith(prefix):
            return open(os.path.join(TXT, f)).read()
    raise SystemExit("missing " + prefix)


def must(t, s, what):
    if s not in t:
        raise SystemExit(f"CHECK FAILED ({what}): {s!r}")


def dollars(x):
    return int(D(x).quantize(D(1), rounding=ROUND_HALF_UP))


cd = txt("ohare_2026CD_OS")
cd25 = txt("Final-Official-Statement---ORD-2025CD")
c16 = txt("O'Hare_2016D-G")
c17 = txt("ORD_2017ABCD_OS")
c18 = txt("ORD_2018ABC_OS")
# printed balances after the 2026CD deal (2026CD OS PDF p.64)
must(cd, "Series 2016D (Non-AMT) 598,730,000 392,740,000", "2016D balance")
must(cd, "Series 2016E (Non-AMT) 61,540,000 34,900,000", "2016E balance")
must(cd, "Series 2017A (Non-AMT) 39,345,000 13,010,000", "2017A balance")
must(cd, "Series 2016G (AMT) 58,675,000 37,075,000", "2016G balance")
must(txt("ohare_2026B_OS"), "Series 2016G (AMT) 61,800,000 58,675,000", "2016G balance before 2026CD")
must(txt("ohare_2026B_OS"), "Total $3,125,000", "2016G 2026B refunded total")
must(cd, "Series 2017C (Non-AMT) 61,985,000 34,380,000", "2017C balance")
must(cd, "Series 2018C (Taxable) 710,130,000 710,130,000", "2018C balance")
# covers
must(c16, "$131,890,000 5.25% Term Bonds due January 1, 2042", "2016D term 2042")
must(c16, "$169,505,000 5.00% Term Bonds due January 1, 2047", "2016D term 2047")
must(c16, "$216,325,000 5.00% Term Bonds due January 1, 2052", "2016D term 2052")
must(c16, "2027 34,900,000 5.00 113.619 3.38 167593WW8", "2016E 2027")
must(c17, "$2,775,000 4.000% Series 2017A Term Bonds due January 1, 2040", "2017A term")
must(c17, "$6,080,000 4.000% Series 2017C Term Bonds due January 1, 2041", "2017C term 4%")
must(c17, "$18,500,000 5.000% Series 2017C Term Bonds due January 1, 2041", "2017C term 5%")
must(c18, "$400,000,000 Term Bond Due January 1, 2049; Interest Rate: 4.472%", "2018C 2049")
must(c18, "$400,000,000 Term Bond Due January 1, 2054; Interest Rate: 4.572%", "2018C 2054")
must(cd25, "Total $89,870,000", "2018C tender total")
must(cd, "Total $205,990,000", "2016D refunded total")

C = D
SER = {}
# maturity {key: (cover amount, coupon %)}, tendered Dec 2025 (2025CD OS App. H p.392-394), refunded 1/1/2027 (2026CD OS App. H p.339-343)
SER["2016D"] = dict(
    cover={2027: (6910000, "5"), 2028: (7265000, "5.25"), 2029: (14985000, "5.25"), 2030: (15770000, "5.25"), 2031: (16595000, "5.25"),
           2032: (17475000, "5.25"), 2033: (18385000, "5.25"), 2034: (19355000, "5.25"), 2035: (20370000, "5.25"), 2036: (21445000, "5.25"),
           2037: (22565000, "5.25"), 2042: (131890000, "5.25"), 2047: (169505000, "5"), 2052: (216325000, "5")},
    tender={2030: 8145000, 2031: 7545000, 2032: 13670000, 2033: 6355000, 2034: 13125000, 2035: 13110000, 2036: 12315000, 2037: 5225000, 2042: 20620000},
    refunded={2028: 7265000, 2029: 14985000, 2030: 7625000, 2031: 9050000, 2032: 3805000, 2033: 12030000, 2034: 6230000, 2035: 7260000,
              2036: 9130000, 2037: 17340000, 2042: 111270000},
    balance=392740000, cover_doc="O'Hare_2016D-G_Sr._Lien_GARB_OS.bW9YWx6Cu3.pdf p.2", official="General Airport Senior Lien Revenue Bonds, Series 2016D (Non-AMT)")
SER["2016E"] = dict(
    cover={2027: (34900000, "5"), 2028: (26640000, "5.25")}, tender={}, refunded={2028: 26640000},
    balance=34900000, cover_doc="O'Hare_2016D-G_Sr._Lien_GARB_OS.bW9YWx6Cu3.pdf p.3", official="General Airport Senior Lien Revenue Bonds, Series 2016E (Non-AMT)")
SER["2016G"] = dict(
    cover={2027: (590000, "5"), 2028: (620000, "5.25"), 2029: (1350000, "5.25"), 2030: (1425000, "5.25"), 2031: (1500000, "5.25"),
           2037: (10720000, "5"), 2042: (11680000, "5"), 2047: (14895000, "5"), 2052: (19020000, "5")},
    tender={},
    # 2026B refunding (2026B OS Appendix H p.329: 3,125,000) plus 2026CD refunding (2026CD OS Appendix H p.341: 21,600,000)
    refunded={2028: 540000 + 80000, 2029: 1180000 + 170000, 2030: 1245000 + 180000, 2031: 1310000 + 190000, 2037: 9365000 + 1355000, 2042: 7960000 + 1150000},
    balance=37075000, cover_doc="O'Hare_2016D-G_Sr._Lien_GARB_OS.bW9YWx6Cu3.pdf p.5 (also refunded in part by the 2026B deal, ohare_2026B_OS.pdf Appendix H p.329)", official="General Airport Senior Lien Revenue Bonds, Series 2016G (AMT)")
SER["2017A"] = dict(
    cover={2027: (7135000, "5"), 2028: (7480000, "5"), 2029: (7875000, "5"), 2030: (8260000, "5"), 2031: (8665000, "5"), 2032: (710000, "3.125"),
           2033: (730000, "5"), 2034: (770000, "3.25"), 2035: (795000, "3.25"), 2036: (825000, "3.375"), 2037: (850000, "5"), 2040: (2775000, "4")},
    tender={2031: 6905000, 2033: 405000, 2037: 215000}, refunded={2028: 7480000, 2029: 7875000, 2030: 8260000, 2031: 1760000, 2033: 325000, 2037: 635000},
    balance=13010000, cover_doc="ORD_2017ABCD_OS.ugRRnIFv.pdf p.2", official="General Airport Senior Lien Revenue Refunding Bonds, Series 2017A (Non-AMT)")
SER["2017C"] = dict(
    cover={2027: (5365000, "5"), 2028: (5630000, "5"), 2029: (5300000, "5"), 2030: (4065000, "5"), 2031: (4270000, "5"), 2032: (4480000, "5"),
           2033: (4705000, "4"), 2034: (4895000, "4"), 2035: (5090000, "4"), 2036: (5295000, "4"), 2037: (5505000, "4"), 2040: (6080000, "4"), 2041: (18500000, "5")},
    tender={2031: 3580000, 2032: 2800000, 2034: 2550000, 2035: 5000, 2041: 4295000 + 3965000},
    refunded={2028: 5630000, 2029: 5300000, 2030: 4065000, 2031: 690000, 2032: 1680000, 2041: 10240000},
    balance=34380000, cover_doc="ORD_2017ABCD_OS.ugRRnIFv.pdf p.4", official="General Airport Senior Lien Revenue Refunding Bonds, Series 2017C (Non-AMT)")
SER["2018C"] = dict(
    cover={2049: (355065000, "4.472"), 2054: (355065000, "4.572")}, tender={}, refunded={},
    balance=710130000, cover_doc="ORD_2018ABC_OS.vKd4ptjc.pdf p.4 (two $400,000,000 term bonds; the Dec 2025 tender took $44,935,000 from each)", official="General Airport Senior Lien Revenue Bonds, Series 2018C (Taxable)")

BOX_ID = "city.loans.chicago-o-hare-airport-fund.0740-2005-0902.other-not-itemised.other-not-itemised"
BOX_AMT = 58_717_912
SRC = {"doc": "O'Hare 2026CD official statement p.64 (balances) and Appendix H p.339-343 (refunded); 2025CD official statement Appendix H p.391-394 (tendered); each series' own statement cover (coupons)",
       "url": CDN + "ILChicago07a-FIN.1Lay3BJv8.pdf"}
pieces, total = [], 0
principal_side = []
for k, s in SER.items():
    left = {}
    for y, (a, c) in s["cover"].items():
        r = a - s["tender"].get(y, 0) - s["refunded"].get(y, 0)
        assert r >= 0, (k, y)
        if r:
            left[y] = (r, c)
    bal = sum(a for a, _ in left.values())
    assert bal == s["balance"], (k, bal, s["balance"])  # ties to the printed post-refunding balance, to the dollar
    interest = dollars(sum(D(a) * D(c) / 100 for a, c in left.values()))
    prin27 = left.get(2027, (0, 0))[0] if k != "2018C" else 0
    total += interest
    principal_side.append({"series": k, "principal_due_1_1_2027_after_refunding": prin27})
    pieces.append({
        "key": f"ohare-{k.lower()}-interest", "name": f"O'Hare {k} (interest)", "amount": interest, "basis": "proxy", "kind": "bond_series",
        "why": ("This is one old airport bond's yearly interest to the people who lent the money, and it is already as small as the bond itself."
                if interest >= 10_000_000 else None),
        "source": SRC,
        "note": (f"Derived, not printed: balance after the 2026 refunding ${bal:,} x each maturity's coupon = ${interest:,} for the bond year Jan 2 2026 to Jan 1 2027. "
                 f"The balance ties to the 2026CD OS p.64 to the dollar after taking the Dec 2025 tender and the Jan 1 2027 refunding off the cover list ({s['cover_doc']}). "
                 f"Series: {s['official']}. Fixed rate. Gross of any federal subsidy or pledged passenger/customer charges. The 2026 budget line was written before the 2026 refunding, "
                 f"so it may hold slightly more interest on bonds that were refunded in October 2026."),
        "extra": {"balance_dollars": bal, "status": "derived_balance_x_coupon"},
    })
assert total < BOX_AMT, (total, BOX_AMT)
sum_prin = sum(p["principal_due_1_1_2027_after_refunding"] for p in principal_side)

splits = [{
    "target": {"by": "id", "id": BOX_ID}, "expect_amount": BOX_AMT, "mode": "budget_split", "pieces": pieces,
    "residual": {"name": "Rest of the older bonds' interest (other older series and rounding)",
                 "why": "The 2026 budget line was written before the October 2026 refunding, so it still holds interest on bonds that were refunded, and the bond papers do not say how much. It also holds the small remaining older series. We do not guess."},
    "note": (f"Six older bonds were taken out of the leftover, each balance times its interest rates, with the balance checked against the airport's own 2026 bond table. "
             f"Their January 1 2027 principal (not placed in any box) is ${sum_prin:,}; the principal box for these older bonds is $46,676,911, so it cannot hold them all and was left alone."),
    "side": [{"kind": "derived_principal", "label": "Principal due 1/1/2027 after the 2026 refunding, by series (2016D, 2016E, 2016G, 2017A, 2017C; 2018C has none until 2049). Not placed in the principal box because the sum is larger than that box.",
              "amount": sum_prin, "period": "bond year ending 1/1/2027", "basis": "proxy", "source": SRC, "items": principal_side}],
}]
json.dump({"meta": {"author": "bonds round 4 (O'Hare older interest)", "built_by": "scripts/bond_series_round4_build.py",
                    "description": "O'Hare older-bond interest split by series from the City's own statements. See research/emma_bonds.md."},
           "splits": splits}, open(OUT, "w"), indent=1)
print("wrote", OUT)
print(f"O'Hare older interest: {total:,} of {BOX_AMT:,}; leftover {BOX_AMT - total:,}; derived 1/1/2027 principal {sum_prin:,}")
for p in pieces:
    print(f"  {p['name']}: {p['amount']:,}")
