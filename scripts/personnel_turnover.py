#!/usr/bin/env python3
"""Parse Position Total / Turnover / Position Net Total blocks from the
2026 Budget Recommendations book text (raw/context/budget_recs_2026.txt,
extracted from budget_recs_2026.pdf) and reconcile with the ordinance.
Writes raw/personnel/turnover_blocks.json
"""
import json, re, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
txt = open(f'{ROOT}/raw/context/budget_recs_2026.txt').read()
pages = txt.split('=====PAGE=====')
num = r'\(?\$?[\d,]+\)?'
def n(s):
    neg = s.startswith('(')
    v = int(re.sub(r'[^\d]', '', s))
    return -v if neg else v
hdr = re.compile(r'Page (\d+)\n(\d{3}) - ([^\n]*)\n(\w{4}) - ([^\n]*)')
blocks = []
for i, pg in enumerate(pages):
    m = hdr.search(pg)
    if not m: continue
    page, dept, dname, fund, fname = m.groups()
    for key in ('Fund Position Total', 'Position Total', 'Turnover', 'Fund Position Net Total', 'Position Net Total'):
        pass
    for line in pg.split('\n'):
        mm = re.match(r'^(Fund Position Total|Position Total|Turnover|Fund Position Net Total|Position Net Total)\s+(.*)$', line.strip())
        if not mm: continue
        kind = mm.group(1)
        toks = re.findall(num, mm.group(2))
        if kind == 'Turnover':
            vals = [n(t) for t in toks]            # [2026, 2025rev, 2025approp]
        else:
            vals = [n(t) for t in toks]            # [cnt26, $26, cnt25rev, $25rev, cnt25app, $25app]
        blocks.append(dict(pdf_page_index=i, book_page=int(page), dept=str(int(dept)), dept_name=dname.strip(),
                           fund=fund, fund_name=fname.strip(), kind=kind, vals=vals))
os.makedirs(f'{ROOT}/raw/personnel', exist_ok=True)
json.dump(blocks, open(f'{ROOT}/raw/personnel/turnover_blocks.json', 'w'), indent=1)
print(len(blocks), 'blocks')

# ---------------------------------------------------------------------------
# Part 2: union salary schedules (book pages "Schedule B" ... "Schedule YZ")
# ---------------------------------------------------------------------------
sched = []
for i, pg in enumerate(pages):
    lines = [l.strip() for l in pg.split('\n') if l.strip()]
    sl = [l for l in lines if re.match(r'^Schedule [A-Z]{1,2}$', l)]
    if not sl or i < 600:
        continue
    code = sl[0].split()[1]
    pgn = next((l for l in lines if l.startswith('Page ')), '')
    units = next((l for l in lines if l.startswith('Units')), '')
    k0 = lines.index(sl[0])
    head = []
    for l in lines[k0 + 1:]:
        if l.startswith(('Units', 'Mayor', 'Page')) or re.match(r'^\S+ (Annual|Monthly)', l): break
        head.append(l)
    rows = []
    for l in lines:
        m = re.match(r'^(\S+) Annual ([\d,\. ]+)$', l)
        if m:
            vals = [float(x.replace(',', '')) for x in m.group(2).split()]
            rows.append(dict(grade=m.group(1), annual=vals))
    # header labels (step names) are everything between 'Class' and first data row
    hdr = []
    if 'Class' in lines:
        j = lines.index('Class')
        for l in lines[j:]:
            if re.match(r'^\S+ Annual', l): break
            hdr.append(l)
    sched.append(dict(schedule=code, book_page=pgn.replace('Page ', ''), units=units.replace('Units:', '').strip(),
                      title=head[:3], header=' '.join(hdr), rows=rows))
json.dump(sched, open(f'{ROOT}/raw/personnel/union_schedules.json', 'w'), indent=1)
print(len(sched), 'salary schedules', sum(len(s['rows']) for s in sched), 'grades')

# ---------------------------------------------------------------------------
# Part 3: subsection names (code - name) in position pages, to label sub_section_code
# ---------------------------------------------------------------------------
names = {}
for pg in pages[40:600]:
    for l in pg.split('\n'):
        m = re.match(r'^(\d{4}) - (.+)$', l.strip())
        if m:
            names.setdefault(m.group(1), set()).add(m.group(2).replace(' - Continued', '').strip())
json.dump({k: sorted(v) for k, v in names.items()}, open(f'{ROOT}/raw/personnel/book_code_names.json', 'w'), indent=0)
print(len(names), 'org/division/section codes named in book')

# ---------------------------------------------------------------------------
# Part 4: 2026 rate vs 2025-revised rate on the same row of the position tables
# ---------------------------------------------------------------------------
pat = re.compile(r'^([0-9A-Z]{4}) (.+?) (\d[\d,]*) \$?(\d[\d,]*\.?\d*)H? (\d[\d,]*) \$?(\d[\d,]*\.?\d*)H? (\d[\d,]*) \$?(\d[\d,]*\.?\d*)H?$')
pairs = []
for i, pg in enumerate(pages[40:600], start=40):
    for l in pg.split('\n'):
        m = pat.match(l.strip())
        if not m: continue
        try:
            r26 = float(m.group(4).replace(',', '')); r25 = float(m.group(6).replace(',', ''))
        except ValueError:
            continue
        if r25 > 0:
            pairs.append(dict(title_code=m.group(1), title=m.group(2), c26=int(m.group(3).replace(',', '')), r26=r26,
                          c25=int(m.group(5).replace(',', '')), r25=r25, page_idx=i))
json.dump(pairs, open(f'{ROOT}/raw/personnel/rate_pairs.json', 'w'))
print(len(pairs), 'rate pairs')

# ---------------------------------------------------------------------------
# Part 5: the same blocks from the PASSED ordinance (raw/gap/ord_2026.txt, from
# scripts/gap_fetch.py). The ordinance amended turnover (Technical Amendments,
# "LESS TURNOVER" lines), so these, not the recommendation book, tie to the
# ordinance's "Salaries and Wages - on Payroll" lines. Writes ord_turnover_blocks.json
# ---------------------------------------------------------------------------
ordp = f'{ROOT}/raw/gap/ord_2026.txt'
if os.path.exists(ordp):
    opages = open(ordp).read().split('=====PAGE')
    ohdr = re.compile(r'Annual Appropriation Ordinance for Year 2026\nPage (\d+)\n(\d{3}) - ([^\n]*)\n(\w{4}) - ([^\n]*)\n')
    oblocks = []
    for i, pg in enumerate(opages):
        m = ohdr.search(pg)
        if not m: continue
        for line in pg.split('\n'):
            mm = re.match(r'^(Fund Position Total|Position Total|Turnover|Fund Position Net Total|Position Net Total)\s+(.*)$', line.strip())
            if mm:
                oblocks.append(dict(ord_page=int(m.group(1)), dept=str(int(m.group(2))), dept_name=m.group(3).strip(),
                                    fund=m.group(4), fund_name=m.group(5).strip(), kind=mm.group(1),
                                    vals=[n(x) for x in re.findall(num, mm.group(2))]))
    json.dump(oblocks, open(f'{ROOT}/raw/personnel/ord_turnover_blocks.json', 'w'), indent=1)
    print(len(oblocks), 'ordinance blocks')
