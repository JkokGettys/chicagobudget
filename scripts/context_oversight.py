"""Oversight and performance findings with verbatim, machine-checked quotes.

For each finding we save: which budget department(s) it touches, the source URL, a short plain-language
summary, and one or more VERBATIM quotes. The script downloads each source (cached in raw/context/) and
checks every quote appears in the source text (after normalizing whitespace and curly quotes/dashes).
If a quote is not found, that finding is marked verified=false and the script exits with an error.

Sources: City Office of Inspector General (igchicago.org), City Council Office of Financial Analysis (COFA),
Civic Federation, Chicago Police Department, 2026 Budget Overview (OBM), and local news where noted.
Findings are by those organizations. Estimates (for example EY savings reported by the Civic Federation)
are THEIR estimates, not audited and not ours.

Department names match dataset 6694-f78c exactly.

Usage: python3 scripts/context_oversight.py -> data/context_oversight_findings.json
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from context_common import fetch, html_text, norm, pdf_text, write_json  # noqa: E402

OIG = "https://igchicago.org/wp-content/uploads"
SRC = {
    "oig_cfd_followup": ("pdf", "oig_cfd_followup.pdf", OIG + "/2025/10/OIG-Second-Follow-up-to-Second-Audit-of-CFD-and-EMS-Response-Times.pdf"),
    "oig_q4_2025": ("pdf", "oig_q4_2025.pdf", OIG + "/2026/01/OIG-Quarterly-Report-Q4-2025.pdf"),
    "cofa_cfd_manning": ("pdf", "cofa_cfd_manning.pdf", "https://www.chicago.gov/content/dam/city/depts/COFA/RevenueResources/COFA_Savings%20Resource_CFD%20Manning_FY26%20Mid%20Year%20Update2.pdf"),
    "oig_311": ("pdf", "oig/sr311.pdf", OIG + "/2026/02/OIG-Audit-of-311-Service-Request-Process.pdf"),
    "oig_rats": ("pdf", "oig/rats.pdf", OIG + "/2026/07/Audit-of-DSSs-Rat-Abatement-Program.pdf"),
    "oig_autopounds": ("pdf", "oig/autopounds.pdf", OIG + "/2026/08/Audit-of-the-Department-of-Streets-and-Sanitations-Administration-of-Auto-Pounds.pdf"),
    "oig_debt": ("pdf", "oig/debt.pdf", OIG + "/2026/05/Audit-of-DOFs-Management-of-Outstanding-Debt-Updated.pdf"),
    "oig_paytime": ("pdf", "oig/paytime.pdf", OIG + "/2026/08/Audit-of-DOFs-Payment-Timeliness.pdf"),
    "oig_water": ("pdf", "oig/water.pdf", OIG + "/2026/05/Audit-of-the-Citys-Metered-Water-Billing.pdf"),
    "oig_dob": ("pdf", "oig/audit-of-dob-permit-inspections-process.pdf", OIG + "/2023/08/Audit-of-the-Department-of-Buildings-Permit-Inspections-Process.pdf"),
    "oig_cdph": ("pdf", "oig/cdph-mental-health-equity.pdf", OIG + "/2025/08/OIG-Audit-of-CDPHs-Mental-Equity-Program.pdf"),
    "oig_dfss_enc": ("pdf", "oig/audit-dfss-encampments-outreach.pdf", OIG + "/2023/08/Audit-of-DFSS-Outreach-to-Encampments-of-People-Experiencing-Homelessness.pdf"),
    "oig_dfss_contract": ("pdf", "oig/audit-of-the-department-of-family-and-support-services-strategic-contracting.pdf", OIG + "/2023/08/Audit-of-the-Department-of-Family-and-Support-Services-Strategic-Contracting.pdf"),
    "oig_dhr_eap": ("pdf", "oig/dhr-eap-audit.pdf", OIG + "/2025/04/OIG-Audit-of-DHRs-Employee-Assistance-Program.pdf"),
    "oig_wc": ("pdf", "oig/dof-civilian-workers-compensation-program-audit.pdf", OIG + "/2024/07/Audit-of-DOFs-Civilian-Workers-Compensation-Program-Administration.pdf"),
    "oig_cofa": ("pdf", "oig/cofa-audit.pdf", OIG + "/2026/04/Audit-of-City-Council-Office-of-Financial-Analysis.pdf"),
    "oig_copa_page": ("html", "oig_copa_timeliness.html", "https://igchicago.org/publications/review-of-the-civilian-office-of-accountabilitys-timeliness-initiative/"),
    "oig_911_page": ("html", "oig_cpd_911_followup.html", "https://igchicago.org/publications/cpd-911-response-time-follow-up/"),
    "cpd_2025": ("pdf", "cpd_2025_review.pdf", "https://www.chicagopolice.org/wp-content/uploads/2025-in-Review.pdf"),
    "hpherald": ("html", "hpherald_clearance.html", "https://www.hpherald.com/evening_digest/police-homicide-clearance-rate-hits-13-year-high-as-murders-fall-dramatically-citywide/article_74ff6015-4da0-4584-944b-354034b61696.html"),
    "wttw_settle": ("html", "wttw_settlements_2025.html", "https://news.wttw.com/2026/07/10/chicago-taxpayers-spent-259m-resolve-police-misconduct-lawsuits-2025-city-analysis"),
    "civicfed_adopted": ("html", "civicfed_fy26.html", "https://www.civicfed.org/chicagos-fy2026-adopted-budget"),
    "civicfed_eff": ("html", "civicfed_eff.html", "https://www.civicfed.org/blog/which-cuts-didnt-make-cut-efficiency-opportunities-chicagos-fy2026-budget"),
    "cofa_midyear": ("pdf", "cofa_midyear_fy26.pdf", "https://www.chicago.gov/content/dam/city/depts/COFA/MidyearReport/COFA_FY2026_MidYear_Full%20Report.pdf"),
    "cofa_budget_rec": ("pdf", "cofa_budget_rec_summary_fy26.pdf", "https://www.chicago.gov/content/dam/city/depts/COFA/ProposedBudget/Presentations_ProposedBudget/COFA_Budget%20Recommendation%20Summary_Final.pdf"),
    "budget_overview": ("pdf", "budget_overview_2026.pdf", "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Overview.pdf"),
}

_cache = {}


def match_norm(s):
    """Normalize for quote matching. Also rejoins words hyphenated across a line wrap ('re-\\nchecks')
    in BOTH the source and the quote, so a wrapped hyphen cannot cause a false miss or a false hit."""
    import re
    s = re.sub(r"-\s*\n\s*", "-", s)
    return norm(s)


def text_of(key):
    if key in _cache:
        return _cache[key]
    kind, name, url = SRC[key]
    path = fetch(url, name, timeout=240)
    t = pdf_text(path) if kind == "pdf" else html_text(path)
    _cache[key] = match_norm(t)
    return _cache[key]


def F(fid, depts, org, src, date, title, summary, quotes, tone, caveat=None, figures=None, estimate=False):
    return {"id": fid, "departments": depts, "org": org, "source_key": src, "source_url": SRC[src][2],
            "date": date, "title": title, "summary": summary, "quotes": quotes, "tone": tone,
            "caveat": caveat, "dollar_figures": figures or [], "is_estimate_not_audited": estimate}


CFD, CPD = "Chicago Fire Department", "Chicago Police Department"
DSS, CDOT = "Department of Streets and Sanitation", "Chicago Department of Transportation"
DWM, DOF = "Department of Water Management", "Department of Finance"
FG, FFM = "Finance General", "Department of Fleet and Facility Management"

FINDINGS = [
    # ---------------- Fire ----------------
    F("oig-cfd-response-times-2025", [CFD], "Office of Inspector General", "oig_cfd_followup", "2025-10-29",
      "CFD still has not fixed how it measures response times (second follow-up to 2021 audit)",
      "The Inspector General checked again and found the Fire Department has not done what the 2021 audit asked: no public response-time reporting, no documented goals, no fix for data gaps. CFD says the budget office denied its requests for data-analysis staff.",
      ["OIG concludes that CFD has not implemented corrective actions related to the audit findings.",
       "CFD attributed its lack of progress to the Office of Budget and Management's (OBM) denying budget requests for personnel and resources to conduct data analysis."],
      "concern", caveat="This is about whether response times are MEASURED and reported, not proof that response times are slow."),
    F("oig-cfd-fire-prevention-2025", [CFD], "Office of Inspector General", "oig_q4_2025", "2025-10-23",
      "Fire Prevention Bureau inspected only 16.8% of buildings in its database within 12 months",
      "OIG audited annual fire-code inspections. Few buildings were inspected on time, and the City collected little of the re-check fees owed.",
      ["Of the buildings and tenant spaces in FPB's database, 16.8% received an annual inspection within a 12-month period.",
       "The City collected only 13.2% of the fees owed for re-checks of violations, leaving $1.1 million unrecovered over a ten-year period."],
      "concern", figures=[{"label": "re-check fees unrecovered over 10 years", "value": 1.1e6}],
      caveat="Quoted from the OIG Q4 2025 quarterly report summary of the audit (page 40). Full audit: https://igchicago.org/publications/audit-cfd-fpb/"),
    F("cofa-cfd-manning-2026", [CFD], "Council Office of Financial Analysis", "cofa_cfd_manning", "2026 mid-year",
      "COFA: lowering fire engine and truck minimum crew from 5 to 4 could save up to $69.43M a year",
      "COFA modeled the savings of a four-person minimum on engines and trucks (NFPA recommends four). It needs a union contract change. COFA also notes CFD does not report response times publicly and has 80 ambulances for 2.7 million people.",
      ["CFD could realize up to approximately $69.43 million in personnel savings",
       "the Department does not report response times publicly",
       "The City operates 80 ambulances to support a population of over 2.7 million"],
      "context", figures=[{"label": "COFA modeled annual savings, up to", "value": 69.43e6},
                          {"label": "CFD overtime paid in 2025 (COFA)", "value": 90.94e6}],
      caveat="A savings option, not a recommendation. Savings depend on how the City implements it and need union agreement. COFA says it does not net out other costs.",
      estimate=True),
    F("oig-cfd-hiring-note", [CFD], "Office of Inspector General", "oig_q4_2025", "2025-10-23",
      "OIG: CFD also is not producing the legally required annual fire-loss report",
      "Same Fire Prevention audit: CFD was not in compliance with a Municipal Code rule to report yearly to the Mayor and Council on the causes and extent of fire loss.",
      ["CFD was not in compliance with MCC"], "concern"),
    # ---------------- Police ----------------
    F("cpd-homicide-clearance-2025", [CPD], "Chicago Police Department", "cpd_2025", "2026-01-05",
      "CPD reports 416 homicides in 2025 and a 71% homicide clearance rate",
      "CPD's own year-end release.",
      ["ending the year with 416 homicides, the lowest since 1965",
       "The Bureau of Detectives cleared a total of 296 homicides this year, for a 71% clearance rate."],
      "context", caveat="Self-reported by CPD. 'Cleared' is not the same as 'solved': it can include cases where the suspect died or prosecutors declined to charge."),
    F("oig-clearance-caution-2026", [CPD], "Inspector General (quoted by Hyde Park Herald)", "hpherald", "2026-01-29",
      "Inspector General: clearance rate is 'a tricky metric'",
      "The OIG's dashboard shows 71.2% of 423 homicides cleared in 2025 (CPD's own release says 416 homicides). The Inspector General warned that 'cleared' does not mean justice was done.",
      ["Chicago police cleared 71.2% of homicides in 2025, a 13-year high, according to new data released by the city's Office of Inspector General (OIG).",
       "We talk about them as if they are solved crimes, but in fact they are cleared crimes"],
      "context", caveat="Homicide count differs between sources (416 CPD release, 423 OIG dashboard per the Herald). The Herald is a news report of the OIG dashboard, not the dashboard itself."),
    F("budget-overview-clearance-2025", [CPD], "Office of Budget and Management", "budget_overview", "2025-10",
      "Mayor's budget book says homicide clearance rate 'has risen to 77.4%'",
      "The 2026 Budget Overview cites a higher number than CPD's full-year 71%. Likely a partway-through-2025 figure, not confirmed.",
      ["homicide clearance rate has risen to 77.4%, the highest in over a decade"],
      "context", caveat="Do not mix the 77.4% (budget book, partial year, as of the book's writing) with the 71% full-year number. Show one, and say which."),
    F("oig-cpd-911-followup-2026", [CPD, "Office of Emergency Management and Communications"], "Office of Inspector General", "oig_911_page", "2026-07-23",
      "OIG follow-up on 911 response-time data: 1 fixed, 2 mostly fixed, 2 not fixed",
      "OIG checked whether CPD fixed missing timestamps in 911 response-time data.",
      ["CPD has fully implemented one, substantially implemented two, and not implemented two of the corrective actions"],
      "mixed"),
    F("oig-copa-timeliness-2026", ["Civilian Office of Police Accountability"], "Office of Inspector General", "oig_copa_page", "2026-06-17",
      "OIG: COPA cut its backlog but did not follow its own rules while doing it",
      "COPA closed old low-level cases with training recommendations instead of discipline. OIG says COPA did not fully follow its guidelines.",
      ["COPA did reduce its investigative caseload under the initiative",
       "COPA did not fully adhere to the TIP guidelines as outlined"],
      "mixed"),
    F("cofa-cpd-overtime-fy26", [CPD], "Council Office of Financial Analysis", "cofa_budget_rec", "2025-10",
      "COFA: CPD overtime is budgeted at $200M for 2026, and actual spending typically runs about 2x budget",
      "Overtime above $200M needs City Council approval under the 2026 management ordinance. In 2025 the budget was $100M.",
      ["Budgeted $200M in Corporate Fund; any overtime above $200M requires City Council approval",
       "actual spend typically 2x over budget"],
      "concern", figures=[{"label": "CPD overtime budgeted FY2026", "value": 200e6}, {"label": "CPD overtime budgeted FY2025", "value": 100e6}]),
    F("budget-overview-cpd-civilianization", [CPD], "Office of Budget and Management", "budget_overview", "2025-10",
      "Budget book: CPD claims nearly $10M in savings from replacing officers with civilians in desk jobs since 2024",
      "Self-reported by the City.",
      ["nearly $10M in civilianization savings achieved since the 2024 budget"], "context",
      figures=[{"label": "claimed civilianization savings since 2024 budget", "value": 10e6}]),
    # ---------------- Streets, transportation, water ----------------
    F("oig-rat-abatement-2026", [DSS], "Office of Inspector General", "oig_rats", "2026-07-28",
      "OIG: rat control reacts to complaints and does not track whether it works",
      "The Bureau of Rodent Control's main tool is poisoning in response to 311 complaints, with no survey of root causes and no evaluation of results. The 2026 budget gives the bureau $12.5M.",
      ["BORC's primary goal was to poison rats in response to complaints rather than addressing the root causes of rat infestations while using poison as a last resort.",
       "BORC did not evaluate or report on the effectiveness of its intervention efforts",
       "The City's 2026 Budget allocated $12,527,603 to BORC"],
      "concern", figures=[{"label": "2026 budget for Bureau of Rodent Control", "value": 12527603}]),
    F("oig-auto-pounds-2026", [DSS], "Office of Inspector General", "oig_autopounds", "2026-08-26",
      "OIG: auto pound records are unreliable and vehicle retrieval is confusing",
      "Records for 15% of a random sample of vehicles could not show whether the car was redeemed, disposed of, or still impounded. Most pound operations are contracted to United Road Towing.",
      ["digital impoundment records are unreliable, such that it was unclear whether 15% of a randomly selected sample of vehicles had been redeemed, disposed of, or remained impounded",
       "The City Has Awarded URT and its Affiliates Over $223 Million in Contracts to Operate City Auto Pounds"],
      "concern", figures=[{"label": "contract value awarded to towing contractor and affiliates since 1997 (OIG Figure 8)", "value": 223e6}],
      caveat="The $223M is a multi-decade total of contract values, not one year's spend."),
    F("oig-311-audit-2026", ["Office of Emergency Management and Communications"], "Office of Inspector General", "oig_311", "2026-02-26",
      "OIG: 311 status information confuses people, and only 2 staff cover 40+ departments",
      "311 is run by OEMC. The public-facing request status information 'contributes to public confusion and distrust'.",
      ["information about service requests on 311's public facing platforms contributes to public confusion and distrust",
       "The two staff in the Service Advocacy Unit are responsible for serving more than 40 City departments"],
      "concern", caveat="311 City Services is part of OEMC in the budget (assumption based on the OIG audit's wording, 'OEMC's management of 311'). Not checked against the department's budget lines."),
    F("oig-water-billing-2026", [DWM, DOF], "Office of Inspector General", "oig_water", "2026-05-06",
      "OIG: water meters are accurate, but billing and service-order processes can create errors",
      "Good news and bad news: residential meters measure accurately (OIG reviewed 2,200 meter tests). The billing and work-order processes can cause or worsen bill spikes.",
      ["OIG reviewed 2,200 DWM meter tests and concluded that meters generally measure water use accurately.",
       "DWM and DOF's processes related to service orders, billing exceptions, and estimate and credit calculations may introduce errors that lead to or worsen spikes for some customers"],
      "mixed"),
    # ---------------- Finance, HR, procurement, law ----------------
    F("oig-city-debt-owed-2026", [DOF], "Office of Inspector General", "oig_debt", "2026-04-16",
      "OIG: about $8.1 billion is owed TO the City (fines, fees, etc.), and no one tracks all of it",
      "This is money people and businesses owe the City, not City borrowing. OIG calls $8.1B 'almost certainly a floor'.",
      ["The systems actively used by DOF contain approximately $8.1 billion in outstanding debt.",
       "No City department has knowledge or management oversight of all debt owed to the City."],
      "concern", figures=[{"label": "debt owed to the City in DOF systems (OIG)", "value": 8.1e9}],
      caveat="Includes fines, penalties and interest that may never be collected. Do not read it as '$8.1B the City could collect'."),
    F("oig-payment-timeliness-2026", [DOF], "Office of Inspector General", "oig_paytime", "2026-08-11",
      "OIG: the City cannot tell whether it pays vendors within 30 days",
      "Data in the City's payment system is not reliable enough to measure on-time payment.",
      ["neither OIG nor DOF can provide reliable information about the timeliness of vendor payments"],
      "concern"),
    F("oig-workers-comp-2024", [DOF], "Office of Inspector General", "oig_wc", "2024-07-31",
      "OIG: workers' compensation program improved; open claims expected to cost over half a billion",
      "Positive on process, a large cost.",
      ["Given that the Program has more than 2,000 open claims expected to cost over half a billion dollars across their lifetimes",
       "DOF has substantially implemented the corrective actions recommended by Grant Thornton in 2019."],
      "mixed", figures=[{"label": "expected lifetime cost of open civilian workers' comp claims, over", "value": 500e6}]),
    F("oig-dhr-eap-2025", ["Department of Human Resources"], "Office of Inspector General", "oig_dhr_eap", "2025-04-17",
      "OIG: HR cannot tell whether the Employee Assistance Program works",
      "No structure, goals or documented policies.",
      ["DHR cannot determine whether the City of Chicago's EAP achieves either of these aims because the program lacks structure, guidance, and clear goals."],
      "concern"),
    F("oig-cofa-audit-2026", ["City Council"], "Office of Inspector General", "oig_cofa", "2026-04-21",
      "OIG: Council's own budget office (COFA) has not consistently given Council independent analysis",
      "COFA is staffed under the City Council. COFA says it lacks timely data access and resources. Which budget department pays for COFA is not checked here.",
      ["COFA has not consistently provided independent financial analysis to assist City Council and protect the public's interest in the effective and efficient expenditure of City funds."],
      "concern", caveat="We cite COFA elsewhere in this file. Weigh it knowing this audit."),
    # ---------------- Buildings, health, family services ----------------
    F("oig-dob-permit-inspections-2022", ["Department of Buildings"], "Office of Inspector General", "oig_dob", "2022-08-25",
      "OIG: 42 buildings were fully built without all required inspections (2017 to 2019 permits)",
      "Buildings relies on contractors to request inspections and does not check which are missing. 35 of the 42 were single-family homes.",
      ["OIG identified 42 buildings within DOB's permit and inspection system that did not have all required inspections and found that the associated buildings had nonetheless been fully constructed."],
      "concern", caveat="2022 audit, followed up in 2024. Check the follow-up before saying the problem persists: https://igchicago.org/publications/follow-up-audit-dob-permit-inspections/"),
    F("oig-cdph-mental-health-2025", ["Chicago Department of Public Health"], "Office of Inspector General", "oig_cdph", "2025-08-12",
      "OIG: mental health network is equitable overall, but City-run clinics' data is not reliable",
      "Mixed: services generally fit program goals, but the City-run centers' own data cannot show performance.",
      ["OIG concluded that CDPH is supporting equitable and integrated mental health services for Chicagoans through the MHEI network",
       "the City-run Mental Health Centers' service data is not complete or reliable enough to enable informed decisions about operations"],
      "mixed"),
    F("oig-dfss-encampments-2023", ["Department of Family and Support Services"], "Office of Inspector General", "oig_dfss_enc", "2023-08-23",
      "OIG: 94.1% of encampment residents who attended a housing event entered stable housing; 78.6% were still housed at the check date",
      "One of the few audit findings that measures an OUTCOME and finds it good.",
      ["224 encampment residents, or 94.1% of participants, entered stable housing",
       "187, or 78.6% of all participants, remained housed as of October 3, 2022"],
      "positive", caveat="Covers Nov 2020 to May 2022 participants only. Small group (about 238 people)."),
    F("oig-dfss-contracting-2022", ["Department of Family and Support Services"], "Office of Inspector General", "oig_dfss_contract", "2022-08-09",
      "OIG: DFSS grant evaluators scored nonprofit applications inconsistently",
      "DFSS passes much of its money to nonprofit 'delegate agencies' (see the delegate agencies line in the appropriations).",
      ["RFP application evaluators inconsistently applied scoring guidance."],
      "concern"),
    # ---------------- Fleet, real estate, procurement, benefits (EY via Civic Federation) ----------------
    F("ey-fleet-civicfed-2025", [FFM], "Civic Federation (summarizing City-commissioned EY report)", "civicfed_eff", "2025-11-07",
      "EY report: average City vehicle driven only 7,000 miles a year; 1 vehicle per 17 employees",
      "The Civic Federation summarized an Ernst & Young efficiency study the City commissioned.",
      ["The average City vehicle was driven only 7,000 miles per year, less than a third of the rate of vehicle usage in Chicago's peer cities.",
       "The City owns one vehicle for every 17 full-time equivalent (FTE) positions, far in excess of the industry equivalent of one per 65 FTE.",
       "The report estimated between $16 million and $31 million in cost savings from optimizing the City's vehicle fleet management."],
      "concern", figures=[{"label": "EY estimated fleet savings, low", "value": 16e6}, {"label": "EY estimated fleet savings, high", "value": 31e6}],
      estimate=True, caveat="An EY estimate reported by the Civic Federation. Not audited."),
    F("ey-real-estate-civicfed-2025", [FFM], "Civic Federation (summarizing EY)", "civicfed_eff", "2025-11-07",
      "EY report: office space in the 10 largest City buildings exceeds the number of employees by 33%",
      "Selling buildings and land is an EY-identified option.",
      ["amount of workspace exceeds the number of employees by 33%",
       "the report identifies $157-$202 million in real estate savings over the course of ten years"],
      "context", figures=[{"label": "EY real estate savings over 10 years, low", "value": 157e6}, {"label": "high", "value": 202e6}],
      estimate=True, caveat="An EY estimate over ten years, much of it one-time sale proceeds."),
    F("ey-benefits-civicfed-2025", [FG], "Civic Federation (summarizing EY)", "civicfed_eff", "2025-11-07",
      "EY report: $80M to $103M a year possible by aligning employee benefits with peer employers",
      "Employee health care sits in Finance General. Many items need union negotiation.",
      ["EY identified $80-$103 million in savings the City could realize from moving itself to align its benefit structure with its peers."],
      "context", figures=[{"label": "EY benefits savings, low", "value": 80e6}, {"label": "high", "value": 103e6}],
      estimate=True, caveat="An EY estimate. Requires bargaining with unions."),
    F("ey-procurement-civicfed-2025", ["Department of Procurement Services"], "Civic Federation (summarizing EY)", "civicfed_eff", "2025-11-07",
      "EY report: 49% of City spending is not managed by the procurement department",
      "EY recommends centralized purchasing ('category management'), taking three to five years.",
      ["49% of total spending not managed by the Department of Procurement Services",
       "EY estimates $55-$111 million in savings based on the 2024 budget"],
      "context", figures=[{"label": "EY procurement savings, low", "value": 55e6}, {"label": "high", "value": 111e6}],
      estimate=True),
    F("civicfed-adopted-2026", [FG, CPD, CFD], "Civic Federation", "civicfed_adopted", "2026-01",
      "Civic Federation: FY2026 budget borrows to pay police settlements and firefighter back pay",
      "The Civic Federation's view of the adopted $16.6B budget.",
      ["Uses debt, rather than operating revenue, to cover the cost of legal police settlements and retroactive salaries for firefighters.",
       "Includes only a handful of efficiencies and cost savings."],
      "concern", caveat="An opinion from a business-funded civic watchdog. It is a fair summary of the budget but also a policy position."),
    # ---------------- COFA options (savings / revenue) ----------------
    F("cofa-midyear-options-2026", [CFD, DSS, DWM, "Department of Human Resources"], "Council Office of Financial Analysis", "cofa_midyear", "2026 mid-year",
      "COFA Budget Options: savings and revenue ideas with dollar ranges",
      "COFA's published menu. Estimates do not net out implementation costs.",
      ["Firefighter Manning Requirement Up to $69.43M in annual savings",
       "Timekeeping and Payroll Modernization Up to $12M annual savings",
       "Garbage Fee Increase $55.38M-$211.75M additional annual revenue",
       "Stormwater Utility User Fee $90.50M annual cost recovery"],
      "context", estimate=True, caveat="Options, not recommendations. COFA says the estimates are not comparable to each other."),
    # ---------------- Budget book self-reported results ----------------
    F("budget-overview-graffiti-2025", [DSS], "Office of Budget and Management", "budget_overview", "2025-10",
      "Budget book: 53,741 graffiti complaints addressed year to date, removed within five days",
      "Self-reported. We can check this against 311 data (see data/context_service_metrics_2025.json).",
      ["Addressed 53,741 graffiti removal complaints year to date",
       "ensuring graffiti is removed within five days"],
      "context"),
    F("budget-overview-rodents-2025", [DSS], "Office of Budget and Management", "budget_overview", "2025-10",
      "Budget book: rodent baiting 'maintaining a five-day response time'",
      "Self-reported. 311 data for 2025 shows a more mixed picture (see service metrics).",
      ["maintaining a five-day response time"],
      "context"),
]

# Items we could not verify against a downloadable source. Kept, but clearly flagged.
UNVERIFIED = [
    {
        "id": "cwb-clearance-critique-2026",
        "departments": [CPD],
        "org": "CWB Chicago (news site)",
        "source_url": "https://cwbchicago.com/2026/04/cpd-calls-hundreds-of-murders-cleared-in-most-cases-nobody-was-ever-charged.html",
        "claim_from_search_snippet": "CPD reported a 71 percent clearance rate in 2025, with 296 homicide cases cleared. But internal records show that only 140 of those were cleared by charging someone with murder.",
        "status": "NOT VERIFIED. The page returned HTTP 403 to our script, so this is the search-result snippet only. Read the article before using.",
    },
]


def main():
    bad = []
    for f in FINDINGS:
        t = text_of(f["source_key"])
        ok = True
        missing = []
        for q in f["quotes"]:
            if match_norm(q) not in t:
                ok = False
                missing.append(q)
        f["verified"] = ok
        f["quote_check"] = "all %d quotes found verbatim in downloaded source" % len(f["quotes"]) if ok else "MISSING"
        if not ok:
            f["missing_quotes"] = missing
            bad.append((f["id"], missing))
        # Keep the quote text for the page, plus where it came from.
    out = {
        "generated_by": "scripts/context_oversight.py",
        "how_verified": "Each source is downloaded; each quote is checked as a substring of the source text after collapsing whitespace and normalizing curly quotes and dashes. verified=true means the quote is in the source, not that the source's claim is true.",
        "findings": FINDINGS,
        "unverified_leads": UNVERIFIED,
        "tones": {"concern": "oversight body found a problem", "positive": "oversight body found a good outcome",
                  "mixed": "both good and bad", "context": "numbers or options, no judgment"},
    }
    write_json("context_oversight_findings.json", out)
    n_ok = sum(1 for f in FINDINGS if f["verified"])
    print("findings: %d verified of %d" % (n_ok, len(FINDINGS)))
    if bad:
        for i, m in bad:
            print("UNVERIFIED:", i)
            for q in m:
                print("   -", q)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
