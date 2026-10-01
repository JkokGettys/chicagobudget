"""Audit 2: the 30 largest leaves >= $10M per government with path, amount, basis, why sentence, and a flag when the sentence looks wrong."""
import json, re, collections
from treeaudit_common import *

AIRPORT = re.compile(r"airport|runway|terminal|o'hare|midway|aviation", re.I)
BIGCOMP = re.compile(r"a few big companies|contracts|company|companies|payment records", re.I)
PEN = re.compile(r"retirement fund|retired|pension", re.I)
BOND = re.compile(r"bond", re.I)
GRANTRES = re.compile(r"promises of (grant|federal) money", re.I)
GENERIC = ["The public budget lists this as one amount, and we could not find public records that split it further.",
           "The budget gives one amount for this kind of contract, and the public payment records do not split it into smaller pieces tied to this line.",
           "The budget sets aside one amount for building work, and the project-by-project list is not published with it.",
           "This is one budget amount for a kind of worker pay, and the City does not publish it split into smaller pieces.",
           "The budget gives this program one amount and does not list what each piece of it buys.",
           "Overtime is paid hour by hour as it happens, so the budget only sets one total for the year."]

def flag(r, path):
    """Return a short flag string if the why sentence does not fit the box, else ''."""
    w = r["why_cant_go_deeper"] or ""
    wl = w.lower()
    nm = (r["name"] + " " + path).lower()
    f = []
    if not w: return "NO SENTENCE"
    if w in GENERIC: f.append("generic fallback")
    if AIRPORT.search(w) and not re.search(r"airport|o'hare|midway|aviation|faa", nm): f.append("airport sentence on a non-airport box")
    if re.search(r"a few big companies each get one large contract", wl) and not re.search(r"contract|vendor|payee|professional|services|construction|repair|maintenance|electric|gas|fuel|water|material|supplies|equipment|drugs|hardware|rental", nm): f.append("contracts sentence on a non-contract box")
    if re.search(r"a few big companies each get one large contract", wl) and re.search(r"emergency medical|delegate agencies|homeless|youth employment|rehabilitation loans|violence reduction|loans and grants|after school|mentoring|gender based|festival|millennium park|reserve|pension|bond|interest|overtime|salar|wage", nm):
        f.append("contracts sentence on grants to agencies, loans or services, not vendor contracts")
    if re.search(r"a few big companies each get one large contract", wl) and "no matched payee" not in w and re.search(r"highway|construction of buildings", nm):
        f.append("stale: 'no matched payee' sentence was written for this box in the gap audit (section 5)")
    if re.search(r"single big construction jobs", w) and re.search(r"cdc|home investment|collaboration with academia|epidemiology|housing opportunities|cops|homeland|senior center", nm):
        f.append("construction sentence on a non-construction grant reserve")
    if "The City has promises of grant money, but it has not published" in w and False: pass
    if re.search(r"retirement fund", w) and not re.search(r"pension|retire|annuity|shortfall|normal cost|advance", nm): f.append("pension sentence on a non-pension box")
    if re.search(r"one bond", w, re.I) and not re.search(r"bond|series|principal|interest", nm): f.append("bond sentence on a non-bond box")
    if re.search(r"train station|rebuild", w) and not re.search(r"station|transit|fta|cta", nm): f.append("station sentence on another box")
    if re.search(r"moves from one city account", w) and not r["id"].startswith("city-twice"): f.append("'counted twice' sentence outside memo branch")
    if r["id"].startswith("city-twice") and not re.search(r"moves from one|account to another", w): f.append("memo branch with different sentence")
    if re.search(r"These are [\d,]+ ", w) and not r["count"]: f.append("people sentence on box without count")
    return "; ".join(f)

def main(n=30):
    rows = load_nodes(); by = {r["id"]: r for r in rows}
    out = {}
    for root in ROOTS:
        ls = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == root and abs(r["amount_cents"]) >= 10 * M
              and not (r["count"] and r["unit_amount_cents"] is not None and abs(r["unit_amount_cents"]) < M)]
        ls.sort(key=lambda r: -abs(r["amount_cents"]))
        allflag = [(r, flag(r, path_names(by, r["id"]))) for r in ls]
        out[root] = {"n_ge10_leaves": len(ls), "n_flagged": sum(1 for _, f in allflag if f),
                     "flag_dollars_cents": sum(abs(r["amount_cents"]) for r, f in allflag if f),
                     "top": [{"path": path_names(by, r["id"]), "name": r["name"], "id": r["id"], "amount": r["amount_cents"] / 100,
                              "basis": r["basis"], "why": r["why_cant_go_deeper"], "flag": f} for r, f in allflag[:n]],
                     "flagged_all": [{"path": path_names(by, r["id"]), "amount": r["amount_cents"] / 100, "basis": r["basis"],
                                      "why": r["why_cant_go_deeper"], "flag": f} for r, f in allflag if f]}
        print(f"\n### {root}: {len(ls)} leaves >= $10M (count x rate excluded), {out[root]['n_flagged']} flagged (${out[root]['flag_dollars_cents']/1e8:,.1f}M)")
        for i, t in enumerate(out[root]["top"], 1):
            print(f"{i:2}. {t['amount']/1e6:8.1f}M {t['basis'][:6]:6} {t['path'][-95:]}\n      WHY: {(t['why'] or '')[:110]}\n      FLAG: {t['flag']}")
    json.dump(out, open(f"{OUT}/top_leaves.json", "w"), indent=1)
    # sentence reuse: how many distinct sentences cover how many leaves
    why = collections.Counter(); wd = collections.Counter()
    for r in rows:
        if r["is_leaf"] and abs(r["amount_cents"]) >= 10 * M and r["why_cant_go_deeper"]:
            why[r["why_cant_go_deeper"]] += 1; wd[r["why_cant_go_deeper"]] += abs(r["amount_cents"])
    print("\nmost reused sentences:")
    for s, c in why.most_common(8): print(c, f"${wd[s]/1e8:,.0f}M", s[:100])

if __name__ == "__main__":
    main()
