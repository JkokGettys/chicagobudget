#!/usr/bin/env python3
"""Remove duplicate rows from City Payments (s4vu-giwb) and write deduped 2025 and 2026 year-to-date files.

Inputs : raw/city_payments_2025.csv                (check year 2025, 115,810 rows)
         raw/contracts/payments_all.csv            (all years; the 2026 rows are the year to date)
         raw/contracts/contracts_all.csv           (only for the award-cap diagnostic)
         data/pensions_2026.json                   (only for the MEABF cross check)
Outputs: raw/contracts/payments_2025_dedup.csv
         raw/contracts/payments_2026ytd_dedup.csv
         data/payments_dedupe_report.json

RULE (chosen, see research/payments_dedupe.md for the evidence)
  Two rows are the same payment line when voucher_number, amount, check_date, vendor_name and contract_number
  are all equal. department_name is IGNORED, because the dataset often carries the same payment twice, once with
  the department filled and once blank. Keep one row per key (the one with a department if any), drop the rest.
  EXEMPTION: rows of $99,000,000 or more are never dropped. The City pays big wires as several checks capped at
  $99M, so identical $99M lines inside one voucher are tranches, not duplicates.
  Only rows with a voucher_number are touched (older rolled-up rows have none).

Other rules measured for comparison (not used): exact full-row duplicates (all six columns), and the loose key
without the $99M exemption.

Importable: dedupe_rows(rows) -> (kept_rows, dropped_rows)."""
import csv, json, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK_CAP = 99_000_000.0
COLS = ["voucher_number", "amount", "check_date", "department_name", "contract_number", "vendor_name"]
LOOSE = ("voucher_number", "amount", "check_date", "vendor_name", "contract_number")


def _mark(rows, key_cols, exempt):
    """Return a list of booleans, True = drop. Keeps the first row of each key, preferring a row with a department."""
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        if not r["voucher_number"]:
            continue
        if exempt and float(r["amount"]) >= CHECK_CAP:
            continue
        groups[tuple(r[c] for c in key_cols)].append(i)
    drop = [False] * len(rows)
    for idx in groups.values():
        if len(idx) < 2:
            continue
        keep = next((i for i in idx if rows[i]["department_name"]), idx[0])
        for i in idx:
            if i != keep:
                drop[i] = True
    return drop


def dedupe_rows(rows):
    drop = _mark(rows, LOOSE, exempt=True)
    kept = [r for r, d in zip(rows, drop) if not d]
    gone = [r for r, d in zip(rows, drop) if d]
    # Second pass: the same payment line listed twice with two spellings of the vendor name
    # (e.g. "F.H. PASCHEN, S.N. NIELSEN" vs "F.H. PASCHEN S.N. NIELSEN"). Same voucher, amount, date and
    # contract, exactly two rows, two different names. Found by scripts/paidtodate_build.py: 1,014 pairs in
    # 2026 YTD. Direct vouchers (contract "DV") are excluded because unrelated payees share them.
    # Keep the row with a department (or the first one).
    groups = defaultdict(list)
    for i, r in enumerate(kept):
        if not r["voucher_number"] or r["contract_number"] in ("", "DV") or float(r["amount"]) >= CHECK_CAP:
            continue
        groups[(r["voucher_number"], r["amount"], r["check_date"], r["contract_number"])].append(i)
    drop2 = set()
    for idx in groups.values():
        if len(idx) == 2 and kept[idx[0]]["vendor_name"] != kept[idx[1]]["vendor_name"]:
            keep = next((i for i in idx if kept[i]["department_name"]), idx[0])
            drop2.update(i for i in idx if i != keep)
    gone += [kept[i] for i in sorted(drop2)]
    kept = [r for i, r in enumerate(kept) if i not in drop2]
    return kept, gone


def tot(rows):
    return sum(float(r["amount"]) for r in rows)


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)


def top(rows, field, n=20):
    d = defaultdict(lambda: [0, 0.0])
    for r in rows:
        x = d[r[field]]; x[0] += 1; x[1] += float(r["amount"])
    return d


def top_table(before, dropped, field, n=20):
    b = top(before, field); x = top(dropped, field)
    out = []
    for k, (cnt, amt) in sorted(x.items(), key=lambda kv: -kv[1][1])[:n]:
        out.append({field: k, "rows_removed": cnt, "dollars_removed": round(amt, 2),
                    "paid_before": round(b[k][1], 2), "paid_after": round(b[k][1] - amt, 2)})
    return out


def measure(rows):
    """Row and dollar counts for each rule on one year of rows."""
    res = {}
    full_cols = tuple(COLS)
    for name, cols, ex in (("exact_full_row", full_cols, False), ("exact_full_row_with_99M_exemption", full_cols, True),
                           ("loose_key_ignoring_department", LOOSE, False), ("CHOSEN_loose_key_with_99M_exemption", LOOSE, True)):
        d = _mark(rows, cols, ex)
        res[name] = {"rows_removed": sum(d), "dollars_removed": round(sum(float(r["amount"]) for r, x in zip(rows, d) if x), 2)}
    return res


def diagnostics(all_rows):
    """Evidence tables used to choose the rule. All computed here."""
    out = {}
    # 1. Award cap: contracts that started on or after 2022-06-01 have all their payments in the voucher-level era (2022+).
    #    If a rule removes true duplicates, contracts with repeats should stop paying more than their total award.
    cons = list(csv.DictReader(open(f"{ROOT}/raw/contracts/contracts_all.csv")))
    award = defaultdict(float); first = {}
    for c in cons:
        n = c["purchase_order_contract_number"]
        award[n] += float(c["award_amount"] or 0)
        s = (c["start_date"] or "")[:10]
        if s and (n not in first or s < first[n]):
            first[n] = s
    new = {n for n, s in first.items() if s >= "2022-06-01" and award[n] > 0}
    # Payments older than two years are rolled up by the City and carry no voucher number, so keep only contracts whose rows ALL have a voucher.
    novoucher = {r["contract_number"] for r in all_rows if not r["voucher_number"]}
    rows = [r for r in all_rows if r["contract_number"] in new and r["contract_number"] not in novoucher and r["check_date"][-4:] >= "2022"]
    full_d = _mark(rows, tuple(COLS), False); loose_d = _mark(rows, LOOSE, False); chosen_d = _mark(rows, LOOSE, True)
    per = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0, 0])   # raw, after_full, after_loose, after_chosen, n_full_dropped, n_loose_dropped
    for r, f, l, c in zip(rows, full_d, loose_d, chosen_d):
        a = float(r["amount"]); p = per[r["contract_number"]]
        p[0] += a; p[1] += 0 if f else a; p[2] += 0 if l else a; p[3] += 0 if c else a; p[4] += f; p[5] += l
    def over(group, i):
        g = list(group)
        return round(sum(1 for p, n in g if p[i] > award[n] * 1.001) / len(g), 4) if g else None
    items = [(p, n) for n, p in per.items()]
    nodup = [(p, n) for p, n in items if p[5] == 0]
    dup = [(p, n) for p, n in items if p[5] > 0]
    loose_only = [(p, n) for p, n in items if p[5] > p[4] and p[4] == 0]
    out["award_cap_test"] = {
        "what": "share of contracts whose payments since 2022 exceed the contract's total award (all revisions summed, 0.1% tolerance). Contracts that started on or after 2022-06-01 with award > 0 and no rolled-up (voucher-less) payment rows.",
        "contracts_tested": len(items), "contracts_with_no_repeat_rows": len(nodup), "contracts_with_repeat_rows": len(dup),
        "share_over_award_contracts_without_repeats_(baseline)": over(nodup, 0),
        "share_over_award_contracts_with_repeats_raw": over(dup, 0),
        "share_over_award_after_exact_full_row": over(dup, 1),
        "share_over_award_after_loose_key": over(dup, 2),
        "share_over_award_after_chosen_rule": over(dup, 3),
        "contracts_whose_only_repeats_differ_by_department": len(loose_only),
        "share_over_award_those_raw": over(loose_only, 0), "share_over_award_those_after_loose_key": over(loose_only, 2),
    }
    t = [r for r in all_rows if r["contract_number"] == "47314"]
    td = _mark(t, LOOSE, True)
    out["transystems_47314"] = {"award_all_revisions": award["47314"], "paid_all_years_raw": round(tot(t), 2),
                                "paid_all_years_after_chosen_rule": round(sum(float(r["amount"]) for r, d in zip(t, td) if not d), 2)}
    # 2. MEABF cross check: PV27 (central Finance) vouchers to the Municipal Employees' fund vs the statutory contribution.
    pens = json.load(open(f"{ROOT}/data/pensions_2026.json"))["funds"]["MEABF"]
    stat26 = pens["budget_2026"]["statutory_contribution"]
    m = [r for r in all_rows if r["vendor_name"] == "MUNICIPAL EMPLOYEE PENSION FD" and r["voucher_number"].startswith("PV27")]
    chk = {}
    for y in ("2025", "2026"):
        ys = [r for r in m if r["check_date"][-4:] == y]
        nb = _mark(ys, LOOSE, False); ch = _mark(ys, LOOSE, True)
        chk[y] = {"pv27_paid_raw": round(tot(ys), 2),
                  "pv27_paid_if_99M_checks_were_dropped": round(sum(float(r["amount"]) for r, d in zip(ys, nb) if not d), 2),
                  "pv27_paid_chosen_rule": round(sum(float(r["amount"]) for r, d in zip(ys, ch) if not d), 2),
                  "rows_of_99M": sum(1 for r in ys if float(r["amount"]) == CHECK_CAP)}
    out["meabf_cross_check"] = {"what": "central Finance (PV27) direct vouchers to MEABF compared with what the City reports contributing (ACFR FY2025) and budgets (2026 ordinance). If the repeated $99M lines were duplicates, payments would fall well below the reported contribution.",
                                "acfr_fy2025_city_contribution_to_meabf": pens["acfr_fy2025"]["city_contributions_2025_thousands"] * 1000,
                                "budget_2026_statutory_contribution": stat26, "budget_2026_advance_contribution": pens["budget_2026"]["advance_contribution"],
                                "by_check_year": chk}
    # 3. shape of repeats
    d25 = [r for r in all_rows if r["check_date"][-4:] == "2025"]
    gp = defaultdict(list)
    for i, r in enumerate(d25):
        gp[tuple(r[c] for c in LOOSE)].append(i)
    pair = defaultdict(int)
    for idx in gp.values():
        if len(idx) > 1:
            nb = sum(1 for i in idx if not d25[i]["department_name"])
            pair["one blank department + one filled (same payment listed twice)" if len(idx) == 2 and nb == 1 else
                 "all copies identical including department" if nb in (0, len(idx)) else "other mix"] += len(idx) - 1
    out["shape_of_repeats_2025_extra_rows"] = dict(pair)
    return out


def main():
    p25 = list(csv.DictReader(open(f"{ROOT}/raw/city_payments_2025.csv")))
    all_rows = list(csv.DictReader(open(f"{ROOT}/raw/contracts/payments_all.csv")))
    p26 = [r for r in all_rows if r["check_date"][-4:] == "2026"]
    latest = max(p26, key=lambda r: (r["check_date"][-4:], r["check_date"][:2], r["check_date"][3:5]))["check_date"]
    years = {"2025": p25, "2026ytd": p26}
    out_files = {"2025": "raw/contracts/payments_2025_dedup.csv", "2026ytd": "raw/contracts/payments_2026ytd_dedup.csv"}
    report = {"generated_by": "scripts/payments_dedupe.py",
              "rule": ("Same payment line = equal voucher_number + amount + check_date + vendor_name + contract_number. department_name is ignored "
                       "(the dataset lists many payments twice, once with the department and once blank). Keep one row per key (prefer the row with a department). "
                       "Rows of $99,000,000 or more are never dropped: the City splits large wires into checks capped at $99M, so identical $99M lines in one voucher are tranches. "
                       "Only rows with a voucher number are considered."),
              "check_cap_exemption_amount": CHECK_CAP, "latest_2026_check_date": latest,
              "label_2026ytd": f"paid Jan 1 to {latest} 2026, partial year", "by_year": {}}
    for y, rows in years.items():
        kept, dropped = dedupe_rows(rows)
        write_csv(f"{ROOT}/{out_files[y]}", kept)
        b, a = tot(rows), tot(kept)
        exempt_rows = [r for r in rows if float(r["amount"]) >= CHECK_CAP]
        drop_noex = _mark(rows, LOOSE, False)
        exempt_dropped_by_noex = sum(float(r["amount"]) for r, d, x in zip(rows, drop_noex, [float(r["amount"]) >= CHECK_CAP for r in rows]) if d and x)
        report["by_year"][y] = {
            "output_file": out_files[y],
            "rows_before": len(rows), "rows_after": len(kept), "rows_removed": len(dropped),
            "dollars_before": round(b, 2), "dollars_after": round(a, 2), "dollars_removed": round(tot(dropped), 2),
            "negative_rows_removed": sum(1 for r in dropped if float(r["amount"]) < 0),
            "rows_of_99M_or_more_kept_by_exemption": len(exempt_rows),
            "dollars_of_99M_or_more_rows_that_the_loose_key_would_drop_without_exemption": round(exempt_dropped_by_noex, 2),
            "rules_compared": measure(rows),
            "top20_vendors_by_dollars_removed": top_table(rows, dropped, "vendor_name"),
            "top20_contracts_by_dollars_removed": top_table(rows, dropped, "contract_number"),
        }
        print(y, "rows", len(rows), "->", len(kept), "removed $", round(tot(dropped)))
    report["diagnostics"] = diagnostics(all_rows)
    json.dump(report, open(f"{ROOT}/data/payments_dedupe_report.json", "w"), indent=1)
    print("latest 2026 check date", latest)


if __name__ == "__main__":
    main()
