#!/usr/bin/env python3
"""Step 2: parse raw/parks/words.json (from parks_extract.py) into unit tables.

Layout facts (Chicago Park District 2026 Budget Appropriations, PDF pp 76-246):
  * A unit block = title (12pt department / 16pt park, "Name - CODE", sometimes the
    dash/code wrapped), a fund line (11pt "<location> - <fund>"), then an account
    table on the left (word x0 < 288) and an optional positions table on the right.
  * Account row: "611005 - Salary & Wages $a $b $c" = 2024 actual, 2025 budget,
    2026 budget. Summary pages have only 2 amounts (2025, 2026). Negatives are
    "($1,234)" and once "$(5,332,865)".
  * Class subtotal rows (codes ending 000: 610000 Personnel Services, 620000 ...)
    FOLLOW their detail rows (membership is positional, e.g. 625035 Workers Comp
    sits inside Personnel Services on the District Administration summary).
  * "Total" closes the table.
  * Positions row: "TITLE.JOBCODE FTE25 $25 FTE26 $26". Titles can wrap with the
    numbers printed between the two text lines.

Output: raw/parks/units.json
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "parks")
LEFT_MAX_X0 = 288.0
FIRST_PAGE, LAST_PAGE = 76, 246
AMT = re.compile(r"^(\(?\$\(?[\d,]+\)?|-)$")
CODE6 = re.compile(r"^\d{6}$")
FTE = re.compile(r"^\d+\.\d$")
DASH = re.compile(r"^[-\u2013\u2014]+$")
# Headerless 2-column summary tables (2025 budget, 2026 budget; no 2024 actual):
# start page -> (title, code, pages the table spans). They are set in 9-10pt type.
SUMMARY_TABLES = {
    76: ("District Administration Summary", None, (76, 77)),
    102: ("Finance General (All Funds)", "8200", (102,)),
    104: ("Districtwide Summary", None, (104, 105)),
    143: ("Central Region Summary", None, (143,)),
    178: ("North Region Summary", None, (178,)),
    215: ("South Region Summary", None, (215,)),
}
# Page 103 (Grant Park Music Festival) is a full-width 8pt table with a "--" separator
# and 3 value columns ending at x1 ~ 380 / 470 / 560. It gets its own parser.
BIG_SMALL_PAGES = {}
WIDE_PAGES = {103: (8440, [379.5, 469.6, 559.9])}


def is_left(w):
    """Left (account) table word. Tables are sometimes shifted a few points, so use
    the word kind: left amounts end before x=380 (positions amounts end > 420);
    other words are left when they start before x=288 (positions text starts >= 291)."""
    if w[0] == "-":
        return w[1] < LEFT_MAX_X0
    if AMT.match(w[0]):
        return w[2] < 380
    return w[1] < LEFT_MAX_X0


def amt(tok):
    if tok == "-":
        return 0
    v = int(re.sub(r"[^\d]", "", tok))
    return -v if "(" in tok else v


FRAG = re.compile(r"^[\$\(\d,\)]+$")


def merge_fragments(line):
    """pdfplumber sometimes splits one amount into pieces ('$42,' '33' '4,115').
    Re-join numeric fragments that touch (gap < 1pt) on one line, never gluing
    onto an already complete amount. `line` is x-sorted."""
    out = []
    for w in line:
        if out:
            p = out[-1]
            if (FRAG.match(w[0]) and FRAG.match(p[0]) and w[1] - p[2] < 1.0
                    and p[0][-1] in ",$0123456789"
                    and not re.match(r"^\(?\$\(?\d{1,3}(,\d{3})+\)?$", p[0])):
                out[-1] = [p[0] + w[0], p[1], w[2], p[3], p[4]]
                continue
        out.append(list(w))
    return out


def group_lines(words, tol=2.5):
    ws = sorted(words, key=lambda w: (w[3], w[1]))
    out, cur, ct = [], [], None
    for w in ws:
        if ct is None or abs(w[3] - ct) <= tol:
            cur.append(w)
            if ct is None:
                ct = w[3]
        else:
            out.append(cur)
            cur, ct = [w], w[3]
    if cur:
        out.append(cur)
    return [merge_fragments(sorted(l, key=lambda w: w[1])) for l in out]


def assign_cols(amt_words, colx):
    """Map amount words to columns by right edge (x1). Missing cells stay None."""
    vals = [None] * len(colx)
    for w in amt_words:
        j = min(range(len(colx)), key=lambda k: abs(colx[k] - w[2]))
        if abs(colx[j] - w[2]) > 14 or vals[j] is not None:
            return None
        vals[j] = amt(w[0])
    return vals


def parse_left_lines(lines, unit, pg, problems):
    """Parse account rows from grouped left-column lines into unit (handles wraps,
    blank cells and the Total row). Returns True once the Total row is seen."""
    if unit["colx"] is None:
        unit["colx"] = [223.3, 259.4, 295.6][-unit["ncols"]:]
    colx = unit["colx"]
    last = unit["accounts"][-1] if unit["accounts"] else None
    for ln in lines:
        toks = [w[0] for w in ln]
        if toks[0] == "Account":
            xs = [w[2] for w in ln if w[0] in ("Actual", "Budget")]
            if len(xs) == unit["ncols"]:
                unit["colx"] = colx = xs
            continue
        if toks[0] == "Positions":
            continue
        awords = [w for w in ln if AMT.match(w[0])]
        if toks[0] == "Total" and len(toks) > 1 and len(awords) == len(toks) - 1:
            v = assign_cols(awords, colx)
            if v is None:
                problems.append(f"p{pg} {unit['title']}: bad Total row {toks}")
            else:
                unit["total"] = v
            unit["wrap_open"] = False
            return True
        garbled = bool(re.match(r"^[A-Za-z]\d{5}$", toks[0]) and len(toks) > 1 and DASH.match(toks[1]))
        if CODE6.match(toks[0]) or garbled:
            i = 1
            if i < len(toks) and DASH.match(toks[i]):
                i += 1
            j = len(toks)
            while j - 1 >= (i if garbled else i + 1) and AMT.match(toks[j - 1]):
                j -= 1
            name = toks[i:j]
            rest = ln[j:]
            row = {"code": toks[0], "name": " ".join(name), "values": None, "page": pg}
            if garbled:
                # PDF typo: p87 prints 'v62710 -' with no account name (a Fixed Asset
                # row inside class 627000). Keep it, flag it, never guess the code.
                row["code"] = "UNKNOWN"
                row["name"] = "(unlabeled in PDF; code printed as '%s')" % toks[0]
                row["flag"] = "garbled_code"
                problems.append(f"p{pg} {unit['title']}: garbled account code {toks[0]!r} kept as UNKNOWN")
            if rest:
                v = assign_cols(rest, colx)
                if v is None:
                    problems.append(f"p{pg} {unit['title']}: unassignable amounts {toks}")
                    continue
                row["values"] = v
                unit["wrap_open"] = False
            else:
                unit["wrap_open"] = True  # wrapped row: amounts on the next line
            unit["accounts"].append(row)
            last = row
            continue
        if last is not None and last["values"] is None and awords and len(awords) == len(toks):
            v = assign_cols(awords, colx)
            if v is None:
                problems.append(f"p{pg} {unit['title']}: unassignable wrapped amounts {toks}")
            else:
                last["values"] = v
            continue
        if last is not None and unit.get("wrap_open") and last["values"] is not None and not awords:
            last["name"] += " " + " ".join(toks)
            unit["wrap_open"] = False
    return False


def parse_title(words):
    ws = sorted(words, key=lambda w: (w[3], w[1]))
    txt = " ".join(w[0] for w in ws).replace("\u2013", "-")
    txt = re.sub(r"\s+", " ", txt).strip()
    m = re.search(r"(\d{4})\s*-?\s*$", txt)
    code = m.group(1) if m else None
    name = txt[:m.start()] if m else txt
    name = re.sub(r"\s*-\s*$", "", name.strip()).strip()
    return name, code


def split_fundline(s):
    s = re.sub(r"\s+", " ", s.replace("\u2013", "-"))
    parts = [p.strip() for p in s.split(" - ")]
    fund = parts[-1].replace("Funds", "Fund")
    return " - ".join(parts[:-1]), fund


def region_for(pg):
    if 144 <= pg <= 170: return "Central Region"
    if 179 <= pg <= 208: return "North Region"
    if 216 <= pg <= 246: return "South Region"
    return None


class PosParser:
    """Line-oriented positions parser. Feed right-column lines in order."""
    def __init__(self):
        self.name, self.nums, self.recs, self.done = [], None, [], False

    def feed(self, toks):
        if self.done or not toks:
            return
        if toks[0] == "Total" and len(toks) == 5 and not self.name:
            f25, b25, f26, b26 = toks[1:]
            self.recs.append({"total": True, "fte2025": float(f25), "budget2025": amt(b25),
                              "fte2026": float(f26), "budget2026": amt(b26)})
            self.done = True
            return
        isnum = lambda t: bool(FTE.match(t) or (AMT.match(t) and t != "-"))
        nums = [t for t in toks if isnum(t)]
        text = [t for t in toks if not isnum(t)]
        if nums:
            if len(nums) != 4:
                self.recs.append({"error": " ".join(toks)})
                return
            self.nums = nums
        self.name.extend(text)
        full = " ".join(self.name)
        if self.nums and re.search(r"\.\d{3,5}$", full):
            m = re.match(r"^(.*)\.(\d{3,5})$", full)
            f25, b25, f26, b26 = self.nums
            self.recs.append({"title": m.group(1).strip(), "job_code": m.group(2),
                              "fte2025": float(f25), "budget2025": amt(b25),
                              "fte2026": float(f26), "budget2026": amt(b26)})
            self.name, self.nums = [], None


def parse_summary(words, start, title, code, span, problems):
    """Parse a 2-column summary table (9-10pt text) into a unit dict."""
    u = {"title": title, "unit_code": code, "location": "Summary", "fund": "All Funds",
         "region": region_for(start), "page": start, "ncols": 2, "accounts": [], "total": None,
         "positions": [], "is_summary": True}
    colx = None
    for pg in span:
        W = [w for w in words[str(pg)] if 8.5 <= w[4] <= 12.5]
        for ln in group_lines(W):
            toks = [w[0] for w in ln]
            if toks[0] == "Account":
                xs = [w[2] for w in ln if w[0] == "Budget"]
                if len(xs) == 2:
                    colx = xs
                continue
            if colx is None:
                continue
            awords = [w for w in ln if AMT.match(w[0])]
            if toks[0] == "Total" and len(awords) == len(toks) - 1 and len(awords) == 2:
                u["total"] = assign_cols(awords, colx)
                return u
            if CODE6.match(toks[0]):
                j = len(toks)
                while j - 1 > 1 and AMT.match(toks[j - 1]):
                    j -= 1
                i = 2 if len(toks) > 1 and DASH.match(toks[1]) else 1
                v = assign_cols(ln[j:], colx)
                if v is None or None in v:
                    problems.append(f"p{pg} {title}: bad summary row {toks}")
                    continue
                u["accounts"].append({"code": toks[0], "name": " ".join(toks[i:j]), "values": v, "page": pg})
    problems.append(f"{title}: no Total row found")
    return u


def parse_wide(words, pg, code, colx, problems):
    W = [w for w in words[str(pg)] if w[4] <= 8.5]
    title = "Grant Park Music Festival"
    u = {"title": title, "unit_code": code, "location": "Districtwide", "fund": "Corporate Fund",
         "region": None, "page": pg, "ncols": 3, "accounts": [], "total": None, "positions": []}
    for ln in group_lines(W):
        toks = [w[0] for w in ln]
        awords = [w for w in ln if AMT.match(w[0])]
        if toks[0] == "Total" and len(awords) == 3:
            u["total"] = assign_cols(awords, colx)
        elif CODE6.match(toks[0]) and len(awords) == 3:
            j = len(toks) - 3
            i = 2 if DASH.match(toks[1]) else 1
            u["accounts"].append({"code": toks[0], "name": " ".join(toks[i:j]),
                                  "values": assign_cols(awords, colx), "page": pg})
    if u["total"] is None:
        problems.append(f"p{pg}: no Total row")
    return u


def find_heads(pg, W):
    """Return list of (top, title_words, fundline_text) for unit headers on this page."""
    heads = []
    mid = [w for w in W if 10.5 <= w[4] <= 12.5 and w[1] < 400]
    for ln in group_lines(mid):
        txt = re.sub(r"\s+", " ", " ".join(w[0] for w in ln)).strip()
        if (re.search(r"Fund[s]?$", txt) and re.search(r"[-\u2013]", txt) and "APPROPRIATIONS" not in txt
                and not re.search(r"\d{4}$", txt)):
            ftop = ln[0][3]
            tw = [w for w in W if 11.6 <= w[4] <= 20.0 and ftop - 40 <= w[3] < ftop - 5 and w[1] < 400]
            if tw:
                heads.append((ftop, tw, txt))
    return heads


def main():
    words = json.load(open(os.path.join(RAW, "words.json")))
    units, problems = [], []
    cur = None
    for pg in range(FIRST_PAGE, LAST_PAGE + 1):
        W = words[str(pg)]
        small = [w for w in W if w[4] <= BIG_SMALL_PAGES.get(pg, 5.5)]
        heads = find_heads(pg, W)
        acct_hdr = [ln for ln in group_lines([w for w in small if is_left(w)]) if ln[0][0] == "Account"]
        blocks = []  # (unit, y0, y1)
        if cur is not None and cur["open"]:
            blocks.append((cur, 0, heads[0][0] if heads else 9999))
        for i, (ftop, tw, txt) in enumerate(heads):
            title, code = parse_title(tw)
            loc, fund = split_fundline(txt)
            # a following title sits ~20pt above its fund line, so cut blocks there
            end = min(w[3] for w in heads[i + 1][1]) - 1 if i + 1 < len(heads) else 9999
            hd = [ln for ln in acct_hdr if ftop <= ln[0][3] < (heads[i + 1][0] if i + 1 < len(heads) else 9999)]
            ncols = 3 if hd and any(w[0] == "2024" for w in hd[0]) else 2
            cur = {"title": title, "unit_code": code, "location": loc, "fund": fund,
                   "region": region_for(pg), "page": pg, "ncols": ncols, "accounts": [], "total": None,
                   "open": True, "positions": [], "colx": None}
            units.append(cur)
            blocks.append((cur, ftop, end))
        for unit, y0, y1 in blocks:
            if not unit["open"]:
                continue
            lw = [w for w in small if is_left(w) and y0 <= w[3] < y1]
            if parse_left_lines(group_lines(lw), unit, pg, problems):
                unit["open"] = False
            rw = [w for w in small if not is_left(w) and y0 <= w[3] < y1]
            if rw:
                pp = unit.setdefault("_pp", None)
                if unit["_pp"] is None:
                    unit["_pp"] = PosParser()
                    unit["_pp_state"] = [[], None, False]
                pp = unit["_pp"]
                for ln in group_lines(rw):
                    toks = [w[0] for w in ln]
                    if toks[0] == "Positions":
                        continue
                    pp.feed(toks)
    for pg, (code, colx) in WIDE_PAGES.items():
        units.append(parse_wide(words, pg, str(code), colx, problems))
    for start, (title, code, span) in SUMMARY_TABLES.items():
        units.append(parse_summary(words, start, title, code, span, problems))
    for u in units:
        pp = u.pop("_pp", None)
        u.pop("_pp_state", None)
        u.pop("open", None)
        if pp:
            u["positions"] = pp.recs
            if pp.name:
                problems.append(f"p{u['page']} {u['title']}: dangling position text {pp.name}")
    json.dump({"units": units, "problems": problems}, open(os.path.join(RAW, "units.json"), "w"))
    print("units", len(units), "problems", len(problems))
    for p in problems[:30]:
        print(p)


if __name__ == "__main__":
    main()
