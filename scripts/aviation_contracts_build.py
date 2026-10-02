#!/usr/bin/env python3
"""Build data/splits/city/aviation_contracts.json: 2026 contract payments next to the O'Hare and Midway operating lines
other than 0140 (IT maintenance 0138, rental 0157, facilities 0160/0161, equipment repair 0162, pavement 0163, water 0183).

Run:  python3 scripts/aviation_contracts_build.py ; then python3 build/city_tree.py (applied, 0 skipped)

RESULT OF THE MATCHING TEST: NO BOXES ARE PLACED. Every line here is "side_only" (facts that are not added into amounts).
Why no payment is placed as a box (the same rule paidtodate_build.py uses: a payment goes on a line only if exactly one line is
left after every clue):
  * The payments file has department, contract and vendor but no fund and no account, so the airport fund (0740 O'Hare,
    0610 Midway) and the account (0161 or 0162 or 0160 ...) must both come from the contract text.
  * Most Aviation maintenance, snow, IT and pavement contracts name both airports, or name none (in 2026: $11.4M and $8.5M of facility work,
    $14.8M and $4.9M of pavement work, $13.3M of IT). They cannot be put on one fund.
  * The contracts that name one airport (an O'Hare snow contract, the automatic doors, the shuttle buses) fit several accounts of
    one family (facilities 0160/0161, equipment 0162, rental of equipment and services 0157). Nothing in the contract text picks one.
  * Contract types that look like one account (pavement work = 0163) all name both airports (Rossi, Sanchez) or none (Preform).
  * Construction contracts (Paschen taxiways, K-Five Midway runway, Blinderman sound insulation) are capital work paid from bond,
    grant or airline money (see aviation_awards.json), not from these operating accounts.
So each line gets a side list: the Aviation contracts of its family paid in 2026, split into "names only this airport",
and one row for "names both airports or neither", with the amount NOT divided between airports. Nothing is scaled or guessed.
"""
import csv
import json
import os
import re
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "splits", "city", "aviation_contracts.json")
PAY = os.path.join(ROOT, "raw", "contracts", "payments_2026ytd_dedup.csv")
CON = os.path.join(ROOT, "raw", "contracts", "contracts_all.csv")

SRC_PAY = {"dataset": "s4vu-giwb", "name": "City of Chicago Payments (deduplicated, checks Jan 1 to 09/28/2026)",
           "url": "https://data.cityofchicago.org/d/s4vu-giwb", "note": "joined to Contracts rsxa-ify5 on contract number (raw/contracts/contracts_all.csv), full contract description"}

# (fund, authority, account, ordinance amount, label, family, airport)
LINES = [
    ("0740", "2015", "0138", 55_012_600, "IT maintenance", "IT", "ORD"),
    ("0740", "2015", "0157", 41_763_901, "rental of equipment and services", "SHUTTLE", "ORD"),
    ("0740", "2015", "0161", 61_340_400, "operation, repair or maintenance of facilities", "FACILITY", "ORD"),
    ("0740", "2015", "0162", 29_763_700, "repair or maintenance of equipment", "FACILITY", "ORD"),
    ("0740", "2015", "0163", 14_395_500, "repair or maintenance of streets and pavements", "PAVEMENT", "ORD"),
    ("0740", "2015", "0183", 12_000_000, "water", "WATER", "ORD"),
    ("0610", "2010", "0138", 9_935_800, "IT maintenance", "IT", "MDW"),
    ("0610", "2010", "0157", 14_875_000, "rental of equipment and services", "SHUTTLE", "MDW"),
    ("0610", "2010", "0161", 29_374_400, "operation, repair or maintenance of facilities", "FACILITY", "MDW"),
    ("0610", "2010", "0162", 32_082_000, "repair or maintenance of equipment", "FACILITY", "MDW"),
    ("0610", "2010", "0163", 6_090_000, "repair or maintenance of streets and pavements", "PAVEMENT", "MDW"),
    ("0610", "2010", "0183", 1_708_900, "water", "WATER", "MDW"),
]
FAMILY_TEXT = {
    "IT": "IT support and maintenance contracts",
    "SHUTTLE": "shuttle bus contracts (the contract text does not say whether the City books them as rental of equipment and services or as operation of facilities)",
    "FACILITY": "maintenance, repair, roofing, doors, snow removal and landscape contracts (one family of accounts: 0160, 0161 and 0162. The contract text does not say which)",
    "PAVEMENT": "pavement, concrete and striping contracts",
}
HOW = {"ORD": "O'Hare", "MDW": "Midway"}


def rev(x):
    try:
        return int(x["revision_number"] or 0)
    except ValueError:
        return 0


def airport_of(desc):
    u = desc.upper()
    o = bool(re.search(r"O.?HARE|\bORD\b", u))
    m = "MIDWAY" in u
    return "BOTH" if o and m else "ORD" if o else "MDW" if m else "NONE"


def family_of(ctype, desc):
    u = desc.upper()
    if re.search(r"^PURCHASE OF", u):
        return None   # equipment purchases (for example the Boschung snow equipment, contract 341673) are not maintenance of facilities
    if re.search(r"TECHNICAL SUPPORT AND MAINTENANCE|INFORMATION TECHNOLOGY", u):
        return "IT"
    if "SHUTTLE BUS" in u:
        return "SHUTTLE"
    if ctype in ("WORK SERV-AVIATION", "JOC"):
        if re.search(r"PAVEMENT|CONCRETE|STRIPING|JOINT SEALING|SAW CUTTING|PAVING", u):
            return "PAVEMENT"
        if re.search(r"ROOFING|DOORS|SNOW|LANDSCAPE|TERRAZZO|MAINTENANCE|REPAIR|PEST|ELECTRICAL|INSPECTION|REHABILITATIONS|FIRE ALARM", u):
            return "FACILITY"
    return None


def main():
    con = defaultdict(list)
    for r in csv.DictReader(open(CON)):
        con[r["purchase_order_contract_number"]].append(r)
    pay = list(csv.DictReader(open(PAY)))
    by = {}
    for r in pay:
        c = r["contract_number"]
        if c == "DV" or c not in con:
            continue
        x = max(con[c], key=rev)
        if (x["department"] or "").upper() != "CHICAGO DEPARTMENT OF AVIATION":
            continue
        ctype = x["contract_type"] or ""
        fam = family_of(ctype, x["purchase_order_description"] or "")
        if not fam:
            continue
        k = c
        if k not in by:
            by[k] = {"contract": c, "vendor": x["vendor_name"], "desc": (x["purchase_order_description"] or "").replace("\ufffd", "'"),
                     "family": fam, "airport": airport_of(x["purchase_order_description"] or ""), "paid": 0.0, "n": 0}
        by[k]["paid"] += float(r["amount"])
        by[k]["n"] += 1

    # City Department of Water on Aviation vouchers (direct vouchers, PV85 prefix): airport not stated
    water = [r for r in pay if r["voucher_number"].startswith("PV85") and r["contract_number"] == "DV"
             and "DEPT OF WATER" in r["vendor_name"].upper()]
    water_tot = round(sum(float(r["amount"]) for r in water), 2)

    splits = []
    for fund, auth, acct, amount, label, fam, ap in LINES:
        side = []
        if fam == "WATER":
            side.append({"kind": "payments_airport_not_stated",
                         "label": (f"Paid in 2026 to the City Department of Water on Aviation vouchers (voucher numbers start PV85, {len(water)} direct vouchers): "
                                   "the payments file does not say whether they are for O'Hare or Midway, so the amount is not divided"),
                         "amount": water_tot, "period": "2026-01-01 to 2026-09-28", "basis": "actual", "source": SRC_PAY})
            note = (f"The {label} line for {HOW[ap]}. Aviation vouchers paid ${water_tot:,.0f} to the City Department of Water in 2026, for both airports together. "
                    "The water bills cannot be told apart by airport in the payments file, so none is placed in a box here.")
        else:
            mine = sorted([c for c in by.values() if c["family"] == fam and c["airport"] == ap], key=lambda c: -c["paid"])
            rest = [c for c in by.values() if c["family"] == fam and c["airport"] in ("BOTH", "NONE")]
            for c in mine[:8]:
                side.append({"kind": "contract_family_paid_2026",
                             "label": f"{c['vendor']}: {c['desc'][:150]} (contract {c['contract']}, names only {HOW[ap]})",
                             "amount": round(c["paid"], 2), "period": "2026-01-01 to 2026-09-28", "basis": "actual", "source": SRC_PAY})
            if rest:
                top = sorted(rest, key=lambda c: -c["paid"])[:5]
                side.append({"kind": "contract_family_paid_2026",
                             "label": (f"{len(rest)} contracts of the same family that name both airports or neither, not divided (largest: "
                                       + "; ".join(f"{c['vendor']} {c['paid']:,.0f}" for c in top) + ")"),
                             "amount": round(sum(c["paid"] for c in rest), 2), "period": "2026-01-01 to 2026-09-28", "basis": "actual", "source": SRC_PAY})
            note = (f"The {label} line for {HOW[ap]}. No payment is placed in a box on this line: the payments file has no fund or account, and the contract text does not pick one line. "
                    f"The side list shows 2026 payments on Aviation {FAMILY_TEXT[fam]} that name only {HOW[ap]}, then the same family for both airports or neither, not divided.")
        splits.append({"target": {"by": "ordinance_line", "fund": fund, "dept": "85", "authority": auth, "account": acct},
                       "expect_amount": amount, "mode": "side_only", "note": note, "side": side})

    meta = {"author": "deep: O'Hare & Midway contracts (non-0140 lines)", "built_by": "scripts/aviation_contracts_build.py",
            "description": "No boxes. Side facts: Aviation contract payments by family next to the IT, rental, facilities, equipment, pavement and water lines. See research/aviation_contracts.md."}
    json.dump({"meta": meta, "splits": splits}, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: {len(splits)} side-only splits, {len(by)} contracts, water {water_tot:,.2f}")
    fams = defaultdict(lambda: defaultdict(float))
    for c in by.values():
        fams[c["family"]][c["airport"]] += c["paid"]
    for f, d in fams.items():
        print(" ", f, {k: round(v) for k, v in d.items()})


if __name__ == "__main__":
    main()
