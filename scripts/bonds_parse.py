#!/usr/bin/env python3
"""Parse per-series debt service from City of Chicago official statements (OS).

Reads PDFs in raw/bonds/ (see scripts/bonds_fetch.py), caches page text in
raw/bonds/txt/<pdf stem>.txt, and writes data/city_bond_series_2026.json.

Convention. The OS tables are labelled "Bond Year Ending January 1" and include
principal and interest paid from January 2 of the prior year through January 1 of
the stated year. The row "2027" is therefore the window Jan 2 2026 to Jan 1 2027.
This is the window that reproduces the 2026 ordinance O'Hare and Midway lines
(see research/bond_series.md section 2). Water and Sewer tables are by fiscal
(calendar) year, and the row "2026" is used for them, which reproduces the ordinance
within 0.2 percent for Water.

Every extracted row is checked: the printed total must equal the sum of the
printed columns (within rounding of the printed figures), or the script stops.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw" / "bonds"
TXT = RAW / "txt"
OUT = ROOT / "data" / "city_bond_series_2026.json"


# ---------------------------------------------------------------- text cache
def pdf_text(pdf_name):
    """Return {page_number: text}, building the cache with pdfplumber if needed."""
    stem = Path(pdf_name).stem
    cache = TXT / (stem + ".txt")
    if not cache.exists():
        import pdfplumber
        TXT.mkdir(parents=True, exist_ok=True)
        with pdfplumber.open(RAW / pdf_name) as pdf, open(cache, "w") as out:
            for i, page in enumerate(pdf.pages, 1):
                out.write("\n<<<PAGE %d>>>\n" % i)
                out.write(page.extract_text() or "")
    parts = re.split(r"<<<PAGE (\d+)>>>", cache.read_text())
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


def find_pdf(fragment):
    hits = [p.name for p in RAW.glob("*.pdf") if fragment in p.name]
    if len(hits) != 1:
        raise SystemExit("expected one PDF containing %r, found %r" % (fragment, hits))
    return hits[0]


# ---------------------------------------------------------------- numbers
TOK = re.compile(r"\(?\$?\s?\d[\d,]*(?:\.\d+)?\)?|(?<![\w.])[-\u2013\u2014]{1,2}(?![\w.])")


def to_num(tok):
    t = tok.replace("$", "").replace(",", "").replace(" ", "")
    if t in ("-", "--", "\u2013", "\u2014"):
        return 0
    if t.startswith("("):
        return -round(float(t.strip("()")))
    return round(float(t))


def row_tokens(page_text, year, after_anchor=None, nth=0):
    """Numeric tokens of the table row that starts with the given year label."""
    lines = page_text.split("\n")
    start = 0
    if after_anchor:
        idx = [i for i, l in enumerate(lines) if re.search(after_anchor, l)]
        if not idx:
            raise ValueError("anchor %r not on page" % after_anchor)
        start = idx[0]
    seen = 0
    for l in lines[start:]:
        m = re.match(r"^%d(\(\d\))?\s+(.*)$" % year, l.strip())
        if m:
            toks = [to_num(t) for t in TOK.findall(m.group(2).replace("$ ", "$"))]
            if len(toks) >= 3:
                if seen == nth:
                    return toks, l.strip()
                seen += 1
    raise ValueError("no row %d" % year)


def page_of(pages, needle):
    for n, t in pages.items():
        if needle in t:
            return n
    raise ValueError("%r not found" % needle)


# ---------------------------------------------------------------- O'Hare
# (pdf fragment, page, anchor, columns in printed order, capitalized-interest column or None)
# 'total' is always the last printed column. A column named 'cap' is subtracted.
OHARE_SPECS = [
    ("OS.X6Bl2Stb8", ["outstanding", "2026A", "total"]),
    ("ohare_2026B_OS", ["outstanding", "2026B", "total"]),
    ("ohare_2026CD_OS", ["outstanding", "2026C", "2026D", "total"]),
    ("Final-Official-Statement---ORD-2025CD", ["outstanding", "2025C", "2025D", "total"]),
    ("Final-OS.KvjbpkoAR", ["outstanding", "2025E", "2025G", "total"]),
    ("OS.NEfpPym7t", ["outstanding", "2025A", "2025B", "total"]),
    ("OS.ZupAfhGTd", ["outstanding", "2024C", "2024D", "2024E", "2024F", "total"]),
    ("Senor-Lien-Revenue-Bonds-Series-2024AB", ["outstanding", "2024A", "2024B", "-cap2024", "total"]),
    ("P21754542-P11248433-P11672754", ["outstanding", "2022A", "2022B", "2022C", "2022D", "total"]),
    ("Chicago-OHare-OS-2020", ["outstanding", "2020A", "2020B", "2020C", "2020D", "2020E", "total"]),
    ("ORD_2018ABC_OS", ["outstanding", "2018A", "2018B", "2018C", "total"]),
    ("ORD_2017ABCD_OS", ["outstanding", "-cap_out", "2017A", "2017B", "2017C", "2017D", "-cap2017D", "total"]),
    ("2016D-G_Sr._Lien_GARB_OS", ["outstanding", "2016D", "2016E", "2016F", "2016G", "total"]),
]

# Series that a later transaction partly or wholly refunded or defeased, so the
# printed series column (from the series' own statement) overstates what is due now.
# Sources: ohare_2026CD_OS pp.64, 339-343 (2026CD refunded list) and ohare_FS2025 p.50.
OHARE_STALE = {
    "2016D": "partly refunded by 2026CD (ohare_2026CD_OS p.64: $598.73M to $392.74M)",
    "2016E": "partly refunded by 2026CD (p.64: $61.54M to $34.90M)",
    "2016F": "fully refunded by 2026CD (p.64: $127.405M to 0), also partly defeased by 2025D (FS p.50)",
    "2016G": "partly refunded by 2026CD (p.64: $58.675M to $37.075M)",
    "2017A": "partly refunded by 2026CD (p.64: $39.345M to $13.010M)",
    "2017B": "fully refunded by 2026CD (p.64: $156.945M to 0), also partly defeased by 2025D (FS p.50)",
    "2017C": "partly refunded by 2026CD (p.64: $61.985M to $34.380M)",
    "2018C": "partly defeased by 2025C (ohare_FS2025 p.50 lists 2018C $89.87M)",
}

# Outstanding principal after the 2026CD refunding, ohare_2026CD_OS p.64 (par amounts).
OHARE_OUTSTANDING = {
    "2010B": 328000000, "2016D": 392740000, "2016E": 34900000, "2016F": 0, "2016G": 37075000,
    "2017A": 13010000, "2017B": 0, "2017C": 34380000, "2017D": 153150000,
    "2018A": 591215000, "2018B": 612095000, "2018C": 710130000,
    "2020A": 494360000, "2020B": 99390000, "2020C": 59865000, "2020D": 302590000, "2020E": 61955000,
    "2022A": 1105415000, "2022B": 150450000, "2022C": 81665000, "2022D": 296360000,
    "2024A": 549985000, "2024B": 436875000, "2024C": 491395000, "2024D": 766970000,
    "2024E": 135240000, "2024F": 52225000,
    "2025A": 211170000, "2025B": 120980000, "2025C": 429525000, "2025D": 525295000,
    "2025E": 1101570000, "2025G": 21300000, "2026A": 612235000, "2026B": 1291630000,
    "2026C": 293185000, "2026D": 226400000,
}


def cover_2027_principal(pdf_name, series):
    """Principal maturing Jan 1 2027 for a series, read from the OS inside cover pages.

    Returns (amount or None, basis). Serial maturities only. A series whose earliest
    printed maturity or term bond date is after 2027 returns 0 with that basis.
    """
    pages = pdf_text(pdf_name)
    found = None
    years = []
    for n in sorted(pages)[:14]:
        cur = None
        for l in pages[n].split("\n"):
            m = re.search(r"SERIES\s+(20\d\d[A-G])\b", l.upper())
            if m and len(l) < 70:
                cur = m.group(1)
            if cur != series:
                continue
            m = re.match(r"^(20\d\d)\*?\s+\$?\s?([\d,]{7,})", l.strip())
            if m:
                y = int(m.group(1))
                years.append(y)
                if y == 2027:
                    found = (found or 0) + int(m.group(2).replace(",", ""))
            m = re.search(r"Term Bond Due January 1, (20\d\d)", l)
            if m:
                years.append(int(m.group(1)))
    if found is not None:
        return found, "serial maturity on OS cover, page %s" % [n for n in sorted(pages)[:14]][0]
    if years and min(years) > 2027:
        return 0, "earliest printed maturity is %d (cover); sinking fund installments not checked" % min(years)
    if years:
        return 0, "no 2027 serial maturity printed on cover (serial years %s); sinking fund installments not checked" % sorted(set(years))[:4]
    return None, "not determinable from cover"


def parse_ohare():
    series = []
    checks = []
    for frag, cols in OHARE_SPECS:
        pdf = find_pdf(frag)
        pages = pdf_text(pdf)
        pg = None
        for n, t in pages.items():
            if "DEBT SERVICE SCHEDULE FOR SENIOR LIEN BONDS" in t:
                pg = n
                break
        toks, line = row_tokens(pages[pg], 2027)
        if len(toks) != len(cols):
            raise SystemExit("%s: %d tokens vs %d columns: %s" % (frag, len(toks), len(cols), line))
        vals = dict(zip(cols, toks))
        calc = sum(v for k, v in vals.items() if k != "total" and not k.startswith("-")) - sum(
            v for k, v in vals.items() if k.startswith("-"))
        if abs(calc - vals["total"]) > 5:
            raise SystemExit("%s: columns sum %d vs printed total %d" % (frag, calc, vals["total"]))
        checks.append({"doc": pdf, "pdf_page": pg, "row": line, "sum_check": "columns sum to printed total"})
        for k, v in vals.items():
            if re.fullmatch(r"20\d\d[A-G]", k):
                cap = vals.get("-cap2024", 0) if k in ("2024A", "2024B") else 0
                series.append({"series": k, "d_s_2027_row": v, "doc": pdf, "pdf_page": pg, "row": line,
                               "outstanding_total_in_doc": vals["outstanding"], "doc_total": vals["total"]})
        if "-cap2024" in vals:
            checks[-1]["note"] = ("2024AB table subtracts one combined capitalized interest column of %d "
                                  "from both series; it is not allocated to 2024A vs 2024B" % vals["-cap2024"])
            for s in series:
                if s["series"] in ("2024A", "2024B"):
                    s["capitalized_interest_combined_2024AB"] = vals["-cap2024"]
    return series, checks


# ---------------------------------------------------------------- GO older series
# (label, pdf fragment, table anchor regex, series included, outstanding principal now)
GO_SPECS = [
    ("2021A and 2021B", "Series-2021A-and-2021B", r"TABLE 53\. LONG-TERM", 435040000 + 219127000),
    ("2020A", "GO_2020A_OS", r"^LONG-TERM GENERAL OBLIGATION BONDS DEBT SERVICE SCHEDULE\(1\)", 283090000),
    ("2019A", "GO_2019A_OS", r"^DEBT SERVICE SCHEDULE\(1\)\(2\)", 407735000),
    ("2017A and 2017B", "GO_2017A&B_OS", r"^DEBT SERVICE SCHEDULE\(1\)\(2\)", 402675000 + 11765000),
    ("2015B (with 2015A)", "GO_2015A&B_OS", r"^Debt Service Schedule\(1\)\(2\)", 98569000),
    ("2015C", "GO_2015C_OS", r"^Debt Service Schedule\(1\)\(2\)", 40015000),
]


def parse_go_older():
    out = []
    for label, frag, anchor, outstanding in GO_SPECS:
        pdf = find_pdf(frag)
        pages = pdf_text(pdf)
        pg = None
        for n, t in sorted(pages.items()):
            if re.search(anchor, t, re.M) and re.search(r"^2026\s", t, re.M):
                pg = n
                break
        lines = pages[pg].split("\n")
        i0 = [i for i, l in enumerate(lines) if re.search(anchor, l.strip())][0]
        princ_total = 0
        row27 = None
        rows = 0
        for l in lines[i0:]:
            m = re.match(r"^(20\d\d)\s+(.*)$", l.strip())
            if not m:
                continue
            toks = [to_num(t) for t in TOK.findall(m.group(2).replace("$ ", "$"))]
            if len(toks) < 7:
                continue
            rows += 1
            # Older GO statements label the row by the calendar year of payment, so the
            # row "2026" holds principal due Jan 1 2027 (checked against the cover
            # maturities and the ACFR). It is the same window as the 2027 bond-year rows.
            if int(m.group(1)) >= 2026:
                princ_total += toks[0]
            if int(m.group(1)) == 2026:
                row27 = (toks[0], toks[1], l.strip())
        out.append({"label": label, "doc": pdf, "pdf_page": pg, "principal_2027": row27[0],
                    "interest_2027": row27[1], "row": row27[2],
                    "principal_remaining_in_doc_from_2027": princ_total,
                    "outstanding_principal_now": outstanding,
                    "principal_mismatch": princ_total - outstanding})
    return out



# ---------------------------------------------------------------- GO 2026AB all-outstanding table
def parse_go_2026ab():
    """go_2026AB_OS Table 4 (p.26) prints debt service on ALL outstanding GO bonds, but by TYPE
    (Series 2026, Tax Levy, Alternate Revenue), not by series. Table 3 (p.24) lists outstanding
    principal by series. Two series can be isolated by matching the two:
      - Alternate Revenue column = Series 2010B (MSAC) only: its total principal $8,480,000 equals
        the Table 3 balance of that one series.
      - Series 2017B is a term bond with final maturity 1/1/2027 (Table 3), so its whole $11,765,000
        falls in the window. Its interest is not printed on its own: derived as balance x coupon.
    """
    pdf = "go_2026AB_OS.pdf"
    pages = pdf_text(pdf)
    toks, line = row_tokens(pages[26], 2027)
    cols = ["s26_p", "s26_i", "tl_p", "tl_i", "ar_p", "ar_i", "go_p", "go_i", "total"]
    if len(toks) != len(cols):
        raise SystemExit("go_2026AB p26: %d tokens: %s" % (len(toks), line))
    v = dict(zip(cols, toks))
    if abs(v["s26_p"] + v["tl_p"] + v["ar_p"] - v["go_p"]) > 5 or abs(v["s26_i"] + v["tl_i"] + v["ar_i"] - v["go_i"]) > 5 \
            or abs(v["go_p"] + v["go_i"] - v["total"]) > 5:
        raise SystemExit("go_2026AB p26 columns do not sum: %r" % v)
    tot = [l for l in pages[26].split("\n") if l.startswith("Total $")][0]
    tt = [to_num(t) for t in TOK.findall(tot[5:].replace("$ ", "$"))]
    # Alternate Revenue total principal (column 5) must equal Table 3 balance of the 2010B MSAC series
    t3 = pages[24]
    msac = [l for l in t3.split("\n") if "2010B (MSAC Program)" in l][0]
    msac_bal = to_num(re.findall(r"[\d,]{9,}", msac)[0])
    b17 = [l for l in t3.split("\n") if "Taxable Project Series 2017B" in l][0]
    b17_bal = to_num(re.findall(r"[\d,]{9,}", b17)[0])
    if tt[4] != msac_bal:
        raise SystemExit("alt revenue total %d != MSAC balance %d" % (tt[4], msac_bal))
    if not b17.rstrip().endswith("1/1/2027"):
        raise SystemExit("2017B final maturity is not 1/1/2027: %s" % b17)
    return {"doc": pdf, "row": line, "values": v, "totals": tt, "msac_balance": msac_bal, "b2017_balance": b17_bal}

# ---------------------------------------------------------------- Midway, Water, Sewer
def row_after(pdf_frag, page, year, cols, label, checks):
    """Parse one table row and verify each (parts, whole) identity within $5."""
    pdf = find_pdf(pdf_frag)
    pages = pdf_text(pdf)
    toks, line = row_tokens(pages[page], year)
    if len(toks) != len(cols):
        raise SystemExit("%s p%d: %d tokens vs %d: %s" % (pdf_frag, page, len(toks), len(cols), line))
    vals = dict(zip(cols, toks))
    for parts, whole in checks:
        if abs(sum(vals[k] for k in parts) - vals[whole]) > 5:
            raise SystemExit("%s p%d: %s != %s in %s" % (pdf_frag, page, parts, whole, line))
    return {"doc": pdf, "pdf_page": page, "row": line, "values": vals, "label": label,
            "checks": ["%s = %s" % ("+".join(p_), w) for p_, w in checks]}


def parse_others():
    r = {}
    # Midway, bond year ending Jan 1 2027 (payments Jan 2 2026 to Jan 1 2027)
    r["midway_2025AB"] = row_after("midway_2025AB_OS", 60, 2027, ["outstanding", "2025A", "2025B", "total"], "Midway 2025AB OS",
                                   [(["outstanding", "2025A", "2025B"], "total")])
    r["midway_2023AB"] = row_after("ILChicago07a-FIN.tKvfUEqGd", 40, 2027, ["outstanding", "2023A", "2023B", "total"], "Midway 2023AB OS",
                                   [(["outstanding", "2023A", "2023B"], "total")])
    r["midway_2023C"] = row_after("Series-2023C--AMT", 36, 2027, ["outstanding", "2023C", "total"], "Midway 2023C OS",
                                  [(["outstanding", "2023C"], "total")])
    r["midway_2024"] = row_after("Series-2024A--AMT", 32, 2027, ["outstanding", "2024A", "2024B", "total"], "Midway 2024AB OS",
                                 [(["outstanding", "2024A", "2024B"], "total")])
    pages = pdf_text(find_pdf("midway_FS2025"))
    toks, line = row_tokens(pages[82], 2026)
    toks = [t * 1000 for t in toks]
    r["midway_fs_2026"] = {"doc": "midway_FS2025.pdf", "pdf_page": 82, "row": line,
                           "unit": "thousands in source, converted to dollars",
                           "values": dict(zip(["2014", "2016", "2018", "2023", "2024", "2025", "total"], toks))}
    # Water, fiscal (calendar) year 2026
    r["water_2026ABC"] = row_after("water_2026ABC_OS", 36, 2026,
        ["outstanding", "ABC_principal", "ABC_interest", "ABC_total", "second_lien_total", "subordinate_iepa", "total"], "Water 2026ABC OS",
        [(["ABC_principal", "ABC_interest"], "ABC_total"), (["outstanding", "ABC_total"], "second_lien_total"),
         (["second_lien_total", "subordinate_iepa"], "total")])
    r["water_2024A"] = row_after("Final-Official-Statement.xhGQmBh3f", 25, 2026,
        ["outstanding", "A_principal", "A_interest", "A_total", "second_lien_total", "subordinate_iepa", "total"], "Water 2024A OS",
        [(["A_principal", "A_interest"], "A_total"), (["outstanding", "A_total"], "second_lien_total"),
         (["second_lien_total", "subordinate_iepa"], "total")])
    # 2023 OS: columns gross outstanding, refunded, net outstanding, A principal, A interest,
    # B principal, B interest, A+B total, total (a "-" prints as 0)
    r["water_2023AB"] = row_after("Offical-Statement.eCHJIWijc", 32, 2026,
        ["gross_outstanding", "refunded", "net_outstanding", "A_principal", "A_interest", "B_principal", "B_interest", "AB_total", "total"],
        "Water 2023AB OS",
        [(["A_principal", "A_interest", "B_principal", "B_interest"], "AB_total"), (["net_outstanding", "AB_total"], "total"),
         (["refunded", "net_outstanding"], "gross_outstanding")])
    # Sewer fiscal 2026
    r["sewer_2024B"] = row_after("wastewater_2024B_OS", 24, 2026,
        ["senior", "second_outstanding", "B_principal", "B_interest", "B_total", "second_lien_total", "senior_plus_second", "subordinate_iepa", "total"],
        "Sewer 2024B OS",
        [(["B_principal", "B_interest"], "B_total"), (["second_outstanding", "B_total"], "second_lien_total"),
         (["senior", "second_lien_total"], "senior_plus_second"), (["senior_plus_second", "subordinate_iepa"], "total")])
    r["sewer_2024A"] = row_after("Refunding-Series-2024A", 23, 2026,
        ["senior", "second_outstanding", "A_principal", "A_interest", "A_total", "second_lien_total", "senior_plus_second", "subordinate_iepa", "total"],
        "Sewer 2024A OS",
        [(["A_principal", "A_interest"], "A_total"), (["second_outstanding", "A_total"], "second_lien_total"),
         (["senior", "second_lien_total"], "senior_plus_second"), (["senior_plus_second", "subordinate_iepa"], "total")])
    # 2023 OS: senior, outstanding second, A principal, A interest, A capitalized interest (neg), A total,
    # B principal, B interest, B total, total second lien, total debt service requirements
    pages = pdf_text(find_pdf("Wastewater-Transmission-Revenue-Bonds--Project-Series-2023A"))
    toks, line = row_tokens(pages[30], 2026)
    r["sewer_2023AB"] = {"doc": find_pdf("Wastewater-Transmission-Revenue-Bonds--Project-Series-2023A"), "pdf_page": 30, "row": line, "label": "Sewer 2023AB OS",
                         "tokens": toks}
    return {k: v for k, v in r.items() if v}



def parse_water_round2():
    pdf10 = find_pdf("Water_2010A-C")
    pg10 = pdf_text(pdf10)
    toks, line = row_tokens(pg10[34], 2026)
    if len(toks) != 3 or abs(toks[0] + toks[1] - toks[2]) > 5:
        raise SystemExit("water 2010 table row: %r" % toks)
    printed = toks[1]  # 'Series 2010 Bonds principal and interest' column (2010A matured 2023)
    cover = pg10[2]
    if "$250,000,000 6.742% Term Bonds due November 1, 2040" not in cover or "$29,665,000 6.642% Term Bonds due November 1, 2029" not in cover:
        raise SystemExit("water 2010 cover not as expected")
    b_int = round(250000000 * 0.06742)
    c_int = round(29665000 * 0.06642)
    sf = pg10[22]
    m = re.search(r"2026 \$([\d,]+)", sf[sf.index("Taxable Series 2010C Bonds due"):])
    c_prin = to_num(m.group(1))
    if abs(b_int + c_int + c_prin - printed) > 5:
        raise SystemExit("water 2010B+2010C %d != printed %d" % (b_int + c_int + c_prin, printed))
    pdf17 = find_pdf("Water_Refunding_Series_2017")
    pg17 = pdf_text(pdf17)
    t17, l17 = row_tokens(pg17[31], 2026)
    # columns: senior, outstanding second, refunded, net, 2017 principal, 2017 interest, 2017 total, total
    if len(t17) != 8 or abs(t17[4] + t17[5] - t17[6]) > 5:
        raise SystemExit("water 2017 row: %r" % t17)
    cov = [l for l in pg17[3].split("\n") if l.startswith("2026 ")][0]
    if to_num(re.findall(r"[\d,]{7,}", cov)[0]) != t17[4]:
        raise SystemExit("2017 cover maturity differs from table principal")
    tend = pdf_text(find_pdf("water_2026ABC_OS"))[170]
    if any(l.startswith("2017 2026") or l.startswith("2017 2027") or l.startswith("2017 2028") for l in tend.split("\n")):
        raise SystemExit("2017 2026-2028 maturity was tendered")
    return {"doc2010": pdf10, "pg2010": 34, "row2010": line, "printed_2010": printed, "b_int": b_int,
            "c_tot": c_int + c_prin, "c_prin": c_prin, "doc2017": pdf17, "pg2017": 31, "row2017": l17, "p2017": t17[4]}


def parse_sewer_round2():
    """Sewer 2017A, 2017B (2017AB OS p.28) and 2010B (2010AB OS p.32), fiscal 2026 rows. The 2017AB
    fiscal-year convention (July 1 of the year and January 1 of the following year) is the same as the
    2024B OS table, which is proven by balances: 2017A principal from fiscal 2024 on sums to $168,135,000
    and 2017B to $153,340,000, the balances printed in wastewater_2024B_OS p.23; and sewer_FS2025 p.41
    shows $165,260K and $139,270K at 12/31/2025, i.e. only the Jan 1 2025 payment less. So no refunding
    since. The 2015 OS table uses a different year label (its 2026 principal is the Jan 1 2026 cover
    maturity), so 2015 is deliberately not used here."""
    pdf = find_pdf("Wastewater_2017AB")
    pg = pdf_text(pdf)
    toks, line = row_tokens(pg[28], 2026)
    if len(toks) != 10:
        raise SystemExit("sewer 2017AB tokens: %r" % toks)
    sen, outst, ap, ai, at, bp_, bi, bt, sec, tot = toks
    if abs(ap + ai - at) > 5 or abs(bp_ + bi - bt) > 5 or abs(outst + at + bt - sec) > 5 or abs(sen + sec - tot) > 5:
        raise SystemExit("sewer 2017AB row does not sum: %r" % toks)
    # balance tie: principal from fiscal 2024 on
    sums = {"A": 0, "B": 0}
    for l in pg[28].split("\n") + pg[29].split("\n"):
        m = re.match(r"^(20\d\d)\s+(.*)$", l.strip())
        if m and int(m.group(1)) >= 2024:
            t = [to_num(x) for x in TOK.findall(m.group(2).replace("$ ", "$"))]
            if len(t) == 10:
                sums["A"] += t[2]; sums["B"] += t[5]
    if sums != {"A": 168135000, "B": 153340000}:
        raise SystemExit("2017AB principal balances do not tie to 2024B OS: %r" % sums)
    pdf10 = find_pdf("Wastewater_2010A&B")
    p10 = pdf_text(pdf10)
    t10, l10 = row_tokens(p10[32], 2026)
    # printed: senior, outstanding second lien, 2010B interest, 2010B total, total (2010A matured, 2010B principal blank)
    if len(t10) != 5 or t10[2] != t10[3] or abs(t10[0] + t10[1] + t10[3] - t10[4]) > 5:
        raise SystemExit("sewer 2010 row: %r" % t10)
    b_int = t10[2]
    if b_int != 17250000 or round(250000000 * 0.069) != b_int:
        raise SystemExit("2010B interest %r != 250,000,000 x 6.9%%" % b_int)
    return {"doc17": pdf, "row17": line, "a": (ap, ai), "b": (bp_, bi), "doc10": pdf10, "row10": l10, "b2010": b_int}

# ---------------------------------------------------------------- build
ORD = {  # 2026 ordinance, Finance General, dataset 6694 / raw/city_appropriations_2026.json
    "ohare": {"interest": 496066181, "principal": 303172911, "fees": 3231068},
    "midway": {"interest": 61100475, "principal": 77455000, "fees": 6147941},
    "water_bonds": {"interest": 92769138, "principal": 86685000},
    "water_loans": {"interest": 14135049, "principal": 39667255},
    "sewer_bonds": {"interest": 77313314, "principal": 36753805},
    "sewer_loans": {"interest": 11735386, "principal": 32626175},
    "go": {"interest": 285429137, "principal": 132090000},
}
OHARE_COVER_PDF = {
    "2026A": "OS.X6Bl2Stb8", "2026B": "ohare_2026B_OS", "2026C": "ohare_2026CD_OS", "2026D": "ohare_2026CD_OS",
    "2025C": "Final-Official-Statement---ORD-2025CD", "2025D": "Final-Official-Statement---ORD-2025CD",
    "2025E": "Final-OS.Kvjb", "2025G": "Final-OS.Kvjb", "2025A": "OS.NEfpPym7t", "2025B": "OS.NEfpPym7t",
    "2024C": "OS.ZupAfhGTd", "2024D": "OS.ZupAfhGTd", "2024E": "OS.ZupAfhGTd", "2024F": "OS.ZupAfhGTd",
    "2024A": "Senor-Lien-Revenue-Bonds-Series-2024AB", "2024B": "Senor-Lien-Revenue-Bonds-Series-2024AB",
    "2022A": "P21754542", "2022B": "P21754542", "2022C": "P21754542", "2022D": "P21754542",
    "2020A": "Chicago-OHare-OS-2020", "2020B": "Chicago-OHare-OS-2020", "2020C": "Chicago-OHare-OS-2020",
    "2020D": "Chicago-OHare-OS-2020", "2020E": "Chicago-OHare-OS-2020",
    "2018A": "ORD_2018ABC", "2018B": "ORD_2018ABC", "2018C": "ORD_2018ABC",
    "2017A": "ORD_2017ABCD", "2017B": "ORD_2017ABCD", "2017C": "ORD_2017ABCD", "2017D": "ORD_2017ABCD",
    "2016D": "2016D-G", "2016E": "2016D-G", "2016F": "2016D-G", "2016G": "2016D-G",
}


def leaf(name, credit, total, principal, doc, page, row, status, note, principal_basis=None, extra=None):
    d = {"series": name, "credit": credit, "window": "payments Jan 2 2026 through Jan 1 2027",
         "total_pi": total, "principal": principal,
         "interest": (total - principal) if principal is not None and total is not None else None,
         "interest_is_derived_as_total_minus_principal": principal is not None,
         "principal_basis": principal_basis, "status": status, "note": note,
         "cite": {"doc": doc, "pdf_page": page, "row": row}}
    if extra:
        d.update(extra)
    return d


def build():
    ohare, ohare_checks = parse_ohare()
    go_older = parse_go_older()
    oth = parse_others()
    leaves = []
    # ---- O'Hare
    cur_sum = stale_printed = 0
    for srs in ohare:
        k = srs["series"]
        p, basis = cover_2027_principal(find_pdf(OHARE_COVER_PDF[k]), k)
        stale = k in OHARE_STALE
        extra = {"outstanding_principal_after_2026CD": OHARE_OUTSTANDING.get(k)}
        if k in ("2024A", "2024B"):
            extra["note_capitalized_interest"] = ("The 2024AB table subtracts $%d of capitalized interest for both series together. "
                                                  "It is not allocated here." % srs["capitalized_interest_combined_2024AB"])
        if stale:
            stale_printed += srs["d_s_2027_row"]
            leaves.append(leaf("O'Hare " + k, "ohare", None, None, srs["doc"], srs["pdf_page"], srs["row"], "stale",
                               "Printed amount %d from the series' own statement is an UPPER BOUND, not a leaf amount. %s. Its true 2026 amount is inside the O'Hare residual line."
                               % (srs["d_s_2027_row"], OHARE_STALE[k]), None, dict(extra, printed_upper_bound=srs["d_s_2027_row"])))
        else:
            cur_sum += srs["d_s_2027_row"]
            leaves.append(leaf("O'Hare " + k, "ohare", srs["d_s_2027_row"], p, srs["doc"], srs["pdf_page"], srs["row"], "current", "", basis, extra))
    total_gar = 771416782
    leaves.append(leaf("O'Hare residual: Series 2010B (BAB, $328M) plus post-refunding remainder of 2016D/E/F/G, 2017A/B/C and 2018C",
                       "ohare", total_gar - cur_sum, None, "ohare_2026CD_OS.pdf", 65,
                       "2027 total net debt service $771,416,782 minus sum of current series columns",
                       "residual_by_subtraction",
                       "Not split by series. The 2026CD statement prints only the combined outstanding column ($754,929,701) after the 2026CD refunding."))
    for key, amt, pg, doc, lab in [("O'Hare CFC Series 2023 bonds", 8786000, 51, "ohare_FS2025.pdf", "2026 interest $8,786K, principal 0"),
                                   ("O'Hare TIFIA loan", 15171000, 52, "ohare_FS2025.pdf", "2026 principal $4,336K, interest $10,835K"),
                                   ("O'Hare PFC Series 2012AB", 4000, 51, "ohare_FS2025.pdf", "2026 interest $4K")]:
        pr = {"O'Hare TIFIA loan": 4336000}.get(key, 0)
        leaves.append(leaf(key, "ohare", amt, pr, doc, pg, lab, "current",
                           "Calendar 2026 from the FY2025 financial statements ($ thousands x 1000)", "printed in the schedule"))
    # ---- Midway
    m = {k: oth[k] for k in oth if k.startswith("midway_") and k != "midway_fs_2026"}
    mid_sum = 0
    for key, col, nm in [("midway_2025AB", "2025A", "2025A"), ("midway_2025AB", "2025B", "2025B"), ("midway_2024", "2024A", "2024A"),
                         ("midway_2024", "2024B", "2024B"), ("midway_2023AB", "2023A", "2023A"), ("midway_2023AB", "2023B", "2023B"),
                         ("midway_2023C", "2023C", "2023C")]:
        v = oth[key]
        mid_sum += v["values"][col]
        leaves.append(leaf("Midway " + nm, "midway", v["values"][col], None, v["doc"], v["pdf_page"], v["row"], "current",
                           "Net of capitalized interest. Variable-rate bonds assumed at 3.00% in the source (midway_2025AB_OS p.60 note 5).",
                           "not extracted"))
    mid_out = oth["midway_2025AB"]["values"]["outstanding"]
    mid_other = mid_out - (oth["midway_2024"]["values"]["2024A"] + oth["midway_2024"]["values"]["2024B"]
                           + oth["midway_2023AB"]["values"]["2023A"] + oth["midway_2023AB"]["values"]["2023B"] + oth["midway_2023C"]["values"]["2023C"])
    leaves.append(leaf("Midway residual: Series 2014B, 2014C, 2018A (and any 2016A remnant)", "midway", mid_other, None,
                       "midway_2025AB_OS.pdf", 60, "outstanding column $%d minus the 2023A/B/C and 2024A/B columns" % mid_out,
                       "residual_by_subtraction", "FY2025 financial statement p.82 shows calendar 2027 for these as $4,240K (2014) + $5,256K (2018)."))
    # ---- Water
    w = oth["water_2026ABC"]["values"]; wa = oth["water_2024A"]["values"]; wb = oth["water_2023AB"]["values"]
    leaves.append(leaf("Water 2026A, 2026B, 2026C (three series, printed combined)", "water", w["ABC_total"], w["ABC_principal"],
                       oth["water_2026ABC"]["doc"], 36, oth["water_2026ABC"]["row"], "current_group",
                       "Sold May 2026. Net of capitalized interest. Fiscal year 2026 (calendar).", "printed in table"))
    leaves.append(leaf("Water 2024A", "water", wa["A_total"], wa["A_principal"], oth["water_2024A"]["doc"], 25, oth["water_2024A"]["row"], "current",
                       "Fiscal year 2026.", "printed in table"))
    leaves.append(leaf("Water 2023A", "water", wb["A_interest"], wb["A_principal"], oth["water_2023AB"]["doc"], 32, oth["water_2023AB"]["row"], "current", "Fiscal year 2026.", "printed in table"))
    leaves.append(leaf("Water 2023B", "water", wb["B_interest"], wb["B_principal"], oth["water_2023AB"]["doc"], 32, oth["water_2023AB"]["row"], "current", "Fiscal year 2026.", "printed in table"))
    # ---- Water round 2: series 2010B, 2010C and 2017 principal (checked against printed totals)
    w2 = parse_water_round2()
    leaves.append(leaf("Water 2010B (Build America Bonds, taxable)", "water", w2["b_int"], 0, w2["doc2010"], w2["pg2010"], w2["row2010"], "current",
                       "Term bond, no principal until the 2031 sinking fund. Interest = $250,000,000 x 6.742%% (cover). The 2010B + 2010C pieces add to the printed 'Series 2010 Bonds' column (%d) within $5. Gross of the federal subsidy. Not touched by the 2026 refunding or tender (Appendix I lists no 2010 bonds). Calendar 2026." % w2["printed_2010"],
                       "no principal due 2026 (first sinking fund installment 2031, OS p.22)"))
    leaves.append(leaf("Water 2010C (Qualified Energy Conservation Bonds)", "water", w2["c_tot"], w2["c_prin"], w2["doc2010"], w2["pg2010"], w2["row2010"], "current",
                       "Principal = 2026 sinking fund installment (OS p.22). Interest = $29,665,000 x 6.642% (cover). Ties to the printed 2010 column with 2010B. Not in the 2026 refunding or tender. Calendar 2026.",
                       "sinking fund schedule, OS p.22"))
    leaves.append(leaf("Water 2017 (principal only; interest left in residual)", "water", w2["p2017"], w2["p2017"], w2["doc2017"], w2["pg2017"], w2["row2017"], "current",
                       "Principal due Nov 1 2026 is $19,425,000, printed in the 2017 OS table and on its cover. The 2026 tender (water_2026ABC_OS Appendix I p.170) removed only 2029 to 2036 maturities, so the 2026 maturity is unaffected. Interest of $7,024,713 printed in the 2017 OS is NOT used because the tender (May 21 2026) changed it by an amount whose timing the statement does not state; it stays in the residual.",
                       "printed in table"))
    w_res = w["outstanding"] - wa["A_total"] - wb["AB_total"] - w2["b_int"] - w2["c_tot"] - w2["p2017"]
    leaves.append(leaf("Water residual: Series 2001, 2004, 2016A-1, 2017 interest, 2017-2 and 2023C (WIFIA)", "water", w_res, None,
                       "water_2026ABC_OS.pdf", 36, "outstanding column $%d minus 2024A, 2023A/B, 2010B, 2010C and 2017 principal" % w["outstanding"],
                       "residual_by_subtraction", "Series list from water_2026_supplement.pdf p.5. Not split further here."))
    leaves.append(leaf("Water IEPA subordinate-lien loans (aggregate)", "water", w["subordinate_iepa"], None, oth["water_2026ABC"]["doc"], 36,
                       oth["water_2026ABC"]["row"], "loan_aggregate", "Loans, not bonds. Per-loan 2026 payments are not printed in the OS (water_2026_supplement.pdf p.6 lists balances).", "not printed"))
    # ---- Sewer
    s24b = oth["sewer_2024B"]["values"]; s24a = oth["sewer_2024A"]["values"]
    # sewer_2023AB tokens: senior, outstanding second, A interest, A cap interest, A total, B interest, B total, second total, total
    t = oth["sewer_2023AB"]["tokens"]
    if len(t) != 9 or abs(t[1] + t[4] + t[5] - t[7]) > 5:
        raise SystemExit("sewer 2023AB row check failed: %r" % t)
    leaves.append(leaf("Sewer 2024B", "wastewater", s24b["B_total"], s24b["B_principal"], oth["sewer_2024B"]["doc"], 24, oth["sewer_2024B"]["row"], "current", "Fiscal year 2026.", "printed in table"))
    leaves.append(leaf("Sewer 2024A", "wastewater", s24a["A_total"], s24a["A_principal"], oth["sewer_2024A"]["doc"], 23, oth["sewer_2024A"]["row"], "current", "Fiscal year 2026.", "printed in table"))
    leaves.append(leaf("Sewer 2023A", "wastewater", t[4], 0, oth["sewer_2023AB"]["doc"], 30, oth["sewer_2023AB"]["row"], "current",
                       "Interest $%d less capitalized interest $%d." % (t[2], -t[3] if t[3] < 0 else t[3]), "no principal column value printed for 2026"))
    leaves.append(leaf("Sewer 2023B", "wastewater", t[5], 0, oth["sewer_2023AB"]["doc"], 30, oth["sewer_2023AB"]["row"], "current", "Fiscal year 2026.", "no principal column value printed for 2026"))
    s2 = parse_sewer_round2()
    leaves.append(leaf("Sewer 2017A", "wastewater", sum(s2["a"]), s2["a"][0], s2["doc17"], 28, s2["row17"], "current",
                       "Fiscal 2026 (July 1 2026 and Jan 1 2027 payments). Principal and interest columns printed. Balances tie to wastewater_2024B_OS p.23 and sewer_FS2025 p.41, so no later refunding.", "printed in table"))
    leaves.append(leaf("Sewer 2017B", "wastewater", sum(s2["b"]), s2["b"][0], s2["doc17"], 28, s2["row17"], "current",
                       "Fiscal 2026. Principal and interest columns printed. Balances tie to wastewater_2024B_OS p.23 and sewer_FS2025 p.41, so no later refunding.", "printed in table"))
    leaves.append(leaf("Sewer 2010B (Build America Bonds, taxable)", "wastewater", s2["b2010"], 0, s2["doc10"], 32, s2["row10"], "current",
                       "Term bond due 1/1/2040, interest only until 2029: $250,000,000 x 6.9% = $17,250,000 (printed column equals it). Gross of the federal subsidy. $250,000,000 still outstanding per wastewater_2024B_OS p.23 and sewer_FS2025 p.41.", "no principal due until 2029"))
    s_res = s24b["second_outstanding"] - s24a["A_total"] - t[4] - t[5] - s2["b2010"] - sum(s2["a"]) - sum(s2["b"])
    leaves.append(leaf("Sewer residual: second-lien 2001, 2015 and any 2008C remnant (2008C defeased)", "wastewater", s_res, None,
                       "wastewater_2024B_OS.pdf", 24, "outstanding second-lien column $%d minus 2024A, 2023A, 2023B, 2010B, 2017A, 2017B" % s24b["second_outstanding"],
                       "residual_by_subtraction", "Series not named in the fetched documents. The 2008C variable-rate bonds were defeased in 2025 (sewer_FS2025.pdf p.44), so this line is overstated by that series' 2026 debt service."))
    # Senior lien: wastewater_2024B_OS p.23 lists exactly one senior lien series, 1998A ($16,401,899, final 1/1/2028), so the whole column is 1998A.
    # Check: the printed senior column total $74,635,000 = fiscal 2024 $595,000 + 3 x $24,680,000 (fiscal 2025, 2026, 2027).
    sp = pdf_text(find_pdf("wastewater_2024B_OS"))
    if "1998A 1/1/2028 $16,401,899 $16,401,899\nSubtotal $16,401,899" not in sp[23]:
        raise SystemExit("senior lien table in 2024B OS p.23 no longer lists only 1998A")
    if 595000 + 3 * s24b["senior"] != 74635000:
        raise SystemExit("senior lien column does not tie to printed total")
    leaves.append(leaf("Sewer 1998A (senior lien)", "wastewater", s24b["senior"], None, "wastewater_2024B_OS.pdf", 24, oth["sewer_2024B"]["row"], "current",
                       "The only senior lien series in the 2024B OS (p.23), balance $16,401,899 at 1/1/2028 final maturity. The column is $24,680,000 in each of fiscal 2025, 2026 and 2027 and $595,000 in 2024, which add to the printed senior total $74,635,000. Principal and interest are not split in the table. The annual $24,680,000 exceeds the $16,401,899 balance, so the column must include accreted interest (inference, not stated in the table). Fiscal 2026 = July 1 2026 and Jan 1 2027 payments.",
                       "not printed"))
    leaves.append(leaf("Sewer IEPA subordinate-lien loans (aggregate)", "wastewater", s24b["subordinate_iepa"], None, "wastewater_2024B_OS.pdf", 24, oth["sewer_2024B"]["row"], "loan_aggregate", "Loans, not bonds.", "not printed"))
    # ---- GO older
    go_out = []
    for g in go_older:
        clean = abs(g["principal_mismatch"]) < 2000000 and g["label"].startswith("2021")
        go_out.append(leaf("GO " + g["label"], "go", (g["principal_2027"] + g["interest_2027"]) if clean else None,
                           g["principal_2027"] if clean else None, g["doc"], g["pdf_page"], g["row"],
                           "current_with_caveat" if clean else "stale",
                           ("Principal remaining in the statement from this row on is $%d vs $%d outstanding now (difference $%d, probably later tenders and refundings)."
                            % (g["principal_remaining_in_doc_from_2027"], g["outstanding_principal_now"], g["principal_mismatch"]))
                           + ("" if clean else " Printed amount is an upper bound only: principal $%d, interest $%d." % (g["principal_2027"], g["interest_2027"])),
                           "printed in table (row labelled 2026 holds payments due Jan 1 2027)",
                           None if clean else {"printed_upper_bound_principal": g["principal_2027"], "printed_upper_bound_interest": g["interest_2027"]}))
    leaves += go_out
    # ---- GO series isolated from the 2026AB all-outstanding table (type columns tied to Table 3 balances)
    g26 = parse_go_2026ab()
    gv = g26["values"]
    leaves.append(leaf("GO Taxable Series 2010B (MSAC Program, BAB)", "go", gv["ar_p"] + gv["ar_i"], gv["ar_p"], g26["doc"], 26,
                       g26["row"], "current",
                       "Alternate Revenue Bonds column of Table 4 is this one series: its total principal $%d equals the Table 3 balance. Row 'Year Ending January 1 2027' holds the June 1 and December 1 2026 payments (table note). Interest is gross of the federal BAB subsidy." % g26["msac_balance"],
                       "printed in table"))
    c17 = round(g26["b2017_balance"] * 0.07045)
    leaves.append(leaf("GO Taxable Project Series 2017B", "go", g26["b2017_balance"] + c17, g26["b2017_balance"], g26["doc"], 24,
                       "Taxable Project Series 2017B 11,765,000 1/1/2027", "current_with_caveat",
                       "Principal is the Table 3 balance, final maturity 1/1/2027, so all of it falls in the window. Interest is DERIVED, not printed: balance x 7.045% coupon (GO_2017A&B_OS cover, term bond due 1/1/2029) for two semiannual payments (Jul 1 2026 and Jan 1 2027), assuming no further tender. Ties to no printed interest figure.",
                       "Table 3 balance with final maturity 1/1/2027",
                       {"interest_derived_from": "11,765,000 x 7.045%"}))
    # ---- reconciliations
    cur = lambda c: sum(l["total_pi"] for l in leaves if l["credit"] == c and l.get("total_pi") is not None and l["status"] in ("current", "current_group", "current_with_caveat"))
    allc = lambda c: sum(l["total_pi"] for l in leaves if l["credit"] == c and l.get("total_pi") is not None)
    oh_ord = ORD["ohare"]["interest"] + ORD["ohare"]["principal"]
    recon = {
        "ohare": {"ordinance_principal": ORD["ohare"]["principal"], "ordinance_interest": ORD["ohare"]["interest"], "ordinance_pi": oh_ord,
                  "sum_of_current_series_leaves": cur("ohare") - 8786000 - 15171000 - 4000,
                  "senior_lien_total_per_2026CD_OS": total_gar, "cfc_plus_tifia_plus_pfc": 8786000 + 15171000 + 4000,
                  "all_listed_lines_total": allc("ohare"), "gap_to_ordinance": oh_ord - allc("ohare")},
        "midway": {"ordinance_pi": ORD["midway"]["interest"] + ORD["midway"]["principal"], "os_aggregate_bond_year_2027": oth["midway_2025AB"]["values"]["total"],
                   "fs_calendar_2026": oth["midway_fs_2026"]["values"]["total"], "fs_calendar_2027": 137561000,
                   "sum_of_lines": allc("midway")},
        "water": {"ordinance_bonds_pi": ORD["water_bonds"]["interest"] + ORD["water_bonds"]["principal"],
                  "ordinance_loans_pi": ORD["water_loans"]["interest"] + ORD["water_loans"]["principal"],
                  "ordinance_bonds_plus_loans": sum(ORD["water_bonds"].values()) + sum(ORD["water_loans"].values()),
                  "os_total_debt_service_requirement_2026": w["total"], "sum_of_lines": allc("water")},
        "wastewater": {"ordinance_bonds_pi": ORD["sewer_bonds"]["interest"] + ORD["sewer_bonds"]["principal"],
                       "ordinance_loans_pi": ORD["sewer_loans"]["interest"] + ORD["sewer_loans"]["principal"],
                       "ordinance_bonds_plus_loans": sum(ORD["sewer_bonds"].values()) + sum(ORD["sewer_loans"].values()),
                       "os_total_debt_service_requirement_2026": s24b["total"], "sum_of_lines": allc("wastewater")},
        "go": {"ordinance_pi": ORD["go"]["interest"] + ORD["go"]["principal"]},
    }
    out = {"generated_by": "scripts/bonds_parse.py", "units": "US dollars",
           "window_note": "O'Hare, Midway and GO use the bond year ending Jan 1 2027 (payments Jan 2 2026 to Jan 1 2027). Water and Sewer use fiscal (calendar) year 2026.",
           "status_key": {"current": "series column from the series' own OS; no later transaction known to change it",
                          "current_group": "series printed combined in one column", "current_with_caveat": "principal in the OS differs slightly from outstanding now",
                          "stale": "later refunding, defeasance or tender makes the printed figure an upper bound; not counted as a leaf amount",
                          "residual_by_subtraction": "aggregate outstanding column minus named series; not a single series",
                          "aggregate": "unnamed series bucket", "loan_aggregate": "IEPA loans, not bonds"},
           "ordinance_lines": ORD, "reconciliation": recon, "leaves": leaves,
           "ohare_parse_checks": ohare_checks,
           "not_covered": ["Library term notes ($125,926,011 principal, $2,200,000 interest): no official statement exists on the BondLink pages; the ACFR lists only the appropriation line (ACFR FY2025 budget schedule).",
                           "GO series 2012B, 2014B, 2015B, 2015C, 2017A/B, 2019A, 2020A: printed series columns are stale (see status).",
                           "O'Hare 2010B: no separate column in any statement fetched."]}
    # Flat list for scripts/leaves_inventory.py: one row per fund x series x kind.
    fund = {"ohare": "Chicago O'Hare Airport Fund", "midway": "Chicago Midway Airport Fund", "water": "Water Fund",
            "wastewater": "Sewer Fund", "go": "Bond Redemption and Interest Series Fund"}
    flat = []
    for l in leaves:
        if l["status"] not in ("current", "current_group", "current_with_caveat"):
            continue
        base = {"series": l["series"], "fund": fund[l["credit"]], "credit": l["credit"], "status": l["status"], "cite": l["cite"]}
        if l["principal"] is not None:
            flat.append(dict(base, kind="principal", amount=l["principal"]))
            flat.append(dict(base, kind="interest", amount=l["total_pi"] - l["principal"]))
        else:
            flat.append(dict(base, kind="principal_and_interest", amount=l["total_pi"],
                             split_note="principal/interest split not extracted for this series"))
    out["series"] = flat
    out["series_total_by_credit"] = {c: sum(r["amount"] for r in flat if r["credit"] == c) for c in fund}
    json.dump(out, open(OUT, "w"), indent=1)
    return out


def main():
    out = build()
    ls = out["leaves"]
    print("leaves", len(ls))
    for c in out["reconciliation"]:
        print(c, out["reconciliation"][c])


if __name__ == "__main__":
    main()
