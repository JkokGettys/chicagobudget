#!/usr/bin/env python3
"""Fetch and parse the Chicago Park District 'Vendor Payments - Ethics Ordinance Report' PDFs
(2019-2022) published under https://www.chicagoparkdistrict.com/ethics-office .
Output: raw/parkvend/ethics/vp_<year>.pdf and raw/parkvend/ethics_rows.json (all rows).
Each PDF lists vendors that received >= $10,000 in a 12-month period; source is the District ERP."""
import json, os, re, subprocess
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "raw", "parkvend", "ethics")
os.makedirs(D, exist_ok=True)
MEDIA = {2019: 29071, 2020: 29076, 2021: 29081, 2022: 29086}
PAGE = "https://www.chicagoparkdistrict.com/media/{}/download?inline"

AMT_X = {2019: 274, 2020: 332, 2021: 332, 2022: 332}  # x of first amount digit, fixed per file


def stream_lines(page, year):
    """Return (name, amount_text) per line using char x positions in content-stream order.
    extract_text() sorts by x and scrambles long names that overflow into the amount column.
    The amount is the trailing run of digit chars whose first char sits at the amount column x."""
    lines = {}
    for c in page.chars:
        lines.setdefault(round(c["top"]), []).append(c)
    out = []
    for _, v in sorted(lines.items()):
        k = len(v)
        while k > 0 and v[k - 1]["text"] in "0123456789.,-":
            k -= 1
        # k = first index of trailing numeric run; extend start so that run begins at the amount column
        start = None
        for i in range(k, len(v)):
            if abs(v[i]["x0"] - AMT_X[year]) <= 1.5:
                start = i
                break
        if start is None:
            out.append(("".join(c["text"] for c in v), None))
        else:
            out.append(("".join(c["text"] for c in v[:start]).strip(), "".join(c["text"] for c in v[start:])))
    return out


rows, problems = [], []
for y, mid in MEDIA.items():
    f = os.path.join(D, f"vp_{y}.pdf")
    if not os.path.exists(f) or os.path.getsize(f) < 1000:
        subprocess.run(["curl", "-sL", "-m", "120", "-o", f, PAGE.format(mid)], check=True)
    pdf = pdfplumber.open(f)
    n = 0
    for pi, page in enumerate(pdf.pages):
        for name, amt in stream_lines(page, y):
            if name.replace(" ", "") in ("VendorNameAmount",) or name.startswith("Vendor Payments"):
                continue
            if amt is None:
                problems.append((y, pi + 1, name))
                continue
            rows.append({"year": y, "vendor": name, "amount": float(amt.replace(",", "")), "pdf_page": pi + 1})
            n += 1
    print(y, "pages", len(pdf.pages), "rows", n, "total", round(sum(r["amount"] for r in rows if r["year"] == y), 2))
print("unparsed lines:", len(problems))
for p in problems[:20]:
    print("  ", p)
json.dump(rows, open(os.path.join(ROOT, "raw", "parkvend", "ethics_rows.json"), "w"))
