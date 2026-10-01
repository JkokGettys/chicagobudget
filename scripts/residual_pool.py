"""Shared loaders for the transfer-residual investigation (research/transfer_residual.md).

Builds, for three books (2025 ordinance, 2026 recommendations, 2026 ordinance), keyed vectors of
  * revenue lines            key ("REV", fund, source)
  * appropriation lines      key ("APP", fund, dept, account text)
and the printed figures used as targets. Reads only raw/ (gitignored); no network.
"""
import json
import os
import re
from collections import defaultdict

RAW = os.path.join(os.path.dirname(__file__), "..", "raw")
BOOKS = ("25", "rec", "ord")


def _load(*p):
    return json.load(open(os.path.join(RAW, *p)))


# Printed figures (ordinance Summary B/G; rec book p. 603; 2025 ordinance Summary B)
PRINTED = {
    "25": dict(deduct=1_622_468_611, debt=117_145_000, gross=18_842_061_980, fg_line=1_543_512_195,
               appAB=8_955_367 + 9_419_419, match=23_999_259),
    "rec": dict(deduct=1_679_051_626, debt=117_145_000, gross=18_350_767_715, fg_line=1_389_476_663,
                appAB=9_015_367 + 10_911_809, match=35_514_285),
    "ord": dict(deduct=1_700_089_446, debt=125_926_011, gross=18_668_568_460, fg_line=1_528_907_883,
                appAB=7_766_967 + 10_911_809, match=35_514_285),
}
for b in BOOKS:
    p = PRINTED[b]
    p["resid"] = p["deduct"] - p["fg_line"] - p["appAB"]            # 60.6M / 269.6M / 152.5M
    p["resid_after_match"] = p["resid"] - p["match"]


def revenue():
    src = {"25": _load("gap", "revenue_2025.json"), "rec": _load("context", "revenue_rec_2026.json"),
           "ord": _load("context", "revenue_2026.json")}
    out = defaultdict(lambda: dict.fromkeys(BOOKS, 0))
    for b, rows in src.items():
        for x in rows:
            out[("REV", x["fund_code"], x["revenue_source"])][b] += round(float(x["estimated_revenue"]))
    return out


def approps():
    o = _load("city_appropriations_2026.json")
    r = _load("gap", "recs_approp_2026.json")
    a = _load("gap", "approp_2025.json")
    out = defaultdict(lambda: dict.fromkeys(BOOKS, 0))
    norm = lambda s: re.sub(r"\s+", " ", s.strip().lower())
    for b, rows, f in (("25", a, lambda x: round(float(x["_ordinance_amount_"]))),
                       ("rec", r, lambda x: round(float(x["recommendation"] or 0))),
                       ("ord", o, lambda x: int(x["_ordinance_amount_"]))):
        for x in rows:
            k = ("APP", x["fund_code"], x["department_description"], norm(x["appropriation_account_description"]))
            out[k][b] += f(x)
    return out, {"25": a, "rec": r, "ord": o}
