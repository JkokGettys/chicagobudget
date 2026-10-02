#!/usr/bin/env python3
"""Build data/splits/city/pensions_detail.json: public detail under each City pension fund's boxes.
Inputs are numbers printed in the 12/31/2025 actuarial valuations (raw/pensions_tree/*.txt, fetched by
scripts/pensions_tree_fetch.py). Page numbers are PDF page indexes (page 1 is the cover).
For each fund: benefit-group pieces under the shortfall box (share of benefit dollars, a PROXY), tier pieces under
the normal-cost box, one piece under the advance line. Pieces always fit inside their box."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "splits", "city", "pensions_detail.json")
PRE = ""
NOT_BEN = ("The City's payment is not the same as the benefits paid. The City sends one payment set by law to the fund, "
           "and the fund pays its retirees from that money plus member contributions and investment earnings. "
           "This split shares the payment out by each group's share of yearly benefit dollars, so it is our estimate, not a City figure.")


def fmt(n):
    return f"{n:,.0f}"


def share_pieces(box, groups, src, label_total):
    """groups: [(name, unit_label, count, annual_benefit_dollars, extra_note)]. Allocate `box` dollars by benefit share.
    Floors to cents, then gives the leftover cents to the largest group so the pieces add up to the box."""
    box_c = round(box * 100)
    tot = sum(g[3] for g in groups)
    cs = [box_c * g[3] // tot for g in groups]
    big = max(range(len(groups)), key=lambda i: groups[i][3])
    cs[big] += box_c - sum(cs)
    out = []
    for g, c in zip(groups, cs):
        name, ulabel, count, ben, extra = g
        amt = c / 100
        p = {"name": f"{name}: {fmt(count)} {ulabel}" if count else name, "amount": amt, "basis": "proxy", "source": src,
             "count": count, "unit_amount": round(amt / count, 2) if count else None,
             "unit_label": f"{ulabel} (share of the City's payment each)" if count else None,
             "note": (f"Proxy: this group draws ${fmt(ben)} a year in benefits, {ben / tot * 100:.2f}% of the {label_total}. "
                      + (f"Average benefit ${fmt(ben / count)} a year per person. " if count else "") + f"{extra} {NOT_BEN}").replace("  ", " ")}
        if amt >= 10_000_000:
            p["why"] = ("The City's payment goes to the fund as one lump sum, and thousands of retirees in this group share it, "
                        "so each person's share is far under $1M and no single person's benefit is bought by one payment.")
        out.append(p)
    return out


def fund_splits(c):
    s = []
    src_val = {"doc": c["val_doc"], "url": c["val_url"], "page": c["val_pages"], "note": c["src_note"]}
    ids = c["ids"]
    # ---- shortfall box
    s.append({
        "target": {"by": "id", "id": PRE + ids["short"]}, "expect_amount": c["short_amt"], "mode": "budget_split",
        "pieces": share_pieces(c["short_amt"], c["groups"], src_val, c["ben_label"]),
        "residual": {"name": "Rounding", "why": None},
        "note": c["short_note"] + " " + NOT_BEN,
        "side": c["short_side"]})
    # ---- normal cost box
    pcs = []
    for t in c["tiers"]:
        p = {"name": f"{t['name']}: {fmt(t['count'])} active members", "amount": t["net_nc"], "basis": t.get("basis", "gov_estimate"),
             "source": {"doc": c["val_doc"], "url": c["val_url"], "page": t["page"], "note": t["src_note"]},
             "count": t["count"], "unit_amount": round(t["net_nc"] / t["count"], 2),
             "unit_label": "active members (net normal cost each)",
             "note": t["note"]}
        if t["net_nc"] >= 10_000_000:
            p["why"] = ("The fund's actuary prints this cost for the whole group, and it is spread over thousands of working "
                        "members, so each member's cost is far under $1M and the City does not publish it person by person.")
        pcs.append(p)
    s.append({
        "target": {"by": "id", "id": PRE + ids["nc"]}, "expect_amount": c["nc_amt"], "mode": "budget_split",
        "pieces": pcs, "residual": {"name": "Rounding", "why": None},
        "note": c["nc_note"], "side": c["nc_side"]})
    # ---- advance line
    s.append({
        "target": {"by": "id", "id": PRE + ids["adv"]}, "expect_amount": c["adv_amt"], "mode": "budget_split",
        "pieces": [{"name": c["adv_name"], "amount": c["adv_amt"], "basis": "tied",
                    "source": {"doc": c["adv_doc"], "url": c["val_url"], "page": c["adv_page"]},
                    "why": ("This is money the City chooses to pay on top of what the law requires, so the fund has more savings "
                            "and the shortfall grows more slowly, and it goes into the fund as one payment."),
                    "note": c["adv_note"]}],
        "note": c["adv_note"], "side": c["adv_side"]})
    return s


FUNDS = []


def add_fund(c):
    FUNDS.append(c)


def write():
    splits = []
    for c in FUNDS:
        splits += fund_splits(c)
    json.dump({"meta": {"author": "pensions detail agent",
                        "description": "Public detail under each City pension fund: benefit groups (count x share, proxy), "
                                       "active members by tier, advance payment notes, funded status as side info.",
                        "built_by": "scripts/pensions_tree_funds.py"}, "splits": splits},
              open(OUT, "w"), indent=1)
    print("wrote", OUT, len(splits), "splits")


