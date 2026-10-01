#!/usr/bin/env python3
"""parkcap_schedules.py: derive an IMPLIED contract price for Chicago Park District capital awards.

Board of Commissioners items on Legistar (https://chicagoparkdistrict.legistar.com) publish no contract amount for
2024-2026 awards, but each award has a scanned "MWBE Schedules" attachment. Schedule A lists, for each MBE/WBE
subcontractor, "Dollars $X" and "Percent: Y" of the contract. X / (Y/100) is the contract price the bidder used.
This script downloads those attachments, OCRs the first pages with macOS Vision (Swift helper compiled on the
fly), parses the (dollars, percent) pairs, and writes raw/parkcap/schedules_implied.json.

Implied price = median over pairs with percent that has a decimal point and dollars >= 20,000, keeping only pairs
within 3 percent of the median. Needs >= 2 agreeing pairs. It is an estimate of the bid, NOT an audited award amount.

Inputs : raw/parkcap/matters_all.json, attachments_all.json (made by parkcap_legistar.py)
Output : raw/parkcap/schedules_implied.json
"""
import json, os, re, subprocess, sys, statistics, time, urllib.request, concurrent.futures as cf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "parkcap")
TOOLS = os.path.join(RAW, "tools")
ATT = os.path.join(RAW, "att")

SWIFT = r'''
import Foundation
import PDFKit
import Vision
import AppKit
let args = CommandLine.arguments
let doc = PDFDocument(url: URL(fileURLWithPath: args[1]))!
let maxp = args.count > 2 ? Int(args[2])! : doc.pageCount
for i in 0..<min(doc.pageCount, maxp) {
    let page = doc.page(at: i)!
    let r = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2.0
    let w = Int(r.width*scale), h = Int(r.height*scale)
    let cs = CGColorSpaceCreateDeviceRGB()
    let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.setFillColor(CGColor(red:1,green:1,blue:1,alpha:1)); ctx.fill(CGRect(x:0,y:0,width:w,height:h))
    ctx.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: ctx)
    let img = ctx.makeImage()!
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    let h2 = VNImageRequestHandler(cgImage: img, options: [:])
    try? h2.perform([req])
    print("=== PAGE \(i+1)")
    for o in req.results ?? [] { if let c = o.topCandidates(1).first { print(c.string) } }
}
'''

CAP = re.compile(r"construct|renovat|reconstruct|rehabilit|restoration|improvement|development|fieldhouse|field house|"
                 r"design|architect|engineering|HVAC|ADA|roof|turf|playground|shoreline|revetment|park (no|#)", re.I)
NOT = re.compile(r"CHAPTER|SETTLEMENT|NAME |NAMING|SUPPLY|MAINTENANCE|FLORAL|LANDSCAP|JANITORIAL|INSURANCE|SERVICES? FOR (CELLULAR|VIDEO)|"
                 r"POOL CHEM|EXTENSION OPTION|MANAGEMENT AND OPERATION|CONCESSION", re.I)


def build_ocr():
    os.makedirs(TOOLS, exist_ok=True)
    src, exe = os.path.join(TOOLS, "ocr.swift"), os.path.join(TOOLS, "ocr")
    if not os.path.exists(exe):
        open(src, "w").write(SWIFT)
        subprocess.run(["swiftc", "-O", src, "-o", exe], check=True)
    return exe


def targets():
    m = {x["MatterId"]: x for x in json.load(open(os.path.join(RAW, "matters_all.json")))}
    att = json.load(open(os.path.join(RAW, "attachments_all.json")))
    out = []
    for mid, x in m.items():
        if x["MatterTypeName"] != "Action Item" or (x["MatterIntroDate"] or "") < "2019":
            continue
        t = (x["MatterTitle"] or "").replace("\n", " ")
        if not CAP.search(t) or NOT.search(t):
            continue
        for a in att.get(str(mid), []):
            n = a["MatterAttachmentName"]
            if re.search(r"MWBE|MBE|Schedule|Target", n, re.I) and a["MatterAttachmentHyperlink"].endswith(".pdf"):
                out.append((mid, x, a))
                break
    return out


def money(s):
    s = re.sub(r"[^\d.,]", "", s).replace(",", "")
    # OCR often turns the thousands comma into a period: 63.000.00 or 336.295.00
    if s.count(".") >= 2:
        parts = s.split(".")
        s = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(s)
    except ValueError:
        return None


def parse(text):
    """Block parser: each subcontractor block starts at 'Participation: Dollars'. Dollars may contain stray spaces
    (OCR: '432, 00 0'); the percent is the first decimal number after the word Percent within the next 5 lines."""
    pairs = []
    parts = re.split(r"Participation:?\s*Doll?ars?\s*\$?", text, flags=re.I)[1:]
    for blk in parts:
        lines = blk.split("\n")
        first = lines[0]
        rest = "\n".join(lines[1:6])
        dtxt = first if re.search(r"\d", first) else (lines[1] if len(lines) > 1 else "")
        dtxt = re.sub(r"(?i)percent.*", "", dtxt)
        dtxt = re.sub(r"[_\s]", "", dtxt)
        d = money(dtxt) if re.search(r"\d", dtxt) else None
        pm = re.search(r"Percent:?[\s_]*([0-9]+\.[0-9]+)", first + "\n" + rest, re.I)
        if not pm:
            pm = re.search(r"^[\s_-]*([0-9]{1,2}\.[0-9]{1,2})\s*%?\s*$", rest, re.M)
        p = money(pm.group(1)) if pm else None
        if d and p and d >= 20000 and 0.2 <= p <= 60:
            pairs.append((d, p, d / (p / 100)))
    if len(pairs) < 2:
        return None
    med = statistics.median(x[2] for x in pairs)
    good = [x for x in pairs if abs(x[2] - med) / med <= 0.04]
    if len(good) < 2:
        return None
    return {"implied_price": round(statistics.median(x[2] for x in good)), "pairs_used": len(good), "pairs_seen": len(pairs),
            "min": round(min(x[2] for x in good)), "max": round(max(x[2] for x in good))}


def work(t, exe):
    mid, x, a = t
    os.makedirs(ATT, exist_ok=True)
    f = os.path.join(ATT, f"m{mid}.pdf")
    if os.path.exists(f) and os.path.getsize(f) == 0:
        os.remove(f)
    if not os.path.exists(f):
        req = urllib.request.Request(a["MatterAttachmentHyperlink"], headers={"User-Agent": "Mozilla/5.0"})
        err = None
        for attempt in range(5):  # the Granicus host throws sporadic 404s under load
            try:
                blob = urllib.request.urlopen(req, timeout=120).read()  # read first so a failure leaves no empty file
                open(f, "wb").write(blob)
                err = None
                break
            except Exception as e:
                err = str(e)
                time.sleep(2 + 3 * attempt)
        if err:
            return mid, {"error": err}
    tf = f[:-4] + ".ocr.txt"
    if not os.path.exists(tf):
        r = subprocess.run([exe, f, "14"], capture_output=True, text=True, timeout=600)
        open(tf, "w").write(r.stdout)
    txt = open(tf).read()
    res = parse(txt) or {}
    res.update({"matter_id": mid, "file": x["MatterFile"], "date": (x["MatterAgendaDate"] or x["MatterIntroDate"] or "")[:10],
                "title": " ".join((x["MatterTitle"] or "").split()), "attachment": a["MatterAttachmentHyperlink"],
                "ocr_chars": len(txt)})
    return mid, res


def main():
    exe = build_ocr()
    ts = targets()
    print(len(ts), "matters with schedules", file=sys.stderr)
    out = {}
    with cf.ThreadPoolExecutor(2) as ex:
        for mid, r in ex.map(lambda t: work(t, exe), ts):
            out[mid] = r
    json.dump(out, open(os.path.join(RAW, "schedules_implied.json"), "w"), indent=1)
    ok = sum(1 for r in out.values() if "implied_price" in r)
    print(f"{ok}/{len(out)} with implied price", file=sys.stderr)


if __name__ == "__main__":
    main()
