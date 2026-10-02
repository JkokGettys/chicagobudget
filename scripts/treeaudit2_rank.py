"""Audit 2, part 5: tag every remaining dead end (leaf of $10M or more, not a count x rate box under $1M) as
  (a) public data unused: a public source we hold or can fetch would split it,
  (b) needs FOIA or the budget office (OBM): no public source says how it splits,
  (c) truly one item: one payment, one contract, one bond series, one planned offset, or money not spent yet.
Rules are ordered regexes on the box path and name (first match wins). Unmatched boxes default to (b) and are counted as 'default'
so the report can say how much of each total rests on an explicit rule. Reads raw/treeaudit2/deadends_<gov>.json (from treeaudit2_deadends.py),
writes raw/treeaudit2/rank.json and prints the markdown tables used in research/tree_gap_audit_2.md."""
import json, re, collections
from treeaudit2_common import *

# (regex on 'path | name', tag, short reason, source or next step)
CITY = [
 (r"Carryover not tied to a named FAA|Still not tied to any FAA|2026 grant money not yet awarded", "b", "federal airport carryover no public record ties to a project", "Ask Aviation/OBM for the AIP grant ledger by award. FAA FY2026 grant history is not published yet"),
 (r"Paid beyond the budget line|Already spent more than", "c", "payments so far are larger than the budget line, shown as a negative box", "note on the box explains it"),
 (r"obm-unexplained|no line explains", "b", "OBM deduction no line explains", "Ask OBM how the $117.0M is figured"),
 (r"Extra payment above what the law requires|One extra payment|Two extra payments|Advance payment", "c", "one extra payment into a pension fund", "none, it is one payment"),
 (r"Budgeted but not spent yet", "c", "money not spent yet, so no payment exists", "revisit when more of 2026 is paid"),
 (r"vacancy savings|Budgeted turnover|Less Corporate Fund Savings", "c", "planned saving that offsets pay lines", "none"),
 (r"Wrongful conviction|Watts global|Police vehicle chase|settlements", "c", "settlement payments, each a separate court deal (cases involve private people)", "Law Dept report lists cases, privacy stops further detail"),
 (r"Scheduled Wage Adjustments", "b", "set aside for union contracts not yet settled, and the 2026 line is 9.3x last year's matching pay, so no public split fits", "Ask OBM for the contract settlement schedule. 2025 pay by title (dawh-m56b) is already side info"),
 (r"Overtime|Duty Availability|Compensatory Time|Uniform Allowance|Specialty Pay|Holiday Premium|Furlough/Supervisors", "c", "one job title's share of a pay line (further detail is individual workers)", "none"),
 (r"Rest of police overtime", "b", "CPD publishes targets for part of its overtime, not the rest", "Ask CPD/OBM for overtime by unit and event"),
 (r"local sewer x|CDBG-DR", "b", "disaster recovery plan has miles and a unit cost, streets not picked", "HUD DRGR quarterly reports are a lead (not checked)"),
 (r"Federal highway money with no project|Rebuild Illinois money with no project|State grant money with no project|Reserve not matched to a project|Other / not itemised", "b", "reserve larger than any public project list", "Ask CDOT/OBM for reserve by project. FHWA FMIS and IDOT e-Project are leads (not checked)"),
 (r"State/Lake|Rest of the federal award", "b", "one federal award, station cost breakdown not published", "FTA TrAMS line items for IL-2016-002 (not reached), or ask CDOT"),
 (r"Emergency Medical Transportation", "b", "use of line unconfirmed", "FOIA Finance for ledger of account 9222, or HFS invoices"),
 (r"Other bonds \(not printed|Rest of the older bonds|Series 2010B|Water 2017|interest left in residual|Midway.*Other bonds", "a", "bond series share not printed in the statements we hold", "EMMA official statements and trustee schedules https://emma.msrb.org/ (document downloads need a browser)"),
 (r"For Interest on Bonds|For Payment of Bonds|Bonds: interest and principal together|O'Hare 20|Midway 20|Sewer 20|Water 20|GO 20|GO Taxable|GO Refunding|Sewer 1998A", "c", "one bond series, interest or principal", "none, one series is the finest level"),
 (r"For Payment of Bonds", "c", "internal transfer that pays general bonds", "none"),
 (r"For Payment on Loans|For Interest on Loans|IEPA", "a", "state revolving loans, one public list per loan", "Illinois EPA loan lists (lead, not checked)"),
 (r"Electricity|Natural Gas|Gasoline", "b", "a few energy suppliers are paid (Constellation NewEnergy $55.2M to 9/28), but payments carry no fund or line, so they cannot be placed", "OBM Mid-Year 'Data Directory' extract, or FOIA Asset Management bills by account"),
 (r"Capital Construction", "a", "water and sewer capital program, project list public in the CIP", "data/city_capital_2026.json (1,479 CIP projects, unused). City CIP 2025-2029"),
 (r"Calumet River Bridges|Englewood Trail|LaSalle Street|Ogden Avenue|Bridge Inspection|Cicero Avenue Bridge|Alternative Fuel|Arterial Resurfacing|Columbus Avenue|Canal Street Viaduct|Archer Ave|Montrose|Chicago Ave Bridge|Superfund|Anadarko|Noise Mitigation|Reconstruct|Expand Terminal|Extend/expand|Rehabilitate|Home Investment Partnership Fy25", "c", "one named project or one federal award", "none, it is a single project"),
 (r"Reserve Balance \((HUD|HHS|DHS|DOJ|DCEO|SOS|EPA)", "a", "federal or state grant reserve, City grants ledger lists projects by grant", "Mid-Year Grants ledger iyu8-jkf8 and data/city_grants_2026.json reserve_attribution (13 lines unattached)"),
 (r"Rehabilitation Loans and Grants|Homeless Services|Youth Mentoring|Youth Employment|Delegate Agencies|Head Start|Festival Production|Millennium Park", "b", "money passed to many agencies or people, contract-to-line link is not public", "OBM Mid-Year 'Data Directory' (payments with funding line, Tableau) or FOIA DFSS/DPD contract list"),
 (r"Claims and Costs of Administration|Hospital and Medical Expenses|Employee Contractual|Dental Plan|Medicare Tax|Insurance Premiums|Loss in Collection", "b", "claims and benefits totals, no public split by type", "FOIA Finance/Risk Management claims by type"),
 (r"CTA Portion|Transfer Tax", "c", "pass-through to the CTA", "none"),
 (r"Salary Provision", "b", "pay provision not yet assigned to positions", "OBM"),
 (r"Contract \d+|CORPORATION|MANAGEMENT GROUP|ABM Aviation|STUDIO ORD|SKIDMORE|HNTB|AOR TRANSIT|LAKESHORE|STANDARD PARKING|OPEN KITCHENS|ALL CHICAGO|SKYLINE|Clark-W.E.|Midway Management", "c", "one contract or one vendor's payments so far", "none, payments by check are in dataset s4vu-giwb"),
 (r"Professional and Technical Services|Professional Services for Information Technology|Software Maintenance|Operation, Repair or Maintenance|Repair/Maintenance|Rental of|Material and Supplies|Repair Parts|Maintenance and Operation of City Owned|Office and Building|Drugs, Medicine|Insurance|Property Maintenance|Purchase of IT|Water \(Chicago|Streets and Pavements", "b", "ordinary contract or supply line, vendor payments exist (side info) but carry no budget line", "OBM Mid-Year 'Data Directory' extract (payments with funding line), or FOIA the Finance voucher lines"),
 (r"Reserve Balance$|Reserve Balance \(", "b", "reserve with no public list", "Ask OBM"),
]
CPS = [
 (r"Series \d|Bond series|bond interest|Bond interest", "c", "one bond series (or one payment of it)", "none, the series is the finest level"),
 (r"vacancy factor|Planned savings|planned cut|Planned cut|Other General Charges \(General Education Fund\)|Other Instr Purposes|set-aside \(budget only\)|PreK Instruction \(Preschool For All \(locally funded\)\)|Contingency Balancing Program \(Contingency for Grant Expansion\)", "c", "planned offset or reserve counted elsewhere", "none"),
 (r"Contingency|Special Income Fund|Money held back|Labor And Employee Rels|School Transitions|Special Education Fund\)", "b", "money held back, no document itemises it", "FOIA CPS Budget Office (planned use of contingency by program)"),
 (r"State Preschool|Preschool For All|PreK Instruction|Payment To Other Govt Units", "a", "passes through the City (DFSS) to community providers, providers are in the City tree", "City tree: 'Delegate Agencies (ISBE - CPS - Early Childhood Block Grant)' paid-to-date boxes. Board Reports 25-0925-EX2"),
 (r"Electricity|Natural gas|Natural Gas", "a", "a few utility suppliers, payments public", "data/cps_supplier_payments_fy2026_over1m.csv: Constellation $37.4M, ComEd $35.9M, Peoples Gas $17.8M, Constellation gas $12.5M"),
 (r"Tuition budgeted but not matched|Special Education Private|Non-Public Tuition", "a", "private special education providers, small ones are in the supplier payment tail", "https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2026 (4,353 vendors under $1M hold $223.7M)"),
 (r"Medical plan share|Prescription plan share|Health insurance set-aside", "b", "reserve for bills that have not arrived", "FOIA CPS Benefits (claims by plan)"),
 (r"Pension reserve|MEABF|operating money diverted|State's share", "c", "one reserve or levy paid as one amount", "none"),
 (r"Emergency/Unanticipated|Potentially Outside Funded|Capital Project Support|IT money budgeted but not spent|IT - Centralized", "c", "capital money not assigned to a project yet", "revisit when CPS charges projects (BI capital expenditure subject area)"),
 (r"Food|Lunch|Breakfast|School meals|Donated food", "b", "one food contract paid across several food lines", "FOIA CPS: Aramark and Open Kitchens payments by meal type"),
 (r"Charter/Contract Per Pupil|Tuition paid to charter", "c", "one charter campus, one payment set by student count", "none"),
 (r"Other job titles \(fewer than 5", "c", "pooled on purpose so no small group of people can be picked out", "none (privacy rule)"),
 (r"paid so far", "c", "one project or provider's payments so far", "none"),
 (r"Public Building Commission|Aramark IFM|Custodial Services|Engineer Services", "b", "PBC building services paid through one authority", "FOIA PBC/CPS invoices by service"),
 (r"Student bus|Options Student|Transportation", "b", "bus contracts, route-level costs not published", "FOIA CPS Transportation"),
]
PARKS = [
 (r"Soldier Field|Boat harbors|Golf", "b", "run by a contractor, no operating budget published", "FOIA Park District: operator budgets (SMG/ASM Global P-12035, Westrec P-14010, Indigo/Troon P-24001)"),
 (r"Water and sewer|Electric", "b", "per-park usage not published", "FOIA Park District utility billing by account (checked: no public per-park data)"),
 (r"principal|Series 2023C", "c", "one bond payment", "none"),
 (r"vacancy", "c", "planned offset", "none"),
]

def tag(path_name, rules):
    for rx, t, why, src in rules:
        if re.search(rx, path_name): return t, why, src, "rule"
    return "b", "no rule matched, treated as needing the budget office", "OBM", "default"

LEADS = [  # (label, regex on the src text, tag it applies to)
    ("OBM Mid-Year Data Directory extract (payments with funding line)", r"Data Directory", None),
    ("Federal airport carryover with no award (Aviation/OBM)", r"AIP grant ledger", None),
    ("CDBG-DR sewer and stormwater (HUD DRGR first)", r"DRGR", None),
    ("Highway and state reserves with no project (CDOT/OBM)", r"FHWA FMIS", None),
    ("State/Lake station cost breakdown (FTA TrAMS or CDOT)", r"TrAMS", None),
    ("Union contract money not yet assigned (OBM)", r"contract settlement schedule", None),
    ("CPS contingencies (CPS Budget Office)", r"contingency by program", None),
    ("City claims and benefits totals (Finance/Risk)", r"claims by type", None),
    ("Bond series not printed (EMMA, trustee schedules)", r"EMMA", None),
    ("Grant reserve lines, project lists in the City ledger", r"Mid-Year Grants ledger", None),
    ("Illinois EPA loan lists", r"Illinois EPA", None),
    ("CPS utilities, four suppliers paid", r"Constellation \$37", None),
    ("CPS preschool, pointer to City delegate agency boxes", r"Early Childhood Block Grant", None),
]

def leads(out):
    print("\n#### leads (dollars of dead ends by next step)")
    allr = [dict(r, gov=g) for g in out for r in out[g]]
    res = []
    for lab, rx, _ in LEADS:
        m = [r for r in allr if re.search(rx, r["src"])]
        res.append((lab, len(m), sum(abs(r["cents"]) for r in m)))
        print(f"  {lab}: {len(m)} boxes ${sum(abs(r['cents']) for r in m)/1e8:,.0f}M")
    return res

def md_tables(out, n=30):
    lines = []
    for g in GOVS:
        lines.append(f"**{ {'city':'City of Chicago','cps':'Chicago Public Schools','parks':'Chicago Park District'}[g] }** ({len(out[g])} dead ends of $10M or more, ${sum(abs(r['cents']) for r in out[g])/1e8:,.0f}M)\n")
        lines.append("| # | $M | Box | Basis | Tag | Why it stops |\n|---:|---:|---|---|:-:|---|")
        for r in out[g][:n]:
            nm = r["path"].split(" > ")
            nm = (" > ".join(nm[-2:]) if len(nm) > 1 else nm[0])
            nm = re.sub(r"\s*\((?:[A-Za-z]+ - )+[^()]*(?:\([^()]*\))?[^()]*\)", "", nm)
            nm = nm.replace("Construction of Buildings and Other Structures", "Construction").replace("For Professional and Technical Services and Other Third Party Benefit Agreements", "Professional services").replace("Paid from: ", "")
            nm = nm if len(nm) <= 80 else nm[:77] + "..."
            lines.append(f"| {r['rank']} | {r['cents']/1e8:,.1f} | {nm.replace('|','/')} | {r['basis'][:6]} | {r['tag']} | {r['why']} |")
        lines.append("")
    return "\n".join(lines)

def main():
    import sys
    out = {}
    rules = {"city": CITY, "cps": CPS, "parks": PARKS}
    summary = {}
    for g in GOVS:
        L = json.load(open(f"{OUT}/deadends_{g}.json"))
        rows = []
        for i, x in enumerate(L, 1):
            pn = x["path"] + " | " + x["name"]
            # whole path matters for context, name for rule priority: try name first then path
            t, why, src, how = tag(x["name"], rules[g])
            if how == "default": t, why, src, how = tag(pn, rules[g])
            rows.append({"rank": i, "id": x["id"], "cents": x["amount_cents"], "basis": x["basis"], "name": x["name"], "path": x["path"], "tag": t, "why": why, "src": src, "how": how})
        tot = sum(abs(r["cents"]) for r in rows)
        by_tag = collections.defaultdict(lambda: [0, 0]); dflt = [0, 0]
        for r in rows:
            by_tag[r["tag"]][0] += 1; by_tag[r["tag"]][1] += abs(r["cents"])
            if r["how"] == "default": dflt[0] += 1; dflt[1] += abs(r["cents"])
        summary[g] = {"n": len(rows), "abs_cents": tot, "by_tag": dict(by_tag), "default": dflt}
        out[g] = rows
        print(f"\n### {g}: {len(rows)} dead ends, ${tot/1e8:,.0f}M")
        for t in "abc": print(f"  ({t}) {by_tag[t][0]:3} boxes ${by_tag[t][1]/1e8:8,.0f}M {100*by_tag[t][1]/tot:5.1f}%")
        print(f"  untouched by an explicit rule (default b): {dflt[0]} boxes ${dflt[1]/1e8:,.0f}M")
        t30 = rows[:30]
        c30 = collections.Counter(r["tag"] for r in t30)
        print("  top 30:", dict(c30), f"${sum(abs(r['cents']) for r in t30)/1e8:,.0f}M")
    lead_rows = leads(out)
    json.dump({"rows": out, "summary": summary, "leads": lead_rows}, open(f"{OUT}/rank.json", "w"), indent=1)
    open(f"{OUT}/top30_tables.md", "w").write(md_tables(out))

    print("\n#### markdown tables, top 30 per government")
    for g in GOVS:
        print(f"\n**{g}**\n\n| # | $M | Box (end of path) | Basis | Tag | Why it stops, and what would move it |\n|---:|---:|---|---|:-:|---|")
        for r in out[g][:30]:
            nm = r["path"].split(" > ")
            nm = " > ".join(nm[-2:]) if len(nm) > 1 else nm[0]
            nm = re.sub(r"\s*\((?:[A-Z][A-Za-z\- ]+ - )+[^)]*\)\)?", "", nm)[:70]
            print(f"| {r['rank']} | {r['cents']/1e8:,.1f} | {nm} | {r['basis'][:6]} | {r['tag']} | {r['why']}. {r['src']} |")

if __name__ == "__main__":
    main()
