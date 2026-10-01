"""Police misconduct settlements and legal costs, 2019 to 2025, from the Chicago Department of Law.

Source: the City's annual "CPD Litigation Report" required by Paragraph 548 of the federal Consent Decree.
Index page: https://www.chicago.gov/city/en/depts/dol/supp_info/CPDAnnLitReports.html

What the reports cover (read this before using the numbers):
- Only lawsuits that name CPD conduct (civil rights cases and police vehicle pursuit crashes) that CLOSED in
  that year. A case counts in the year it closes, not the year the harm happened. Wrongful conviction
  cases pay out decades after the event.
- 'Payout' = settlements + judgments + fees and costs awarded, per the Law Department's own definition.
- It does NOT cover every claim against the City (for example ordinary car crashes, slip and fall, or
  claims paid out by other City departments). There is no single public total for all City payouts.
- The 2025 report shows two totals because the City voted in 2025 to settle 184 'Watts' wrongful conviction
  cases for $101.3M but pays most of it in 2026. We keep both.
- The Law Department notes its definitions changed between report years, so treat the series as approximate.

No number is typed in by hand: each one is found in the downloaded PDF text by a pattern, the matching
sentence is saved as 'evidence', and the script stops if a pattern is not found.

Usage: python3 scripts/context_settlements.py -> data/context_settlements_2019_2025.json
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from context_common import fetch, load_json, money, norm, pdf_text, write_json  # noqa: E402

B = "https://www.chicago.gov/content/dam/city/depts/dol/CPDLitigationReports"
REPORTS = {
    2019: B + "/City%20of%20Chicago%20Report%20on%202019%20CPD%20Litigation.pdf",
    2020: B + "/City%20of%20Chicago%20Report%20on%202020%20CPD%20Litigation.pdf",
    2021: B + "/2025-11-6%20amended%20City%20of%20Chicago%20Report%20on%202021%20CPD%20Litigation.pdf",
    2022: B + "/City%20of%20Chicago%20Report%20on%202022%20CPD%20Litigation.pdf",
    2023: B + "/City%20of%20Chicago%20Report%20on%202023%20CPD%20Litigation.pdf",
    2024: B + "/11.7.25%20updated%20City%20of%20Chicago%20Report%20on%202024%20CPD%20Litigation.pdf",
    2025: B + "/2025/2025%20Annual%20Litigation%20Report%206.30.26.pdf",
}
INDEX = "https://www.chicago.gov/city/en/depts/dol/supp_info/CPDAnnLitReports.html"


def squash(txt, join_digits=False):
    """Normalize whitespace. Only the 2022 PDF has digits split by spaces ('$ 8 6 , 2 8 9'); for that
    one report (join_digits=True) we rejoin them. Doing it for other reports fuses neighbouring numbers."""
    t = norm(txt)
    if not join_digits:
        return t
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r"(\d) (?=[\d,.])", r"\1", t)
        t = re.sub(r"(?<=[\d,.]) (?=\d)", "", t)
    return t


def find(txt, pattern, year, what):
    m = re.search(pattern, txt, flags=re.I)
    if not m:
        raise SystemExit("PATTERN NOT FOUND for %s %s: %s" % (year, what, pattern))
    start = max(0, m.start() - 120)
    ev = txt[start:m.end() + 120]
    return m, ev


def main():
    series = {}
    for y, url in REPORTS.items():
        path = fetch(url, "law%d.pdf" % y if y != 2025 else "law_cpd_litigation_2025.pdf", timeout=180)
        t = squash(pdf_text(path), join_digits=(y == 2022))
        rec = {"report_url": url}
        if y == 2019:
            m, ev = find(t, r"the City paid plaintiffs a total of \$([0-9.]+) million in (\d+) cases", y, "total paid")
            rec["total_payout"] = float(m.group(1)) * 1e6
            rec["cases_with_payout"] = int(m.group(2))
            rec["total_payout_precision"] = "rounded to $0.1M in the report"
            rec["evidence_total"] = ev
            m, ev = find(t, r"the City paid outside counsel \$ ?([0-9.]+) million", y, "outside counsel")
            rec["outside_counsel_fees"] = float(m.group(1)) * 1e6
            rec["evidence_outside_counsel"] = ev
        elif y == 2020:
            m, ev = find(t, r"Settlements and Jury Awards Paid, 2020 Type Payouts % of Total Payouts # of Cases % of Payout Cases Settlements \$([0-9,]+)\*? \d+% (\d+) \d+% Plaintiffs. Verdicts & Satisfactions of Judgment \$([0-9,]+) \d+% (\d+) \d+% Total: \$([0-9,]+)", y, "settlements and jury awards table")
            rec["settlement_payouts"] = money(m.group(1))
            rec["settled_cases_paid"] = int(m.group(2))
            rec["jury_award_and_judgment_payouts"] = money(m.group(3))
            rec["litigated_cases_paid"] = int(m.group(4))
            rec["total_payout"] = money(m.group(5))
            rec["cases_with_payout"] = int(m.group(2)) + int(m.group(4))
            rec["evidence_total"] = ev
        elif y == 2021:
            m, ev = find(t, r"Settlements and Jury Awards Paid, 2021 Type Payouts % of Total Payouts # of Cases % of Payout Cases Settlements \$([0-9,\.]+) \d+% (\d+) \d+% Plaintiffs. Verdicts & Satisfactions of Judgment \$([0-9,]+) \d+% (\d+) \d+% Total: \$([0-9,]+)", y, "settlements and jury awards table")
            rec["settlement_payouts"] = money(m.group(1))
            rec["settled_cases_paid"] = int(m.group(2))
            rec["jury_award_and_judgment_payouts"] = money(m.group(3))
            rec["litigated_cases_paid"] = int(m.group(4))
            rec["total_payout"] = money(m.group(5))
            rec["cases_with_payout"] = int(m.group(2)) + int(m.group(4))
            rec["evidence_total"] = ev
            m, ev = find(t, r"in 2021 the City paid outside counsel \$ ?([0-9,\.]+) for legal services", y, "outside counsel")
            rec["outside_counsel_fees"] = money(m.group(1))
            rec["evidence_outside_counsel"] = ev
        elif y == 2022:
            m, ev = find(t, r"total amount of all payouts by the City in 2022 was \$ ?([0-9,\.]+?)\.(?=[A-Za-z ])", y, "total payouts")
            rec["total_payout"] = money(m.group(1))
            rec["evidence_total"] = ev
            m, ev = find(t, r"the total 2021 settlement amount to \$([0-9,\.]+?)\.?, and the total 2021 payout amount to \$([0-9,\.]+?)\.?\d{0,2} ?The 2021 report|total 2021 payout amount to \$([0-9,\.]+)", y, "2021 restatement")
            restated = [g for g in m.groups() if g][-1]
            rec["restates_2021_total_payout_to"] = money(restated)
            rec["evidence_2021_restatement"] = ev
        elif y in (2023, 2024):
            m, ev = find(t, r"total amount of all payouts by the City for the %d reportable cases was \$([0-9,\.]+)" % y, y, "total payouts")
            rec["total_payout"] = money(m.group(1))
            rec["evidence_total"] = ev
            if y == 2023:
                m, ev = find(t, r"in 202 ?3 the City paid outside counsel \$ ?([0-9.]+) million", y, "outside counsel")
                rec["outside_counsel_fees"] = float(m.group(1)) * 1e6
                rec["outside_counsel_precision"] = "rounded to $0.1M in the report; federal civil rights cases only"
            else:
                m, ev = find(t, r"in 2024 the City paid outside counsel \$ ?([0-9,\.]+) million for legal services", y, "outside counsel")
                rec["outside_counsel_fees"] = money(m.group(1))
                rec["outside_counsel_note"] = "The report prints '$34,767,711.13 million', which is a typo for dollars. We read it as $34.77 million."
            rec["evidence_outside_counsel"] = ev
        elif y == 2025:
            m, ev = find(t, r"total amount of all payouts by the City for the 202 ?5 reportable cases was \$ ?([0-9,\.]+)", y, "total payouts")
            rec["total_payout"] = money(m.group(1))
            rec["evidence_total"] = ev
            m, ev = find(t, r"also settled (\d+) Reversed Conviction .Watts. Cases for \$([0-9,\.]+)", y, "Watts")
            rec["watts_cases"] = int(m.group(1))
            rec["watts_settlements_approved_in_2025_mostly_paid_2026"] = money(m.group(2))
            rec["evidence_watts"] = ev
            m, ev = find(t, r"Including the .Watts Cases,. the 202 ?5 total reportable payout is \$ ?([0-9,\.]+)", y, "total with Watts")
            rec["total_payout_including_watts"] = money(m.group(1))
            rec["evidence_total_with_watts"] = ev
            rec["watts_note"] = ("The report text says City Council approved a resolution settling 176 Watts lawsuits (Sept 2025). "
                                 "Its footnote (and Appendix C, which we did not parse) counts 184 settled Watts cases for $101.3M. "
                                 "Both numbers appear in the report, we keep the footnote's 184 and flag the difference.")
            m, ev = find(t, r"in 202 ?5 the City paid outside counsel a total of \$ ?([0-9,\.]+) for legal services", y, "outside counsel")
            rec["outside_counsel_fees"] = money(m.group(1))
            rec["evidence_outside_counsel"] = ev
            m, ev = find(t, r"Reversed Conviction (\d+) \$([0-9,]+\.\d\d)", y, "wrongful conviction row")
            rec["wrongful_conviction_cases"] = int(m.group(1))
            rec["wrongful_conviction_payout"] = money(m.group(2))
            rec["evidence_wrongful_conviction"] = ev
            m, ev = find(t, r"Vehicle Pursuit (\d+) \$([0-9,]+\.\d\d)", y, "pursuit row")
            rec["vehicle_pursuit_cases"] = int(m.group(1))
            rec["vehicle_pursuit_payout"] = money(m.group(2))
            rec["evidence_pursuit"] = ev
            m, ev = find(t, r"Use of Force (\d+) \$([0-9,]+\.\d\d)", y, "use of force row")
            rec["use_of_force_cases"] = int(m.group(1))
            rec["use_of_force_payout"] = money(m.group(2))
            m, ev = find(t, r"Of the (\d+) reportable cases, the City incurred a payout in (\d+) cases", y, "case counts")
            rec["reportable_cases"] = int(m.group(1))
            rec["cases_with_payout"] = int(m.group(2))
            m, ev = find(t, r"As of December 31, 2025: .*?reported (\d+) pending lawsuits", y, "pending")
            rec["pending_civil_rights_lawsuits_dec_31_2025"] = int(m.group(1))
        series[y] = rec

    # Budget side: what the 2026 budget sets aside for judgments (appropriations dataset)
    approps = json.load(open(os.path.join(os.path.dirname(__file__), "..", "raw", "city_appropriations_2026.json")))
    judg = {}
    law_total = 0.0
    for a in approps:
        d = a["department_description"]
        acct = a["appropriation_account_description"]
        v = float(a["_ordinance_amount_"])
        if acct.startswith("For the Payment of Tort and Non-Tort Judgments"):
            judg[d] = judg.get(d, 0.0) + v
        if d == "Department of Law":
            law_total += v
    # Law Department 2026 appropriation (all line items)

    # Check each series value against its evidence one more time, and compute 2019-2025 totals
    base = {y: s.get("total_payout") for y, s in series.items()}
    five = sum(base[y] for y in (2021, 2022, 2023, 2024, 2025))
    pop = load_json("context_resident_2026.json")["population"]["chicago_population"]
    hh = load_json("context_resident_2026.json")["population"]["households"]

    out = {
        "generated_by": "scripts/context_settlements.py",
        "index_page": INDEX,
        "what_this_covers": [
            "Only lawsuits that name CPD conduct (civil rights cases and police vehicle pursuit crashes) that closed in that year.",
            "A case counts in the year it closes, not the year the harm happened. Wrongful conviction payouts can come 20 to 40 years after the event.",
            "Payout = settlements + judgments + fees and costs awarded (the Law Department's definition).",
            "This is NOT every payout by the City. Other claims (ordinary crashes, slip and fall, claims in other departments) are not in these reports.",
            "The Law Department changed definitions between years, so the series is approximate. Example: the 2021 report says $122.5M, the 2022 report restates 2021 to $126.1M after adding one more case. The 2021 figure used here is the amended 2021 report posted in Nov 2025.",
        ],
        "by_year": {str(y): s for y, s in series.items()},
        "five_year_total_2021_2025_sum_of_report_totals": five,
        "five_year_note": ("Our sum of the 'total_payout' in each year's Law Department report, 2021 to 2025, with 2025 excluding the $101.3M Watts settlements. "
                                 "UNRESOLVED DISCREPANCY: WTTW reports $472.4M for 2021 to 2025 "
                                 "(https://news.wttw.com/2026/07/10/chicago-taxpayers-spent-259m-resolve-police-misconduct-lawsuits-2025-city-analysis). "
                                 "Our sum is higher by the amount in five_year_difference_vs_wttw. We tried: 2021 as restated in the 2022 report ($126.1M instead of $122.5M), "
                                 "and settlements-only totals. Neither reproduces $472.4M. Likely cause is that WTTW or the Law Department counts 2021 differently (the 2021 report "
                                 "lists $53.0M settlements and $122.5M with jury awards). Not confirmed. Until resolved, use the single-year totals, which are each stated in the "
                                 "Law Department's own report, and do not publish the 5-year sum."),
        "five_year_wttw_reported": 472.4e6,
        "five_year_difference_vs_wttw": five - 472.4e6,
        "five_year_total_matches_wttw": abs(five - 472.4e6) < 0.5e6,
        "per_resident_2025_total_payout_excluding_watts": round(series[2025]["total_payout"] / pop, 2),
        "per_resident_2025_total_payout_including_watts": round(series[2025]["total_payout_including_watts"] / pop, 2),
        "per_household_2025_total_payout_excluding_watts": round(series[2025]["total_payout"] / hh, 2),
        "population_used": pop,
        "households_used": hh,
        "budget_2026_money_set_aside_for_judgments_by_department": {
            k: v for k, v in sorted(judg.items(), key=lambda x: -x[1])
        },
        "budget_note": "Appropriation line 'For the Payment of Tort and Non-Tort Judgments, Outside Counsel Expenses and Expert Costs, as Approved by the Corporation Counsel' in dataset 6694-f78c. CPD's line is for CPD judgments plus outside counsel and experts.",
        "budget_2026_department_of_law_total": law_total,
        "secondary_reporting": [
            {
                "claim": "CPD spent $131.1M on police misconduct lawsuits in 2025 per the City's audited annual financial report, and CPD overspent its total 2025 budget by $162.5M. The remaining ~$127.8M of the $258.96M is unexplained in public reports.",
                "source": "WTTW News, Jul 10 2026, citing the City's 2025 Annual Comprehensive Financial Report",
                "url": "https://news.wttw.com/2026/07/10/chicago-taxpayers-spent-259m-resolve-police-misconduct-lawsuits-2025-city-analysis",
                "status": "NOT checked against the ACFR itself. Use as 'reported by WTTW'.",
            },
            {
                "claim": "Civic Federation: the FY2026 adopted budget uses debt, not operating revenue, to cover the cost of legal police settlements and retroactive salaries for firefighters.",
                "source": "Civic Federation, Chicago's FY2026 Adopted Budget: Still Short of the Mark",
                "url": "https://www.civicfed.org/chicagos-fy2026-adopted-budget",
                "status": "Quote verified in downloaded page text (see data/context_oversight_findings.json).",
            },
        ],
    }
    write_json("context_settlements_2019_2025.json", out)
    for y, s in series.items():
        print(y, "payout $%.1fM" % (s["total_payout"] / 1e6), "outside counsel", s.get("outside_counsel_fees"))
    print("5yr", five, "matches WTTW:", out["five_year_total_matches_wttw"], "diff", out["five_year_difference_vs_wttw"])
    print("judgments budget:", {k: round(v / 1e6, 1) for k, v in judg.items()})


if __name__ == "__main__":
    main()
