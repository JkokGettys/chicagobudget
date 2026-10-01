"""Decide whether a payee name is a business/organization or an individual person.

Used to hide individuals' names in vendor payment side info while keeping every payment
row visible. Rule of thumb: when unsure, treat it as a PERSON (hide the name). Hiding a
business name by mistake is harmless; showing a private person's name is not.

is_business(name, has_contract) -> True | False
"""
import re

# Words that only appear in organization names.
ORG_TOKENS = {
    "INC", "INCORPORATED", "LLC", "L.L.C", "LLP", "LP", "LTD", "LIMITED", "CORP", "CORPORATION", "CO", "COMPANY",
    "PLLC", "PC", "P.C", "NFP", "PLC", "GMBH", "NA", "N.A", "FSB",
    "ASSOCIATES", "ASSOCIATION", "ASSOC", "ASSN", "PARTNERS", "PARTNERSHIP", "GROUP", "HOLDINGS", "ENTERPRISES",
    "SERVICES", "SERVICE", "SOLUTIONS", "SYSTEMS", "TECHNOLOGIES", "TECHNOLOGY", "CONSULTING", "CONSULTANTS",
    "CONSTRUCTION", "CONTRACTORS", "CONTRACTING", "ENGINEERING", "ENGINEERS", "ARCHITECTS", "MANAGEMENT",
    "BANK", "TRUST", "FUND", "FOUNDATION", "INSTITUTE", "UNIVERSITY", "COLLEGE", "SCHOOL", "ACADEMY",
    "CHURCH", "MINISTRIES", "MINISTRY", "CENTER", "CENTRE", "CLINIC", "HOSPITAL", "HEALTH", "MEDICAL",
    "CITY", "COUNTY", "STATE", "VILLAGE", "DISTRICT", "AUTHORITY", "DEPARTMENT", "DEPT", "BOARD", "COMMISSION",
    "AGENCY", "COUNCIL", "SOCIETY", "LEAGUE", "CLUB", "ALLIANCE", "COALITION", "NETWORK", "COOPERATIVE", "COOP",
    "TREASURER", "COMPTROLLER", "RETIREMENT", "PENSION", "ANNUITY", "INSURANCE", "MUTUAL", "CREDIT", "FINANCIAL",
    "SUPPLY", "SUPPLIES", "EQUIPMENT", "MOTORS", "AUTO", "FORD", "CHEVROLET", "TOYOTA", "SALES", "RENTAL",
    "PRODUCTIONS", "STUDIO", "STUDIOS", "MEDIA", "PRESS", "PUBLISHING", "COMMUNICATIONS", "WIRELESS",
    "ENERGY", "ELECTRIC", "GAS", "WATER", "ENVIRONMENTAL", "LABS", "LABORATORIES", "INDUSTRIES", "MANUFACTURING",
    "INTERNATIONAL", "NATIONAL", "AMERICAN", "AMERICA", "CHICAGO", "ILLINOIS", "MIDWEST", "GLOBAL", "USA", "US",
    "JOINT", "VENTURE", "JV", "CAFE", "RESTAURANT", "CATERING", "HOTEL", "REALTY", "PROPERTIES", "PROPERTY",
    "APARTMENTS", "HOUSING", "DEVELOPMENT", "HOMES", "LENDING", "MORTGAGE", "CAPITAL", "INVESTMENTS",
    "NEIGHBORHOOD", "COMMUNITY", "FAMILY", "YOUTH", "SENIOR", "SENIORS", "MUSEUM", "THEATER", "THEATRE",
    "PROGRAM", "PROJECT", "INITIATIVE", "OUTREACH", "RECOVERY", "PARTNERSHIPS", "CONSORTIUM", "ESTATE",
    "TRUSTEE", "ESCROW", "TITLE", "ATTORNEYS", "LAW", "LEGAL", "OFFICES",
}
ORG_PHRASES = re.compile(r"(\bD/?B/?A\b|\s&\s|&|\bAND\b|^THE\b|\bOF\b|\bFOR\b)")


def tokens(u):
    return [t.strip(".,'\"") for t in re.split(r"[\s,/()]+", u) if t.strip(".,'\"")]


def is_business(name, has_contract=False, known_people=None):
    """known_people: set of upper-case names of individuals (e.g. current City employees).
    A name in that set is always treated as a person."""
    u = (name or "").upper().strip()
    if not u:
        return False
    if known_people and u in known_people:
        return False
    # The payment system appends numbers to some personal names ("PEDRO CISNEROS 01", "Lisa Moore1"),
    # so drop trailing digits before testing. Addresses ("1237 N. CALIFORNIA") start with a number.
    u = re.sub(r"\s*\d+$", "", u).strip()
    toks = tokens(u)
    if any(t in ORG_TOKENS for t in toks):
        return True
    if ORG_PHRASES.search(u):
        return True
    if re.match(r"^\d", u) or re.search(r"\b(LLC|INC|CORP)\b", u):
        return True
    if re.search(r"\.(COM|ORG|NET)\b", u):
        return True
    # "LAST, FIRST M": a person, even with a contract (e.g. "ODIE PAYNE, MD" stays hidden)
    if re.match(r"^[A-Z' .-]+, ?[A-Z' .-]+$", u):
        return False
    # Holding a City contract means the City procured from this payee: a business or nonprofit
    # (single-word names like PATSON, THRESHOLDS, TAPROOTS, CLIHTF).
    if has_contract:
        return True
    # A single word with no contract is usually a trade name (USALCO, CCMSI, TEACHSTONE);
    # people are listed with at least two names.
    if len(toks) == 1 and len(u) >= 4:
        return True
    return False
