#!/usr/bin/env python3
"""Parse personnel appropriation lines (0003, 0005, 0015, 0020 ...) from the book's
department/fund appropriation pages. Gives 2026 rec, 2025 revised, 2025 appropriation and
2024 EXPENDITURES per line. Output raw/personnel/book_pers_lines.json
Page layout: top marker '(fund/org/auth)', footer 'Page N' + '057 - Dept name' + fund line.
"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pages = open(f'{ROOT}/raw/context/budget_recs_2026.txt').read().split('=====PAGE=====')
ACC = ('0003', '0005', '0008', '0011', '0012', '0015', '0020', '0021', '0022', '0024', '0027', '0028', '0032',
       '0039', '0060', '0061', '0062', '0063', '0070', '0088', '0091')
out = []
for i, pg in enumerate(pages):
    lines = [l.strip() for l in pg.split('\n') if l.strip()]
    if not lines: continue
    m = re.match(r'^\((\w{4})/(\d{4})(?:/(\w{4}))?\)$', lines[0])
    if not m: continue
    fund, org, auth = m.groups()
    dept = None
    for j, l in enumerate(lines):
        if l.startswith('Page ') and j + 1 < len(lines):
            d = re.match(r'^(\d{3}) - (.+)$', lines[j + 1])
            if d: dept = (str(int(d.group(1))), d.group(2))
    if not dept: continue
    for l in lines:
        mm = re.match(r'^(\w{4}) (.+?) ((?:\$?\(?[\d,]+\)?\s*){1,4})$', l)
        if not mm or mm.group(1) not in ACC: continue
        nums = [int(x.replace(',', '').replace('$', '').replace('(', '').replace(')', '')) for x in mm.group(3).split()]
        out.append(dict(page_idx=i, fund=fund, org=org, auth=auth, dept=dept[0], dept_name=dept[1],
                        acct=mm.group(1), name=mm.group(2), nums=nums))
json.dump(out, open(f'{ROOT}/raw/personnel/book_pers_lines.json', 'w'), indent=0)
print(len(out), 'lines')
