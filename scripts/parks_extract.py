#!/usr/bin/env python3
"""Step 1: extract positioned words from the Chicago Park District 2026 Budget
Appropriations PDF (274 PDF pages; printed page number = PDF page - 6).

Writes raw/parks/words.json: {pdf_page: [[text, x0, x1, top, size], ...]}
Rotated sidebar text is dropped (upright words only). Downloads the PDF into
raw/parks/approp.pdf when it is not already there.

Usage: python3 scripts/parks_extract.py
"""
import json, os, sys, urllib.request
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "parks")
PDF = os.path.join(RAW, "approp.pdf")
URL = ("https://files.chicagoparkdistrict.com/2025-12/2026%20Budget%20Appropriations.pdf"
       "?VersionId=4S4MZxZ1Cut5r1bdwmTOgGBFF4mHJbmq")


def main():
    os.makedirs(RAW, exist_ok=True)
    if not os.path.exists(PDF):
        urllib.request.urlretrieve(URL, PDF)
    pages = {}
    with pdfplumber.open(PDF) as pdf:
        for i, p in enumerate(pdf.pages):
            n = i + 1
            ws = p.extract_words(x_tolerance=1.5, y_tolerance=2, extra_attrs=["upright", "size"])
            pages[n] = [[w["text"], round(w["x0"], 1), round(w["x1"], 1), round(w["top"], 1),
                         round(w["size"], 1)] for w in ws if w["upright"]]
            if n % 50 == 0:
                print("page", n, file=sys.stderr)
    with open(os.path.join(RAW, "words.json"), "w") as f:
        json.dump(pages, f)
    print("pages:", len(pages))


if __name__ == "__main__":
    main()
