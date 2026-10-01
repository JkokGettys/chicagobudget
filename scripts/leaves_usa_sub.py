#!/usr/bin/env python3
"""Fetch USASpending sub-awards to the City of Chicago (pass-through money: IDOT -> City) for ALN 20.205 and 20.507,
and prime awards for ALN 20.205/20.507/66.802/14.218. Caches to raw/leaves/usa_sub_<aln>.json with HTTP status.
Run: python3 scripts/leaves_usa_sub.py"""
import json, os, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
os.makedirs(f"{ROOT}/raw/leaves", exist_ok=True)
log = []
def post(body):
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status, json.load(r)
def sub(aln, name):
    out = []
    for page in range(1, 40):
        body = {"filters": {"award_type_codes": ["02", "03", "04", "05"], "time_period": [{"start_date": "2007-10-01", "end_date": "2026-09-30"}],
                "recipient_search_text": [name], "program_numbers": [aln]},
                "fields": ["Sub-Award ID", "Sub-Awardee Name", "Sub-Award Amount", "Sub-Award Date", "Sub-Award Description", "Prime Award ID", "Prime Recipient Name"],
                "page": page, "limit": 100, "subawards": True, "sort": "Sub-Award Amount", "order": "desc"}
        st, d = post(body)
        out += d["results"]
        if not d["page_metadata"]["hasNext"]: break
    log.append({"url": URL + " (subawards, ALN %s, recipient '%s')" % (aln, name), "http_status": st, "rows": len(out)})
    return out
res = {}
for aln in ("20.205", "20.507"):
    rows = sub(aln, "CITY OF CHICAGO")
    rows = [r for r in rows if r["Sub-Awardee Name"] in ("CITY OF CHICAGO", "CHICAGO DEPARTMENT OF TRANSPORTATION", "CITY OF CHICAGO DEPARTMENT OF TRANSPORTATION", "CHICAGO, CITY OF")]
    res[aln] = rows
json.dump({"log": log, "subawards": res}, open(f"{ROOT}/raw/leaves/usa_sub.json", "w"), indent=1)
print(log, {k: len(v) for k, v in res.items()})
