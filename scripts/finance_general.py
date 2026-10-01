"""Break Chicago's "Finance General" department into plain-English categories.

Pulls the 2026 Budget Ordinance (data.cityofchicago.org, dataset 6694-f78c),
classifies each Finance General line item, and flags internal transfers between
city funds (money counted twice: once when moved, once when spent).

Usage: python3 scripts/finance_general.py  -> writes data/finance_general_2026.json
"""
import json, os, urllib.parse, urllib.request
from collections import defaultdict

DATASET = "https://data.cityofchicago.org/resource/6694-f78c.json"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "finance_general_2026.json")

# (category, subcategory or None, is_internal_transfer, matcher on account description)
RULES = [
    ("Internal transfers (double counted)", "Pension money moved into pension funds", True,
     lambda a: "Pension Allocation" in a or "Advance Pension Payment" in a),
    ("Internal transfers (double counted)", "Reimbursements to the Corporate Fund", True,
     lambda a: a.startswith("To Reimburse")),
    # Fund-to-fund "Transfer ..." lines (see research/reconciliation.md). OBM keeps the
    # Corporate Fund's own $350,000 "Transfers Out" line, handled in classify().
    ("Internal transfers (double counted)", "Transfers between city funds", True,
     lambda a: a.startswith("Transfer")),
    ("Pensions", None, False, lambda a: "Annuity and Benefit Fund" in a),
    ("Debt payments", "Interest", False, lambda a: a.startswith("For Interest")),
    ("Debt payments", "Paying back principal", False,
     lambda a: a.startswith("For Payment of Bonds") or a.startswith("For Payment of Term Notes")
     or a.startswith("For Payment on Loans")),
    ("Debt payments", "Bond fees", False, lambda a: "Bond Fees" in a),
    ("Employee health & benefits", "Health care", False,
     lambda a: "Hospital and Medical" in a or "HMO" in a or "Dental" in a),
    ("Employee health & benefits", "Workers' compensation", False, lambda a: "Workers' Compensation" in a),
    ("Employee health & benefits", "Medicare tax", False, lambda a: "Medicare" in a),
    ("Employee health & benefits", "Unemployment insurance", False, lambda a: "Unemployment" in a),
    ("Employee health & benefits", "Other benefits", False,
     lambda a: "Deferred Compensation" in a or "Employee Contractual" in a),
    ("Raises not yet assigned to departments", None, False, lambda a: "Wage Adjustments" in a),
    ("Lawsuits & legal", None, False,
     lambda a: "Judgments" in a or "Legal Expenses" in a or "Consent Decree" in a),
    ("Taxes the city expects not to collect", None, False, lambda a: "Loss in Collection" in a),
    ("Technology & outside services", None, False,
     lambda a: "Information Technology" in a or "Professional and Technical" in a),
    ("Money passed to other agencies", None, False,
     lambda a: "CTA Portion" in a or "Metropolitan Sanitary" in a),
    ("Insurance", None, False, lambda a: "Insurance Premiums" in a),
    ("Emergency medical transportation (ambulance)", None, False, lambda a: "Emergency Medical Transportation" in a),
]


def fetch():
    q = urllib.parse.urlencode({"$where": "department_description='Finance General'", "$limit": 5000})
    return json.load(urllib.request.urlopen(f"{DATASET}?{q}"))


def classify(acct, fund=""):
    if acct.startswith("Transfer") and fund == "Corporate Fund":
        return "Other citywide costs", None, False
    for cat, sub, transfer, match in RULES:
        if match(acct):
            return cat, sub, transfer
    return "Other citywide costs", None, False


def main():
    rows = fetch()
    tree = defaultdict(lambda: defaultdict(list))
    for r in rows:
        acct = r["appropriation_account_description"]
        cat, sub, transfer = classify(acct, r["fund_description"])
        tree[cat][sub or acct].append({
            "account": acct, "fund": r["fund_description"],
            "amount": int(r["_ordinance_amount_"]), "internal_transfer": transfer,
        })

    total = sum(int(r["_ordinance_amount_"]) for r in rows)
    out = {"source": DATASET, "total_gross": total, "categories": []}
    for cat, subs in tree.items():
        children = []
        for name, items in subs.items():
            items.sort(key=lambda i: -i["amount"])
            children.append({"name": name, "amount": sum(i["amount"] for i in items), "items": items})
        children.sort(key=lambda c: -c["amount"])
        out["categories"].append({"name": cat, "amount": sum(c["amount"] for c in children),
                                  "internal_transfer": any(i["internal_transfer"] for c in children for i in c["items"]),
                                  "children": children})
    out["categories"].sort(key=lambda c: -c["amount"])
    transfers = sum(c["amount"] for c in out["categories"] if c["internal_transfer"])
    out["total_net"] = total - transfers

    # Sanity check: every dollar is classified exactly once.
    assert sum(c["amount"] for c in out["categories"]) == total

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    print(f"Finance General gross: ${total:,}   net of internal transfers: ${out['total_net']:,}\n")
    for c in out["categories"]:
        flag = "  (not new spending)" if c["internal_transfer"] else ""
        print(f"${c['amount']:>15,}  {c['amount']/total:5.1%}  {c['name']}{flag}")
        for ch in c["children"][:6]:
            print(f"      ${ch['amount']:>14,}  {ch['name'][:70]}")


if __name__ == "__main__":
    main()
