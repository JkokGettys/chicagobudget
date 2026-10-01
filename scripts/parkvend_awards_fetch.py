#!/usr/bin/env python3
"""For every Legistar matter whose title is a contract award, renewal, extension, change order,
or management agreement (2019 on), list attachments via the public Web API, download the PDFs,
and extract text. Output: raw/parkvend/award_text/<MatterId>_<n>.txt and raw/parkvend/award_index.json."""
import json, os, re, subprocess, time
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "parkvend")
PDFS = os.path.join(RAW, "award_pdf")
TXT = os.path.join(RAW, "award_text")
for d in (PDFS, TXT):
    os.makedirs(d, exist_ok=True)
API = "https://webapi.legistar.com/v1/chicagoparkdistrict/matters/{}/attachments"
pat = re.compile(r"CONTRACT|AGREEMENT|EXTEN|CHANGE ORDER|MODIFICATION|PAYMENT|AWARD|RENEW", re.I)
skip = re.compile(r"TAX LEVY|BOND|APPROPRIATION|JOURNAL|MINUTES", re.I)

matters = json.load(open(os.path.join(RAW, "legistar_matters_all.json")))
sel = [m for m in matters if (m["MatterIntroDate"] or m["MatterAgendaDate"] or "")[:4] >= "2019"
       and m["MatterTypeName"] in ("Action Item", "Report")
       and pat.search(m["MatterTitle"] or "") and not skip.search(m["MatterTitle"] or "")]
print("selected matters", len(sel))
index = []
for i, m in enumerate(sel):
    r = subprocess.run(["curl", "-sL", "-m", "40", API.format(m["MatterId"])], capture_output=True, text=True)
    try:
        atts = json.loads(r.stdout)
    except Exception:
        atts = []
    for j, a in enumerate(atts):
        url = a["MatterAttachmentHyperlink"]
        pdf = os.path.join(PDFS, f"{m['MatterId']}_{j}.pdf")
        txt = os.path.join(TXT, f"{m['MatterId']}_{j}.txt")
        if not os.path.exists(txt):
            if not os.path.exists(pdf):
                subprocess.run(["curl", "-sL", "-m", "90", "-o", pdf, url])
            try:
                with pdfplumber.open(pdf) as p:
                    open(txt, "w").write("\n".join((pg.extract_text() or "") for pg in p.pages[:12]))
            except Exception as e:
                open(txt, "w").write("")
        index.append({"matter_id": m["MatterId"], "file": m["MatterFile"], "passed": (m["MatterPassedDate"] or "")[:10],
                      "title": re.sub(r"\s+", " ", m["MatterTitle"] or ""), "attachment": a["MatterAttachmentName"],
                      "url": url, "txt": os.path.basename(txt)})
    if i % 25 == 0:
        print(i, len(index), flush=True)
json.dump(index, open(os.path.join(RAW, "award_index.json"), "w"))
print("attachments", len(index))
