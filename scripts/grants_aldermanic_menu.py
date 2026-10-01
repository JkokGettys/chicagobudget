#!/usr/bin/env python3
"""Parse OBM Aldermanic Menu Q2 2026 report into ward-level project lines.
Source: https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CIP_Archive/Aldermanic%20Menu/Q2_2026_Ald_Menu_Report.pdf
Output: appended into data/city_capital_2026.json under 'aldermanic_menu_2026' (run after grants_capital_cip.py).
Check: per-ward sum of items must equal printed 'WARD COMMITTED 2026 TOTAL'.
"""
import json, os, re, subprocess, collections
import pypdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'raw', 'grants')
URL = 'https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CIP_Archive/Aldermanic%20Menu/Q2_2026_Ald_Menu_Report.pdf'
PDF = os.path.join(RAW, 'menu_q2_2026.pdf')
os.makedirs(RAW, exist_ok=True)
if not os.path.exists(PDF):
    subprocess.check_call(['curl', '-sL', '-A', 'Mozilla/5.0', '-o', PDF, URL])
r = pypdf.PdfReader(PDF)
M = lambda s: round(float(s.replace('$', '').replace(',', '')), 2)
ITEM = re.compile(r'^(?P<pkg>\S.*?\(\d{4}\))\s{2,}(?P<loc>.*?)\s{2,}\$(?P<cost>[\d,]+\.\d\d)\s*$')
items, wards = [], {}
ward = None
for pno in range(6, len(r.pages) + 1):
    txt = r.pages[pno - 1].extract_text(extraction_mode='layout')
    for l in txt.splitlines():
        m = re.match(r'^\s*Ward:\s*(\d+)', l)
        if m:
            ward = int(m.group(1)); wards.setdefault(ward, {'budget': None, 'committed': None, 'balance': None}); continue
        m = re.match(r'^\s*MENU BUDGET\s+\$([\d,\.]+)', l)
        if m and ward: wards[ward]['budget'] = M(m.group(1)); continue
        m = re.match(r'^\s*WARD COMMITTED 2026 TOTAL\s+\$([\d,\.]+)', l)
        if m and ward: wards[ward]['committed'] = M(m.group(1)); continue
        m = re.match(r'^\s*WARD 2026 BALANCE\s+\$([\d,\.]+)', l)
        if m and ward: wards[ward]['balance'] = M(m.group(1)); continue
        m = ITEM.match(l)
        if m and ward:
            items.append({'ward': ward, 'package': m.group('pkg').strip(), 'location': re.sub(r'\s+', ' ', m.group('loc')).strip(),
                          'estimated_2026_cost': M(m.group('cost')), 'pdf_page': pno})
sums = collections.Counter()
for it in items: sums[it['ward']] += it['estimated_2026_cost']
bad = []
for w, v in sorted(wards.items()):
    if v['committed'] is None or abs(sums[w] - v['committed']) > 0.02:
        bad.append((w, round(sums[w], 2), v['committed']))
print('items', len(items), 'wards', len(wards), 'sum', round(sum(sums.values()), 2), 'printed committed', round(sum(v['committed'] or 0 for v in wards.values()), 2))
print('wards not matching printed committed total:', bad)
pk = collections.Counter(); pks = collections.Counter()
for it in items:
    k = re.sub(r'\s*\(\d{4}\)$', '', it['package']); pk[k] += 1; pks[k] += it['estimated_2026_cost']
path = os.path.join(ROOT, 'data', 'city_capital_2026.json')
d = json.load(open(path)) if os.path.exists(path) else {}
d['aldermanic_menu_2026'] = {'source': {'url': URL, 'document': 'OBM Aldermanic Menu Program Q2 2026 Update', 'ward_summary_pdf_page': 4},
                             'note': 'Each ward has a $1.5M 2026 menu budget (capital bond funds). Items with $0 are supplemental and do not count against the balance.',
                             'wards': {str(k): {**v, 'sum_of_items': round(sums[k], 2)} for k, v in sorted(wards.items())},
                             'package_totals': {k: {'count': pk[k], 'total': round(pks[k], 2)} for k in sorted(pk, key=lambda x: -pks[x])},
                             'items': items, 'mismatched_wards': bad}
json.dump(d, open(path, 'w'), indent=1)
print('max single item', max(i['estimated_2026_cost'] for i in items))
print('items >= $1M', sum(1 for i in items if i['estimated_2026_cost'] >= 1e6))
