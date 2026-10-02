#!/usr/bin/env python3
"""Build data/splits/city/aviation_awards.json: more FAA award detail for the two AIP carryover lines, plus the airport
capital program (O'Hare 21 and Midway CIP) as side facts on the airport bond lines.

Run:  python3 scripts/aviation_awards_build.py            (uses cached raw/aviation/*, fetches what is missing)
      python3 scripts/aviation_awards_build.py --refresh  (re-pull award funding histories from USASpending.gov)
Then: python3 build/city_tree.py   (every split must show applied, 0 skipped)

This file is the companion of scripts/aviation_build.py (which owns data/splits/city/aviation.json and runs first,
because split files apply in file name order). Nothing here edits that file. It reads it only to know which FAA
awards are already named, so that no award is counted twice and the new pieces fit in the leftover residual boxes.

What it writes (research/aviation_awards.md has sources, checks and gaps):
 1. Residual box "Carryover not tied to a named FAA award" under 925F-2810-909A (O'Hare, 311.7M): FAA awards that were
    still open on 2026-01-01 and had unspent money on the carryover date (Aug 1 2025, the date the Budget Book says
    carryover is calculated) but are not named in aviation.json. Every piece fits inside the residual.
 2. Same for Midway 925F-2805-909A (99.8M). The rule finds no further award, so that one is side info only.
    Both get a side list of every named award's unspent balance on the carryover date and the IIJA facts.
 3. O'Hare 2026B bond lines (0740-2005-0902 and 0912): capital program cost table, funding sources by program, AULA
    project list with completion years, significant CIP projects. Midway 2023A line: 2023 Airport Projects table
    and the 2023-2027 CIP cost and funding tables.
Nothing is scaled. Never invents numbers.
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "raw", "aviation")
OUT = os.path.join(ROOT, "data", "splits", "city", "aviation_awards.json")
AWARDS = os.path.join(RAW, "faa_awards_usaspending.json")
FUNDING = os.path.join(RAW, "faa_award_funding.json")
AVIATION_JSON = os.path.join(ROOT, "data", "splits", "city", "aviation.json")

ZIP_AIRPORT = {"60666": "ORD", "60638": "MDW"}
AIP_ALN = {"20.106", "20.116"}
CARRYOVER_CUT = (2025, 10)      # USASpending reporting period: FY2025 month 10 = July 2025 (federal FY starts in October)
CARRYOVER_DATE = "2025-08-01"   # Summary G: "Carryover appropriations are calculated at a point in time: August 1 of the prior budget fiscal year"
OPEN_ON = "2026-01-01"          # same rule as aviation.json: the award must still be open in the budget year
ORD_RESERVE = 411_790_000
MDW_RESERVE = 123_869_000

ID_ORD = "city.infrastructure-services.chicago-department-of-aviation.grant-money-not-yet-assigned-to-projects.925f-federal-grant-fund.925f-2810-909a.other-not-itemised"
ID_MDW = "city.infrastructure-services.chicago-department-of-aviation.grant-money-not-yet-assigned-to-projects.925f-federal-grant-fund.925f-2805-909a.other-not-itemised"

SRC_BOOK = {"doc": "Mayor's Budget Recommendations for Year 2026, Summary G (grant funds)",
            "url": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Recommendations.pdf"}
SRC_OS_CD = {"doc": "O'Hare General Airport Senior Lien Revenue Refunding Bonds 2026C and 2026D, Official Statement dated 2026-08-21 (Appendix E, Report of the Airport Consultant)",
             "url": "https://bondlink-cdn.com/1348/ILChicago07a-FIN.1Lay3BJv8.pdf", "file": "raw/bonds/ohare_2026CD_OS.pdf"}
SRC_OS_B = {"doc": "O'Hare General Airport Senior Lien Revenue and Revenue Refunding Bonds 2026B, Official Statement (Appendix E, Report of the Airport Consultant, July 2026)",
            "url": "https://bondlink-cdn.com/1348/ILChicago06a-FIN.MLCK3FoI1.pdf", "file": "raw/bonds/ohare_2026B_OS.pdf"}
SRC_MDW = {"doc": "Chicago Midway Airport Senior Lien Revenue and Revenue Refunding Bonds 2025A and 2025B, Official Statement (includes the October 2023 Report of the Airport Consultant and a 2025 update letter)",
           "url": "https://bondlink-cdn.com/1351/Official-Statement.02duRik1H.pdf", "file": "raw/bonds/midway_2025AB_OS.pdf"}


def src(base, page, note=None):
    d = dict(base)
    d["page"] = page
    if note:
        d["note"] = note
    return d


# ---------------------------------------------------------------- USASpending
def curl_json(url, body):
    cmd = ["curl", "-s", "-m", "90", "-A", "Mozilla/5.0", url, "-H", "Content-Type: application/json", "-d", json.dumps(body)]
    for _ in range(3):
        r = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except Exception:
            time.sleep(2)
    raise SystemExit("failed " + url)


def fetch_funding(awards):
    """Per award: every reporting-period record (obligations and gross outlays by federal account) from USASpending."""
    out = {}
    for a in awards:
        rows, page = [], 1
        while True:
            r = curl_json("https://api.usaspending.gov/api/v2/awards/funding/",
                          {"award_id": a["generated_internal_id"], "limit": 100, "page": page,
                           "sort": "reporting_fiscal_date", "order": "asc"})
            rows += r.get("results", [])
            if not r.get("page_metadata", {}).get("hasNext"):
                break
            page += 1
        out[a["award_id"]] = rows
        time.sleep(0.1)
    json.dump(out, open(FUNDING, "w"))
    return out


def as_of(rows, cut):
    """Obligated and outlaid dollars on the books through reporting period `cut` (fiscal year, fiscal month).
    Outlays are cumulative per account line, so the latest report per line counts; obligations are summed."""
    ob, last = 0.0, {}
    for r in rows:
        t = (r["reporting_fiscal_year"], r["reporting_fiscal_month"])
        if t > cut:
            continue
        ob += r["transaction_obligated_amount"] or 0.0
        if r["gross_outlay_amount"] is not None:
            key = (r["federal_account"], r["object_class"], r["disaster_emergency_fund_code"])
            if key not in last or t >= last[key][0]:
                last[key] = (t, r["gross_outlay_amount"])
    return ob, sum(v[1] for v in last.values())


def r2(x):
    return round(float(x), 2)


PROGRAM = {"069-8106": "Airport Improvement Program (entitlement or discretionary)", "069-1338": "IIJA Airport Infrastructure Grants",
           "069-1337": "IIJA Airport Terminal Program", "069-2815": "COVID relief for airports (CRRSA and ARPA)"}


def project_phrase(desc):
    import re
    m = re.match(r"PURPOSE:\s*([^.]+)\.", desc or "")
    return (m.group(1).strip().capitalize() if m else "Airport improvement (older FAA record gives no project text)")


def faa_grant_numbers():
    """FAIN -> FAA grant number, from the FAA workbooks via the first-pass script (read only)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("aviation_build", os.path.join(ROOT, "scripts", "aviation_build.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {k: v["grant_number"] for k, v in mod.faa_workbook_index().items()}


def named_award_ids():
    names = {}
    for s in json.load(open(AVIATION_JSON))["splits"]:
        for p in s.get("pieces", []):
            e = p.get("extra") or {}
            if e.get("award_id"):
                names[e["award_id"]] = p["name"]
    return names


def main():
    refresh = "--refresh" in sys.argv
    awards = json.load(open(AWARDS))["awards"]
    if refresh or not os.path.exists(FUNDING):
        funding = fetch_funding([a for a in awards if ZIP_AIRPORT.get(a["zip5"])])
    else:
        funding = json.load(open(FUNDING))
    named = named_award_ids()
    idx_gn = faa_grant_numbers()
    splits = []

    snap = {"ORD": [], "MDW": []}
    for a in awards:
        ap = ZIP_AIRPORT.get(a["zip5"])
        if not ap or a["recipient"] != "CITY OF CHICAGO" or not (set(a.get("aln") or []) & AIP_ALN):
            continue
        if a["start"] > CARRYOVER_DATE or a["award_id"] not in funding:
            continue
        ob, out = as_of(funding[a["award_id"]], CARRYOVER_CUT)
        unspent = ob - out
        if unspent <= 1:
            continue
        accts = sorted({r["federal_account"] for r in funding[a["award_id"]]})
        snap[ap].append({"a": a, "unspent": unspent, "named": a["award_id"] in named, "open": a["end"] >= OPEN_ON,
                         "program": ", ".join(PROGRAM.get(x, x) for x in accts)})
    for ap in snap:
        snap[ap].sort(key=lambda s: -s["unspent"])

    def snapshot_side(ap, reserve):
        rows = []
        for s in snap[ap]:
            a = s["a"]
            tag = ("already a named box above (shown there at today's balance)" if s["named"] else
                   ("a new named box above" if s["open"] else "grant period ended before 2026, so not treated as 2026 carryover"))
            rows.append({"kind": "carryover_date_balance",
                         "label": f"Unspent on FAA award {a['award_id']} on {CARRYOVER_DATE}: {project_phrase(a['description'])} ({s['program']}), {tag}",
                         "amount": r2(s["unspent"]), "period": f"balance on {CARRYOVER_DATE}", "basis": "published",
                         "source": {"doc": "USASpending.gov award record, award funding history (Treasury account data)", "url": a["usaspending_url"],
                                    "note": "obligations minus gross outlays reported through July 2025 (federal fiscal year 2025, period 10). Agencies report outlays late, so older awards can look more unspent than they were."}})
        tot = sum(s["unspent"] for s in snap[ap])
        rows.append({"kind": "carryover_date_total", "label": f"All unspent money on {ap} FAA awards on {CARRYOVER_DATE}, added up (the budget carried {reserve:,.0f})",
                     "amount": r2(tot), "period": f"balance on {CARRYOVER_DATE}", "basis": "published",
                     "source": {"doc": "USASpending.gov award funding histories (raw/aviation/faa_award_funding.json), summed by scripts/aviation_awards_build.py"}})
        return rows, tot

    # ------------------------------------------------ 1. O'Hare carryover residual
    side_ord, tot_ord = snapshot_side("ORD", ORD_RESERVE)
    pcs = []
    for s in snap["ORD"]:
        a = s["a"]
        if s["named"] or not s["open"]:
            continue
        f = funding[a["award_id"]]
        pcs.append({
            "name": f"{project_phrase(a['description'])} (FAA grant {a['award_id']})", "amount": r2(s["unspent"]), "basis": "gov_estimate", "kind": "grant_award",
            "source": {"doc": "USASpending.gov award record and award funding history", "url": a["usaspending_url"]},
            "why": ("The FAA promised this money to the City for one airport project. On the day the budget counted carryover the City had not yet been paid "
                    "any of it, so the whole grant was waiting to be used."),
            "note": (f"Award {a['award_id']} ({s['program']}): {a['total_obligation']:,.2f} awarded, period {a['start']} to {a['end']}. The box is the unspent balance on "
                     f"{CARRYOVER_DATE} (obligated minus gross outlays reported through July 2025), because that is the date the Budget Book uses to calculate carryover. "
                     f"Treasury has since reported gross outlays of {funding_out(f):,.2f} (through the latest report in the file), so little may be left to pay today. "
                     "The first pass named only awards with money still unspent today, so this one was missing. "
                     + (f"FAA grant history lists it as {idx_gn[a['award_id']]}. " if a["award_id"] in idx_gn else "")),
            "extra": {"award_id": a["award_id"], "obligation": r2(a["total_obligation"]), "balance_date": CARRYOVER_DATE, "period_start": a["start"], "period_end": a["end"]}})
    tot_new = sum(p["amount"] for p in pcs)
    residual_ord = ORD_RESERVE - sum_named_pieces("2810", "909A")
    assert tot_new <= residual_ord, (tot_new, residual_ord)
    side_ord += [
        {"kind": "iija_allocation", "label": "IIJA Airport Infrastructure Grants allocated to O'Hare for federal fiscal years 2022 to 2026 (about $73.7M, $73.4M, $69.6M, $63.9M, $66.0M, added up from the printed figures)",
         "amount": 346_600_000, "period": "FFY2022 to FFY2026", "basis": "published", "source": src(SRC_OS_CD, "301 (E-137) and 71", "text says $346.6 million allocated through August 2026")},
        {"kind": "iija_atp", "label": "IIJA Airport Terminal Program discretionary grants awarded to O'Hare ($50.0M FFY23, $40.0M FFY24, $20.0M FFY25)",
         "amount": 110_000_000, "period": "FFY2023 to FFY2025", "basis": "published", "source": src(SRC_OS_CD, "71 and 301 (E-137)")},
        {"kind": "faa_loi", "label": "FAA Letter of Intent LOI AGL-10-01 discretionary grants for O'Hare Modernization (total, $605.0M received by July 2026, final $20.0M payment is for federal fiscal year 2026 and goes to Series 2016E bond debt service)",
         "amount": 625_000_000, "period": "FFY2011 to FFY2026", "basis": "published", "source": src(SRC_OS_CD, "300 (E-136) and 190 (E-26, footnote 20)")},
        {"kind": "budget_book_bil_line", "label": "Summary G also lists 925F-2827 DOT - FAA - Airport Improvement Program - O'Hare (BIL) (20.106) with $90,000,000 anticipated for 2026 and no carryover. The ordinance data has no row for it, so it is not a box in this tree.",
         "amount": 90_000_000, "period": "2026 budget", "basis": "published", "source": src(SRC_BOOK, "607 (PDF 616)")},
        {"kind": "faa_fy2026_awards_listed_elsewhere", "label": "FAA awards made in August and September 2026 (including $83.3M of IIJA Airport Infrastructure Grants under ALN 20.117) are listed on the 'professional and technical services' O'Hare grant line, not here. They were awarded after the August 2025 carryover date, so they cannot be part of this carryover.",
         "amount": 83_314_240, "period": "awarded 2026-09", "basis": "actual",
         "source": {"doc": "USASpending.gov awards 31700222072026, 31700222092026, 31700222102026 (ALN 20.117, sum of obligations)", "url": "https://www.usaspending.gov/"}}]
    splits.append({
        "target": {"by": "id", "id": ID_ORD}, "mode": "budget_split", "pieces": pcs,
        "residual": {"name": "Still not tied to any FAA award, even on the carryover date",
                     "why": ("The budget carries this much federal airport grant money over from earlier years. Federal records show awards with unspent money on the day the carryover was counted, "
                             "but they explain only about a third of it. No public record ties the rest to a project.")},
        "note": (f"Second pass on this box. Unspent money on every named O'Hare FAA award on {CARRYOVER_DATE} (the date the Budget Book says carryover is counted) adds up to "
                 f"${tot_ord:,.0f}, against the ${ORD_RESERVE:,.0f} carried. Awards made after that date, the IIJA 2026 awards, expired grants, and awards already named in the first pass are not repeated."),
        "side": side_ord})

    # ------------------------------------------------ 2. Midway carryover residual (side only: no further award qualifies)
    side_mdw, tot_mdw = snapshot_side("MDW", MDW_RESERVE)
    mdw_new = [s for s in snap["MDW"] if not s["named"] and s["open"]]
    assert not mdw_new, "a Midway award qualifies: build pieces for it"
    side_mdw += [
        {"kind": "iija_allocation", "label": "IIJA Airport Infrastructure Grants allocated to Midway for federal fiscal years 2022 to 2025 (FFY2022 $20.3M, FFY2023 $20.2M, FFY2024 $20.3M, FFY2025 $20.1M)",
         "amount": 80_800_000, "period": "FFY2022 to FFY2025", "basis": "published", "source": src(SRC_MDW, "159 and 67")},
        {"kind": "aip_entitlement", "label": "AIP entitlement grants allocated to Midway for federal fiscal years 2022 to 2025",
         "amount": 19_000_000, "period": "FFY2022 to FFY2025", "basis": "published", "source": src(SRC_MDW, "159")},
        {"kind": "project_funding", "label": "Runway 13C-31C pavement rehabilitation: IIJA AIG funds applied",
         "amount": 28_200_000, "period": "FFY2022 to FFY2025", "basis": "published", "source": src(SRC_MDW, "159")},
        {"kind": "project_funding", "label": "Runway 13C-31C pavement rehabilitation: AIP entitlement funds applied",
         "amount": 9_600_000, "period": "FFY2022 to FFY2025", "basis": "published", "source": src(SRC_MDW, "159")},
        {"kind": "faa_fy2026_awards_not_placed", "label": "Two Midway IIJA Airport Infrastructure Grants (ALN 20.117, Reconstruct taxiway $8,646,553 and Reconstruct terminal $12,763,682) were awarded in September 2026, after the August 2025 carryover date. No Midway budget line carries IIJA money, so they sit in no box. The 2026 Midway AIP awards (ALN 20.116) are boxes on the Midway 'professional and technical services' grant line.",
         "amount": 21_410_235, "period": "awarded 2026-09", "basis": "actual",
         "source": {"doc": "USASpending.gov awards 31700251122026 and 31700251132026 (ALN 20.117)", "url": "https://www.usaspending.gov/award/ASST_NON_31700251132026_069"}}]
    splits.append({
        "target": {"by": "id", "id": ID_MDW}, "mode": "side_only",
        "note": (f"No further Midway FAA award both had unspent money on {CARRYOVER_DATE} and was still open in 2026, beyond the ones already named above. Unspent money on every named Midway FAA award on that date "
                 f"adds up to ${tot_mdw:,.0f}, against the ${MDW_RESERVE:,.0f} carried. The side list shows each award's balance that day, including four whose grant period ended before 2026."),
        "side": side_mdw})

    # ------------------------------------------------ 3. Capital program side facts
    ps1 = src(SRC_OS_CD, "184 (E-20, Table S-1) and 210 (E-46, Table 2-2)")
    cap = []
    for lab, tot, prev, b26, fut, oth in (
            ("TAP Phase 1 elements (O'Hare Global Terminal, Concourses D and E, tunnel, baggage, Terminal 5)", 9_826_217, 2_937_130, 695_305, 6_193_783, 0),
            ("Pre-approved capital improvement projects", 1_925_810, 1_352_816, 130_828, 442_166, 0),
            ("Pre-approved allowances and infrastructure reliability", 768_157, 96_291, 45_659, 26_207, 600_000),
            ("Ongoing projects from earlier agreements", 209_218, 149_842, 18_598, 40_778, 0),
            ("New approvals since the 2018 airline agreement", 1_493_760, 957_552, 111_010, 425_198, 0),
            ("Proposed projects", 403_952, 44_144, 3_259, 356_549, 0),
            ("Total airport capital program", 14_627_114, 5_537_774, 1_004_658, 7_484_681, 600_000)):
        cap.append({"kind": "capital_program_funding",
                    "label": f"{lab}: total cost in escalated dollars (of which already funded ${prev * 1000:,.0f}, paid by the 2026B bonds ${b26 * 1000:,.0f}, to be paid by future bonds ${fut * 1000:,.0f}, other (airline fees) ${oth * 1000:,.0f})",
                    "amount": tot * 1000, "period": "program to 2035", "basis": "published", "source": ps1})
    cap.append({"kind": "capital_program_funding", "label": "Executed grant funding already counted inside 'already funded' (about $290.1M). The financial analysis assumes no future grants: new grants would reduce future bonds.",
                "amount": 290_100_000, "period": "to July 2026", "basis": "published", "source": src(SRC_OS_CD, "184 (E-20, note 3) and 209 (E-45)")})
    exh_l = [("Central detention basin elimination and south basin expansion", 223_000, 0, "2026"),
             ("Concourse D (Satellite 1)", 730_000, 0, "2028"),
             ("Concourse E (Satellite 2), north portion 2030 and south portion 2034", 527_000, 0, "2030 and 2034"),
             ("Concourse L 3-gate expansion", 25_063, 28_763, "complete 2025"),
             ("Terminal 5 landside and parking, phase 1 (stage 1 garage complete 2024, stage 2 2029)", 222_000, 0, "2029"),
             ("Consolidated people mover, pedestrian and utility tunnel (phase 1)", 665_000, 0, "2035"),
             ("Baggage handling system equipment", 825_000, 0, "2033"),
             ("Terminal 2 redevelopment: O'Hare Global Terminal and Global Concourse", 1_830_000, 0, "2033"),
             ("Terminal 5 repurposing and core expansion", 250_000, 0, "2029"),
             ("TAP phase 1 utilities allowance", 493_000, 0, "2033"),
             ("Western parking and screening facilities allowance", 215_000, 0, "2030"),
             ("Concourse L 5-gate buyout", 78_000, 0, "complete 2018")]
    assert sum(a + b for _, a, b, _ in exh_l) == 6_111_826
    ps2 = src(SRC_OS_CD, "207 (E-43, Table 2-1)", "2018 dollars, unescalated, includes contingency and management reserve spread across projects by the airport consultant")
    for lab, a, b, yr in exh_l:
        cap.append({"kind": "capital_project_2018", "label": f"AULA Exhibit L: {lab} (approval ${a * 1000:,.0f}" + (f" plus ${b * 1000:,.0f} added later" if b else "") + f"), estimated completion {yr}",
                    "amount": (a + b) * 1000, "period": "approved 2018, 2018 dollars", "basis": "published", "source": ps2})
    cap += [{"kind": "capital_project_2018", "label": "AULA Exhibit N: remaining O'Hare Modernization airfield projects (complete 2021)", "amount": 334_443_000, "period": "2018 dollars", "basis": "published", "source": ps2},
            {"kind": "capital_project_2018", "label": "AULA Exhibit N: capital improvement projects (ongoing)", "amount": 1_352_032_000, "period": "2018 dollars", "basis": "published", "source": ps2},
            {"kind": "capital_project_2018", "label": "AULA Exhibit O: pre-approved allowances ($40 million a year, paid from airport fees and charges)", "amount": 600_000_000, "period": "2018 dollars", "basis": "published", "source": ps2},
            {"kind": "capital_project_2018", "label": "AULA Exhibit O: infrastructure reliability allowance (ongoing)", "amount": 168_157_000, "period": "2018 dollars", "basis": "published", "source": ps2},
            {"kind": "capital_project_2018", "label": "Total airline agreement funding approval, all exhibits", "amount": 8_566_458_000, "period": "2018 dollars", "basis": "published", "source": ps2}]
    ps3 = src(SRC_OS_CD, "215 (E-51)", "unescalated dollars, 'significant ongoing projects included in the CIP'")
    for lab, amt in (("Vehicle acquisition, high-speed runway equipment", 99_100_000), ("Full core terminal virtual ramp control", 48_800_000),
                     ("Taxiway N reconstruction", 59_900_000), ("Taxiway V reconstruction", 91_100_000), ("Grade separated roads", 282_300_000),
                     ("Terminal 3 improvements (ElevateT3)", 305_700_000), ("Terminal 3 city equipment", 76_900_000)):
        cap.append({"kind": "capital_project_cip", "label": f"Capital improvement program project: {lab}", "amount": amt, "period": "ongoing, unescalated", "basis": "published", "source": ps3})
    cap += [{"kind": "bond_uses", "label": "2026B bonds (new money part only): par amount $1,185.9M, deposit to project fund", "amount": 1_004_400_000, "period": "2026", "basis": "published", "source": src(SRC_OS_B, "184 (E-30, Table 1-2)")},
            {"kind": "bond_uses", "label": "2026B bonds (new money part only): deposit to capitalized interest accounts (interest paid from bond money, not from airport revenue)", "amount": 134_900_000, "period": "2026", "basis": "published", "source": src(SRC_OS_B, "184 (E-30, Table 1-2)")},
            {"kind": "bond_uses", "label": "2026B bonds (new money part only): deposit to common debt service reserve", "amount": 63_500_000, "period": "2026", "basis": "published", "source": src(SRC_OS_B, "184 (E-30, Table 1-2)")},
            {"kind": "bond_uses", "label": "2026B bonds (new money part only): cost of issuance", "amount": 9_500_000, "period": "2026", "basis": "published", "source": src(SRC_OS_B, "184 (E-30, Table 1-2)")}]
    splits.append({"target": {"by": "id", "id": "city.loans.chicago-o-hare-airport-fund.0740-2005-0902.o-hare-2026b"}, "expect_amount": 1_825_655, "mode": "side_only",
                   "note": ("This bond's new money (about $1.0 billion) pays for part of the O'Hare capital program (O'Hare 21 and other projects). The side list shows the program's cost, who pays for what, "
                            "the approved project list with completion years, and how the bond money is used. The bond is not tied to single projects: the airport consultant states only the total share by program."),
                   "side": cap})
    splits.append({"target": {"by": "id", "id": "city.loans.chicago-o-hare-airport-fund.0740-2005-0912.o-hare-2026b"}, "expect_amount": 1_410_000, "mode": "side_only",
                   "note": "Principal on the 2026B bonds. See the interest line of the same bond for the capital program tables and the 2026B sources and uses.",
                   "side": [{"kind": "bond_uses", "label": "2026B bonds (new money part only): deposit to project fund, which pays for part of the airport capital program", "amount": 1_004_400_000,
                             "period": "2026", "basis": "published", "source": src(SRC_OS_B, "184 (E-30, Table 1-2)")}]})

    mw = []
    ps4 = src(SRC_MDW, "212 (E-34, Table 2-1)", "Chicago Department of Aviation, October 2023, thousands of dollars in the source")
    for lab, tot, ser in (("Fuel farm garage and upgrades", 4_000, 4_000), ("Restrooms modernization", 22_585, 6_115),
                          ("Baggage handling system and checked bag inspection system elements", 36_520, 28_838), ("Holdroom carpet replacement", 1_800, 1_800),
                          ("Passenger loading bridge refresh", 9_385, 9_385), ("North CBIA matrix recapitalization and optimization", 1_800, 1_385),
                          ("Project implementation", 16_500, 8_150)):
        mw.append({"kind": "capital_project", "label": f"2023 Airport Project: {lab} (cost ${tot * 1000:,.0f}, of which paid by the Series 2023 bonds ${ser * 1000:,.0f})",
                   "amount": tot * 1000, "period": "2023 to 2027", "basis": "published", "source": ps4})
    mw.append({"kind": "capital_project", "label": "2023 Airport Projects total cost (the Series 2023 bonds pay $59,672,000 of it; the table's own parts add to $59,673,000 because of rounding)",
               "amount": 92_590_000, "period": "2023 to 2027", "basis": "published", "source": ps4})
    ps5 = src(SRC_MDW, "213 (E-35, Table 2-2)", "printed in millions of dollars")
    for lab, amt in (("Airfield (mostly Runway 13C-31C, Runway 4R-22L, Taxiway Y, apron pavement)", 216.9), ("Terminal (restrooms, baggage systems, loading bridges, carpet)", 57.2),
                     ("Parking and roadway", 8.8), ("Facilities, fuel, vehicles", 88.0), ("Land and property acquisition", 23.6), ("Residential noise mitigation (about 2,020 homes)", 119.8)):
        mw.append({"kind": "capital_program_cost", "label": f"2023 to 2027 capital improvement program cost: {lab}", "amount": round(amt * 1_000_000), "period": "2023 to 2027", "basis": "published", "source": ps5})
    ps6 = src(SRC_MDW, "214 (E-36, Table 2-3)", "printed in millions of dollars. Assumes grant funding for about 60 percent of noise mitigation projects")
    for lab, amt in (("Previously issued senior lien revenue bonds", 137.2), ("FAA AIP grants", 63.7), ("Series 2023 bonds", 59.7), ("Future bonds (assumed 2025 issue, level debt service 2036 to 2055)", 253.7), ("Total", 514.3)):
        mw.append({"kind": "capital_program_funding", "label": f"2023 to 2027 capital improvement program paid by: {lab}", "amount": round(amt * 1_000_000), "period": "2023 to 2027", "basis": "published", "source": ps6})
    splits.append({"target": {"by": "id", "id": "city.loans.chicago-midway-airport-fund.bonds.midway-2023a"}, "expect_amount": 17_850_013, "mode": "side_only",
                   "note": ("The Series 2023A bonds put $59.7 million into the project fund for the 'Midway 2023 Airport Projects'. The side list shows those projects and the 2023 to 2027 Midway capital program by cost and by who pays. "
                            "The consultant's report dates from October 2023, so the amounts are plans from then."),
                   "side": mw})

    meta = {"author": "deep: O'Hare & Midway awards and capital tables", "built_by": "scripts/aviation_awards_build.py",
            "description": ("Second pass on the FAA AIP carryover lines (awards with unspent money on the Aug 1 2025 carryover date not named in aviation.json), plus the O'Hare and Midway "
                            "capital program tables as side facts on the airport bond lines. See research/aviation_awards.md."),
            "carryover_snapshot": {ap: [{"award": s["a"]["award_id"], "unspent": r2(s["unspent"]), "named_in_aviation_json": s["named"], "open_2026": s["open"]} for s in snap[ap]] for ap in snap}}
    json.dump({"meta": meta, "splits": splits}, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: {len(splits)} splits")
    print(f"  ORD new named pieces {len(pcs)} total {tot_new:,.2f} inside residual {residual_ord:,.2f}; carryover-date balances {tot_ord:,.2f} vs reserve {ORD_RESERVE:,}")
    print(f"  MDW new named pieces 0; carryover-date balances {tot_mdw:,.2f} vs reserve {MDW_RESERVE:,}")


def funding_out(rows):
    """Gross outlays reported to date (latest report per account line)."""
    return as_of(rows, (9999, 99))[1]


def sum_named_pieces(authority, account):
    """Total of the named pieces in aviation.json for a reserve line (so the residual left for this file is known)."""
    for s in json.load(open(AVIATION_JSON))["splits"]:
        t = s["target"]
        if t.get("authority") == authority and t.get("account") == account and t.get("fund") == "925F":
            return sum(p["amount"] for p in s.get("pieces", []))
    raise SystemExit("reserve split not found in aviation.json")


if __name__ == "__main__":
    main()
