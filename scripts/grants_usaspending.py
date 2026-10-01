#!/usr/bin/env python3
"""Pull federal assistance awards to City of Chicago recipients from the USASpending.gov API (FY2021-FY2026),
and fetch award detail (place of performance zip) for FAA awards so they can be assigned to O'Hare (60666) or Midway (60638).
API: https://api.usaspending.gov/api/v2/search/spending_by_award/ and /api/v2/awards/{generated_internal_id}/
Raw cache: raw/grants/usaspending_chicago_awards.json, raw/grants/faa_awards_detail.json (both gitignored).
Run: python3 scripts/grants_usaspending.py   (about 5 minutes, rerun is cached unless --refresh)
"""
import json, os, sys, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'raw', 'grants')
os.makedirs(RAW, exist_ok=True)
SEARCH = 'https://api.usaspending.gov/api/v2/search/spending_by_award/'
AWARD = 'https://api.usaspending.gov/api/v2/awards/%s/'
NAMES = ['CITY OF CHICAGO', 'CHICAGO, CITY OF', 'CHICAGO DEPARTMENT OF', 'CITY OF CHICAGO DEPARTMENT']
PERIODS = [('2025-10-01', '2026-09-30'), ('2024-10-01', '2025-09-30'), ('2023-10-01', '2024-09-30'), ('2022-10-01', '2023-09-30'), ('2021-10-01', '2022-09-30')]
TYPES = (['02', '03', '04', '05'], ['06', '10'])  # grants/cooperative agreements, direct payments


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=90))


def search(page, types, start, end, name):
    return post(SEARCH, {"filters": {"award_type_codes": types, "time_period": [{"start_date": start, "end_date": end, "date_type": "action_date"}],
                                     "recipient_search_text": [name], "recipient_type_names": ["government"]},
                         "fields": ["Award ID", "Recipient Name", "Award Amount", "Total Outlays", "Description", "Awarding Agency", "Awarding Sub Agency",
                                    "Assistance Listings", "Start Date", "End Date"],
                         "page": page, "limit": 100, "sort": "Award Amount", "order": "desc", "subawards": False})


def pull_awards():
    out = {}
    for nm in NAMES:
        for s, e in PERIODS:
            for types in TYPES:
                p = 1
                while True:
                    r = search(p, types, s, e, nm)
                    for x in r['results']:
                        out.setdefault(x['Award ID'], {**x, '_fy_window_start': s})
                    if not r['page_metadata'].get('hasNext'):
                        break
                    p += 1
    return list(out.values())


def faa_detail(awards):
    out = []
    for x in awards:
        if 'Federal Aviation' not in (x['Awarding Sub Agency'] or ''):
            continue
        r = post(SEARCH, {"filters": {"award_type_codes": ["02", "03", "04", "05"], "award_ids": [x['Award ID']]}, "fields": ["Award ID"], "limit": 2})
        gid = r['results'][0]['generated_internal_id']
        det = json.load(urllib.request.urlopen(AWARD % urllib.parse.quote(gid), timeout=60))
        zip5 = det['place_of_performance'].get('zip5')
        out.append({'award_id': x['Award ID'], 'recipient': x['Recipient Name'], 'total_obligation': det['total_obligation'], 'total_outlay': det.get('total_outlay'),
                    'description': det['description'], 'zip5': zip5, 'airport': {'60666': "O'Hare", '60638': 'Midway'}.get(zip5, 'unknown'),
                    'start': det['period_of_performance']['start_date'], 'end': det['period_of_performance']['end_date'],
                    'aln': [a['cfda_number'] for a in x['Assistance Listings']], 'usaspending_url': 'https://www.usaspending.gov/award/' + gid})
        time.sleep(0.2)
    return out


if __name__ == '__main__':
    refresh = '--refresh' in sys.argv
    p1 = os.path.join(RAW, 'usaspending_chicago_awards.json')
    p2 = os.path.join(RAW, 'faa_awards_detail.json')
    if refresh or not os.path.exists(p1):
        json.dump(pull_awards(), open(p1, 'w'))
    awards = json.load(open(p1))
    print('awards', len(awards))
    if refresh or not os.path.exists(p2):
        json.dump(faa_detail(awards), open(p2, 'w'), indent=1)
    print('faa awards', len(json.load(open(p2))))
