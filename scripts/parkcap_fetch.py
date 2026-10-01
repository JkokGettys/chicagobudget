#!/usr/bin/env python3
"""parkcap_fetch.py: download every raw input used by parkcap_build.py into raw/parkcap/ (gitignored).

Skips files that already exist. Sources (all public, no key):
  * Legistar Web API   https://webapi.legistar.com/v1/chicagoparkdistrict/{matters,events,matters/{id}/attachments}
  * Bonfire public contracts detail  https://chicagoparkdistrict.bonfirehub.com/internalApi/publicContracts/{id}
  * ArcGIS capital layer + park master layer (services7.arcgis.com/HpTF5nhGpVZolZvo)
  * USAspending API (recipient text 'CHICAGO PARK DISTRICT')
  * IDNR OSLAD award announcements (3 PDFs)
  * Older Capital Improvement Plans (files.chicagoparkdistrict.com)
Also reuses (already in the repo's raw/): raw/grants/ds_fpsv-qjg3.json (City TIF Projections 2025-2034, Socrata fpsv-qjg3),
raw/grants/ds_mex4-ppfc.json (TIF IGA/agreement list, Socrata mex4-ppfc), raw/grants/menu_q2_2026.json,
raw/gap/bonfire_contracts.json, raw/parks/cap24_projects.json.
"""
import json, os, sys, time, urllib.parse, urllib.request, concurrent.futures as cf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "parkcap")
UA = {"User-Agent": "Mozilla/5.0"}
LEG = "https://webapi.legistar.com/v1/chicagoparkdistrict"
ARC = "https://services7.arcgis.com/HpTF5nhGpVZolZvo/arcgis/rest/services"


def get(url, data=None, headers=None, tries=4, timeout=90):
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:  # sporadic 404/5xx from Granicus and Bonfire under load
            err = e
            time.sleep(2 + 3 * i)
    raise err


def save(name, obj):
    os.makedirs(RAW, exist_ok=True)
    json.dump(obj, open(os.path.join(RAW, name), "w"))


def have(name):
    return os.path.exists(os.path.join(RAW, name))


def odata(path):
    out, skip = [], 0
    while True:
        q = urllib.parse.urlencode({"$top": 1000, "$skip": skip, "$orderby": path[1]})
        r = json.loads(get(f"{LEG}/{path[0]}?{q}"))
        out += r
        if len(r) < 1000:
            return out
        skip += 1000


def legistar():
    if not have("matters_all.json"):
        save("matters_all.json", odata(("matters", "MatterId")))
    if not have("events_all.json"):
        save("events_all.json", odata(("events", "EventId")))
    if not have("attachments_all.json"):
        m = json.load(open(os.path.join(RAW, "matters_all.json")))
        ids = [x["MatterId"] for x in m if x["MatterTypeName"] in
               ("Action Item", "Report", "Resolution", "Presentation", "Ordinance", "Bond Notification", "General")]
        with cf.ThreadPoolExecutor(6) as ex:
            res = dict(ex.map(lambda i: (i, json.loads(get(f"{LEG}/matters/{i}/attachments"))), ids))
        save("attachments_all.json", res)


def bonfire():
    if have("bonfire_details.json"):
        return
    pc = json.load(open(os.path.join(ROOT, "raw", "gap", "bonfire_contracts.json")))["payload"]["publicContracts"]
    ids = [v["ContractID"] for v in pc.values()]
    with cf.ThreadPoolExecutor(8) as ex:
        res = dict(ex.map(lambda i: (i, json.loads(get(f"https://chicagoparkdistrict.bonfirehub.com/internalApi/publicContracts/{i}"))), ids))
    save("bonfire_details.json", res)


def arcgis():
    if not have("chicago_parks_layer.json"):
        q = "where=1%3D1&outFields=PARK_NO,PARK,LOCATION,WARD,ACRES&returnGeometry=false&resultRecordCount=2000&f=json"
        save("chicago_parks_layer.json", json.loads(get(f"{ARC}/Chicago_Parks/FeatureServer/0/query?{q}")))


def usaspending():
    if have("usa/usa_cpd_awards.json"):
        return
    os.makedirs(os.path.join(RAW, "usa"), exist_ok=True)
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    out = {}
    for types, kind in ((["02", "03", "04", "05"], "assist"), (["06", "10"], "direct"), (["A", "B", "C", "D"], "contract")):
        p = 1
        while True:
            body = {"filters": {"award_type_codes": types, "time_period": [{"start_date": "2007-10-01", "end_date": "2026-09-30"}],
                                "recipient_search_text": ["CHICAGO PARK DISTRICT"]},
                    "fields": ["Award ID", "Recipient Name", "Award Amount", "Total Outlays", "Description", "Awarding Agency",
                               "Awarding Sub Agency", "Start Date", "End Date"],
                    "page": p, "limit": 100, "sort": "Award Amount", "order": "desc", "subawards": False}
            r = json.loads(get(url, json.dumps(body).encode(), {"Content-Type": "application/json"}))
            for x in r["results"]:
                if "CHICAGO PARK DISTRICT" in (x["Recipient Name"] or "").upper():
                    out[x["Award ID"]] = {**x, "_kind": kind}
            if not r["page_metadata"].get("hasNext"):
                break
            p += 1
    save("usa/usa_cpd_awards.json", list(out.values()))


def files():
    os.makedirs(os.path.join(RAW, "oslad"), exist_ok=True)
    os.makedirs(os.path.join(RAW, "cip"), exist_ok=True)
    pdfs = {
        "oslad/oslad2024.pdf": "https://capitolnewsillinois.com/wp-content/uploads/2024/04/OSLAD-LIST.pdf",
        "oslad/oslad_dec2024.pdf": "https://www.illinois.gov/content/dam/soi/en/web/illinois/iisnewsattachments/30748-121624-dnr-oslad-grants-announced.pdf.pdf",
        "oslad/oslad_jan2026.pdf": "https://www.illinois.gov/content/dam/soi/en/web/illinois/iisnewsattachments/32088-011426-01092026-idnr-oslad-park-grants-awarded.pdf.pdf",
        "cip/2015-2019.pdf": "https://files.chicagoparkdistrict.com/2025-04/2015-2019%20Capital%20Improvement%20Plan.pdf",
        "cip/2016-2020.pdf": "https://files.chicagoparkdistrict.com/2025-04/2016-2020_Capital_Improvement_Plan_11.2015.pdf",
        "cip/2017-2021.pdf": "https://files.chicagoparkdistrict.com/2025-04/2017-2021_Capital_Improvement_Plan_11.2016.pdf",
        "cip/2018-2022.pdf": "https://files.chicagoparkdistrict.com/2025-04/2018-2022%20Capital%20Improvement%20Plan.pdf",
        "cip/2019-2023.pdf": "https://files.chicagoparkdistrict.com/2025-04/2019-2023%20Capital%20Improvement%20Plan.pdf",
        "cip/2020-2024.pdf": "https://files.chicagoparkdistrict.com/2025-04/2020-2024%20Capital%20Improvement%20Plan.pdf",
    }
    for rel, u in pdfs.items():
        f = os.path.join(RAW, rel)
        if not os.path.exists(f):
            open(f, "wb").write(get(u))


if __name__ == "__main__":
    for fn in (legistar, bonfire, arcgis, usaspending, files):
        print(fn.__name__, file=sys.stderr)
        fn()
