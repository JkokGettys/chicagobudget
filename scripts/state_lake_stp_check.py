#!/usr/bin/env python3
"""Launch fix 5: is the $102,140,573 State/Lake STP ledger record (2025-06-01 extract) superseded by the newer
records (2026-05-31 extract)? Every number in research/state_lake_stp.md comes from this script.

Inputs (cached under raw/, gitignored):
  raw/grants/midyear925.json                    City Mid-Year Grants 925 ledger (dataset iyu8-jkf8), extracts 2025-06-01 and 2026-05-31
  raw/cdot/usaspending_IL2016002_funding.json   USASpending award funding history for FTA award IL-2016-002
  raw/grants/usaspending_chicago_awards.json    USASpending prime award summary (obligation, outlays; Aug 2025 pull)
  raw/cdot/cdot_stp_2025_2029.txt               CDOT STP program text (State/Lake lines)

Run from anywhere: python3 scripts/state_lake_stp_check.py        (prints the tables)
cdot_build.py imports facts() and asserts the same equalities before it writes the notes."""
import collections, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTH = {1: "Oct", 2: "Nov", 3: "Dec", 4: "Jan", 5: "Feb", 6: "Mar", 7: "Apr", 8: "May", 9: "Jun", 10: "Jul", 11: "Aug", 12: "Sep"}


def cal(fy, period):
    """Federal fiscal period (October = 1) -> 'Mon YYYY'."""
    y = fy - 1 if period <= 3 else fy
    return f"{MONTH[period]} {y}"


def facts():
    led = json.load(open(os.path.join(ROOT, "raw", "grants", "midyear925.json")))
    d1209 = [r for r in led if r["grant_project_code"] == "D1209"]
    old = [r for r in d1209 if r["data_extract_as_of_date"].startswith("2025")]
    new = [r for r in d1209 if r["data_extract_as_of_date"].startswith("2026")]
    fta = lambda r: r["grant_agency"] in ("FTA", "FTA (DIRECT)")
    num = lambda r, k: float(r.get(k) or 0)
    hist = json.load(open(os.path.join(ROOT, "raw", "cdot", "usaspending_IL2016002_funding.json")))["results"]
    ob = [(r["reporting_fiscal_year"], r["reporting_fiscal_month"], r["transaction_obligated_amount"]) for r in hist
          if r["transaction_obligated_amount"]]
    usa = next(a for a in json.load(open(os.path.join(ROOT, "raw", "grants", "usaspending_chicago_awards.json")))
               if a["Award ID"] == "IL-2016-002")
    # extract overlap
    old_all = [r for r in led if r["data_extract_as_of_date"].startswith("2025")]
    new_all = [r for r in led if r["data_extract_as_of_date"].startswith("2026")]
    oid, nid = {r["record_id"] for r in old_all}, {r["record_id"] for r in new_all}
    ok = {(r["fund_code"], r["grant_project_code"]) for r in old_all}
    nk = {(r["fund_code"], r["grant_project_code"]) for r in new_all}
    f = {}
    f["old_record"] = old[0]
    f["old_budget"] = num(old[0], "budget")
    f["new_stp"] = [r for r in new if r["fund_code"] == "F0W16"][0]
    f["new_stp_budget"] = num(f["new_stp"], "budget")
    f["new_stp_spent"] = num(f["new_stp"], "expended_project_to_date")
    f["new_stp_unspent"] = f["new_stp_budget"] - f["new_stp_spent"]
    f["new_fta_budget"] = sum(num(r, "budget") for r in new if fta(r))
    f["new_fta_spent"] = sum(num(r, "expended_project_to_date") for r in new if fta(r))
    f["new_fta_unspent"] = f["new_fta_budget"] - f["new_fta_spent"]
    f["award_obligated"] = float(usa["Award Amount"])
    f["award_outlays"] = float(usa["Total Outlays"])
    f["history_total"] = sum(o[2] for o in ob)
    by_fy = collections.defaultdict(float)
    for fy, p, a in ob:
        by_fy[fy] += a
    f["by_fy"] = dict(sorted(by_fy.items()))
    f["dec2024"] = sum(a for fy, p, a in ob if (fy, p) == (2025, 3))
    f["jan2025_deob"] = sum(a for fy, p, a in ob if (fy, p) == (2025, 4) and a < 0)
    f["jan2025_new"] = sum(a for fy, p, a in ob if (fy, p) == (2025, 4) and a > 0)
    f["aug2025"] = {a: (fy, p) for fy, p, a in ob if (fy, p) == (2025, 11)}
    aug = sorted((a for fy, p, a in ob if (fy, p) == (2025, 11)), reverse=True)   # FTA period 11 of FY2025 = Aug 2025
    assert aug == [85_000_000.0, 48_040_000.0, 11_896_082.0, 3_103_918.0], aug
    # The 85.0M equals CDOT's FFY2025 STP programming for State/Lake (68,552,719 + 16,447,281). USASpending does not name the
    # fund of the 48.04M, so calling it CMAQ is our reading. The last two add to 15.0M, the Carbon Reduction record in the 2026 ledger.
    f["aug2025_stp"], f["aug2025_cmaq"], f["aug2025_crp"] = aug[0], aug[1], aug[2] + aug[3]
    f["fy2023_stp"] = sum(a for fy, p, a in ob if fy == 2023 and a in (28_968_000.0, 5_112_000.0))
    f["cum_after_dec2024"] = sum(a for fy, p, a in ob if (fy, p) <= (2025, 3))
    f["cum_after_jan2025"] = sum(a for fy, p, a in ob if (fy, p) <= (2025, 4))
    f["not_in_new_ledger"] = f["old_budget"] + f["aug2025_stp"] + f["aug2025_cmaq"]
    f["ledger_plus_missing"] = f["new_fta_budget"] + f["not_in_new_ledger"]
    f["outlay_gap"] = f["award_outlays"] - f["new_fta_spent"]
    f["residual_check"] = f["aug2025_stp"] + f["aug2025_cmaq"] - f["outlay_gap"]
    f["overlap"] = {"old_rows": len(old_all), "new_rows": len(new_all), "record_ids_in_both": len(oid & nid),
                    "fund_project_pairs_in_both": len(ok & nk), "pairs_old": len(ok), "pairs_new": len(nk)}
    # CDOT STP program lines for State/Lake
    f["cdot_ffy24"] = 77_140_573 + 25_000_000
    f["cdot_ffy25"] = 68_552_719 + 16_447_281
    return f


def main():
    f = facts()
    m = lambda x: f"${x:,.0f}"
    print("== 1. The two ledger records")
    o, n = f["old_record"], f["new_stp"]
    print(f"  older  {o['data_extract_as_of_date'][:10]} {o['record_id']}  grant start {o['grant_start_date'][:10]}  budget {m(f['old_budget'])}  spent {m(float(o.get('expended_project_to_date') or 0))}")
    print(f"  newer  {n['data_extract_as_of_date'][:10]} {n['record_id']}  grant start {n['grant_start_date'][:10]}  budget {m(f['new_stp_budget'])}  spent {m(f['new_stp_spent'])}  unspent {m(f['new_stp_unspent'])}")
    ov = f["overlap"]
    print(f"  the two extracts: {ov['old_rows']} and {ov['new_rows']} rows, record ids in both: {ov['record_id' + 's_in_both']}, (fund, project) pairs in both: {ov['fund_project_pairs_in_both']} of {ov['pairs_old']} and {ov['pairs_new']}")
    print("== 2. FTA obligations on award IL-2016-002 (USASpending, federal fiscal periods, October = 1)")
    print("  by FTA fiscal year:", {k: m(v) for k, v in f["by_fy"].items()}, "total", m(f["history_total"]))
    print(f"  FY2025 period 3 ({cal(2025, 3)}): {m(f['dec2024'])}  (= old ledger record {m(f['old_budget'])}: {f['dec2024'] == f['old_budget']})  CDOT FFY2024 STP {m(f['cdot_ffy24'])}")
    print(f"  FY2025 period 4 ({cal(2025, 4)}): de-obligated {m(-f['jan2025_deob'])}, new {m(f['jan2025_new'])}, net {m(f['jan2025_new'] + f['jan2025_deob'])}")
    print(f"  cumulative obligations after Dec 2024 {m(f['cum_after_dec2024'])}, after Jan 2025 {m(f['cum_after_jan2025'])} (the {m(f['old_budget'])} is never reversed)")
    print(f"  FY2025 period 11 ({cal(2025, 11)}): STP {m(f['aug2025_stp'])} (= CDOT FFY2025 STP {m(f['cdot_ffy25'])}), CMAQ {m(f['aug2025_cmaq'])}, Carbon Reduction {m(f['aug2025_crp'])}")
    print(f"  FY2023 STP tranches 28,968,000 + 5,112,000 = {m(f['fy2023_stp'])}  (= newer ledger STP budget {m(f['new_stp_budget'])}: {f['fy2023_stp'] == f['new_stp_budget']})")
    print("== 3. Does the newer extract already hold the older slice? Award total versus ledger")
    print(f"  award obligated (USASpending) {m(f['award_obligated'])}")
    print(f"  newer ledger, FTA records only: budget {m(f['new_fta_budget'])}, spent {m(f['new_fta_spent'])}, unspent {m(f['new_fta_unspent'])}")
    print(f"  not in the newer ledger: old record {m(f['old_budget'])} + Aug 2025 STP {m(f['aug2025_stp'])} + Aug 2025 CMAQ {m(f['aug2025_cmaq'])} = {m(f['not_in_new_ledger'])}")
    print(f"  newer ledger + those three = {m(f['ledger_plus_missing'])}, award {m(f['award_obligated'])}, difference {m(f['ledger_plus_missing'] - f['award_obligated'])}")
    print("== 4. The $127,618,674 'rest of the award' box")
    print(f"  Aug 2025 STP + CMAQ {m(f['aug2025_stp'] + f['aug2025_cmaq'])} minus outlay gap (USASpending {m(f['award_outlays'])} minus ledger spent {m(f['new_fta_spent'])} = {m(f['outlay_gap'])}) = {m(f['residual_check'])}  (tree box 127,618,674)")


if __name__ == "__main__":
    main()
