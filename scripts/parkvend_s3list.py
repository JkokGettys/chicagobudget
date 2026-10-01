#!/usr/bin/env python3
"""List every key in the Park District public S3 bucket (files.chicagoparkdistrict.com)
and write raw/parkvend/s3_keys.json. Then print keys that look like payment,
vendor, checkbook, contract, expenditure, disbursement or audit documents."""
import json, os, re, subprocess, urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "raw", "parkvend")
os.makedirs(OUT, exist_ok=True)
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
BASE = "https://files.chicagoparkdistrict.com/"


def fetch(marker):
    url = BASE + "?max-keys=1000" + ("&marker=" + urllib.parse.quote(marker) if marker else "")
    return subprocess.run(["curl", "-sL", "-m", "60", url], capture_output=True, text=True).stdout


keys, marker = [], ""
while True:
    root = ET.fromstring(fetch(marker))
    page = root.findall("s:Contents", NS)
    for c in page:
        keys.append({"key": c.find("s:Key", NS).text,
                     "size": int(c.find("s:Size", NS).text),
                     "modified": c.find("s:LastModified", NS).text})
    trunc = root.find("s:IsTruncated", NS).text == "true"
    if not page or not trunc:
        break
    nxt = page[-1].find("s:Key", NS).text
    if nxt == marker or root.find("s:Marker", NS).text == "" and marker:
        # The CDN in front of the bucket ignores query strings, so paging is impossible.
        print("WARNING: marker ignored by CDN, listing is capped at the first 1000 keys")
        break
    marker = nxt
json.dump(keys, open(os.path.join(OUT, "s3_keys.json"), "w"))
print("total keys", len(keys))

pat = re.compile(r"payment|vendor|checkbook|check.?reg|disburse|expenditure|paid|warrant|"
                 r"contract|foia|single.?audit|audit|procure|award|spend|transparen|"
                 r"management.?agree|amend", re.I)
hits = [k for k in keys if pat.search(k["key"]) and not k["key"].lower().endswith((".png", ".jpg", ".gif", ".jpeg"))]
print("candidate keys", len(hits))
for k in hits:
    print(k["modified"][:10], k["size"], k["key"])
