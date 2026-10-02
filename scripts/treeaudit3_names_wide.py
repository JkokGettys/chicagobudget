"""Audit 3: wider person-like payee sweep (looser than treeaudit3_names.py, which uses audit 2's logic and reports 0).
Scope: side_info kind vendors_paid items not marked individual. Two groups, counts and dollars only. The strings go to
raw/treeaudit3/names_wide_private.txt (gitignored) for the person who fixes build/payee.py. Nothing printed is a name.
 couple: contains '&' or AND, 3 to 7 plain-letter tokens (a trailing '&' counts), no business word, no contract number.
 artist single: 2 to 4 plain-letter tokens, no business word, and the description says artist grant, residency, exhibition or IAP."""
import json, re, collections, sys, os
from treeaudit3_common import *
sys.path.insert(0, os.path.join(ROOT, "build")); import payee
ORG = {x.rstrip(".") for x in payee.ORG_TOKENS} | {"DBA","LLC","INC","CO","MD","JR","SR","II","III","ESQ","PC","PLLC","LIMITED","LABS","PRODUCTS","GOVERNMENT","DIRECT","GENERAL","OFFICE","SONS","SON","BODY","SHOP","PARK","MARKET","BAKERY","PIANO","TUNING","REPAIR","TOWING","MARCHING","ARTS","PRINTING","TRAVELING","ZOO","SOUND","HEALING","SHIELD","CROSS","BLUE","REPORTING","DEPOSITION","TRIAL","COMPANIES","NURSING","REHAB","BOOKS","RARE","USED","SODABLAST","SANSTORM","WOODCRAFT","DESIGN","CONCRETE","CAFE","SOUPS","SANDWICHES","SALADS","CANDLE","BATH","PHYSICIANS","SURGEONS","ORTHOPAEDIC","SPORTS","CONTEMPORARY","MEMBERSHIP","GLASS","MIRROR","MIRRORS","FENDER","MOBILITY","CPA'S","CPAS","REAVIS","POGUE","HARDIN","WAITE","MARTIN","BELL","HARTIGAN","CONNOR","GOLDMAN","GRANT","LEACH","CATER","EVENTS","DROPOFFS","VOICES","ACME","STUDIO","FELLOWSHIP","METHODIST","ESTATE","FUND","MUSIC","ENTERPRISES","FILE","SERVE","XPRESS","XPRESSS","A","T","AT","&","FEDERAL","AFRS","ALA","AAAE"}
ART = re.compile(r"individual artist|\bIAP\b|practitioner in residence|artist in residence|exhibition agreement|fellowship", re.I)
def run(label):
    c = con(); res = collections.defaultdict(lambda: [set(), 0, 0.0]); priv = []
    for r in c.execute("select extra from side_info where kind='vendors_paid'"):
        for it in json.loads(r["extra"] or "{}").get("items") or []:
            v = it.get("vendor") or ""
            if it.get("is_individual") or "name hidden" in v.lower(): continue
            u = re.sub(r"\s*\d+$", "", v.upper()).strip()
            t = [x.strip(".,") for x in re.split(r"[\s,/()&]+", u) if x.strip(".,")]
            if not t or any(x in ORG for x in t) or not all(re.fullmatch(r"[A-Z'\-]+", x) for x in t): continue
            couple = "&" in v or " AND " in u
            has_c = bool(it.get("contract"))
            if couple and 2 <= len(t) <= 7 and not has_c: k = "couple, no contract number"
            elif (not couple) and 2 <= len(t) <= 4 and ART.search(it.get("description") or ""): k = "artist-grant single name"
            else: continue
            res[k][0].add(v); res[k][1] += 1; res[k][2] += it.get("amount", 0) / 100
            priv.append(f"{k}\t{v}\t{it.get('amount',0)/100:.0f}")
    for k, (s, n, a) in sorted(res.items()): print(f"{label} {k}: {len(s)} payee strings, {n} rows, ${a:,.0f}")
    return priv
if __name__ == "__main__":
    priv = run("now" if "prev" not in OUT else "prev")
    open(os.path.join(OUT, "names_wide_private.txt"), "w").write("\n".join(sorted(set(priv))))
