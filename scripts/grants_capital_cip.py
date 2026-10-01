#!/usr/bin/env python3
"""Parse the City of Chicago 2025-2029 Capital Improvement Program (latest CIP published on chicago.gov
as of 2026-09-30; a 2026-2030 CIP was NOT found, see research/grants_capital.md).

Source PDF: https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CIP/City%20of%20Chicago%202025-2029%20CIP.pdf
Parses (a) project pages: project id, name, phases, per-fund amounts (Total, Prior Years, 2025, 2025-2029), location
         (b) fund summary pages: per program/subprogram/fund type/fund yearly amounts 2025..2029 (gives the 2026 column)
Output: data/city_capital_2026.json
"""
import json, os, re, subprocess, collections
import pypdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'raw', 'grants')
URL = 'https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CIP/City%20of%20Chicago%202025-2029%20CIP.pdf'
PDF = os.path.join(RAW, 'cip2025.pdf')
os.makedirs(RAW, exist_ok=True)
if not os.path.exists(PDF):
    subprocess.check_call(['curl', '-sL', '-A', 'Mozilla/5.0', '-o', PDF, URL])

reader = pypdf.PdfReader(PDF)
def N(s):
    s = s.replace('$', '').replace(',', '').strip()
    neg = s.startswith('(') and s.endswith(')')
    s = s.strip('()')
    return -int(s) if neg and s else (int(s) if s else 0)

NUM = r'\$?\s?[\d,]+'

PROJ_START = re.compile(r'^\s{4,12}(\d{4,6})\s{1,6}(\S.*?)\s*$')
V = r'\(?-?[\d,]+\)?'
FUND_ROW = re.compile(r'(?P<code>[0-9A-Z]{3,4}) - (?P<type>[A-Za-z\-]+)\s+(?P<total>' + V + r')\s+(?P<prior>' + V + r')\s+(?P<y1>' + V + r')\s+(?P<five>' + V + r')\s*$')
TOTAL_ROW = re.compile(r'^\s+\$?(' + V + r')\s+\$?(' + V + r')\s+\$?(' + V + r')\s+\$?(' + V + r')\s*$')
PHASE = re.compile(r'(Design|Construct\.)\s+(\d{4})\s+(\d{4})')
SUBTOTAL = re.compile(r'^\s*([A-Z0-9 &/\-\.,\']+?) Total\s+\$([\d,]+)\s+\$([\d,]+)\s+\$([\d,]+)\s+\$([\d,]+)\s*$')


PHASE_TOTAL = re.compile(r'(?:Design|Construct\.)\s+\d{4}\s+\d{4}\s+\$?(' + V + r')\s+\$?(' + V + r')\s+\$?(' + V + r')\s+\$?(' + V + r')\s*$')


def parse_projects():
    projects, subtotals = [], {}
    cur = None
    for pno, page in enumerate(reader.pages, start=1):
        txt = page.extract_text(extraction_mode='layout')
        lines = txt.splitlines()
        if not lines or '2025 - 2029 Capital Improvement Program' not in lines[0] + ''.join(lines[:3]):
            continue
        prog = None
        for l in lines[:8]:
            if re.match(r'^\s*[A-Z][A-Z &/\-\.,\']+ - [A-Z0-9 &/\-\.,\'\(\)]+\s*$', l) and 'Capital Improvement' not in l:
                prog = l.strip(); break
        pending_loc = False
        for l in lines:
            m = SUBTOTAL.match(l)
            if m:
                subtotals[m.group(1).strip()] = {'total': N(m.group(2)), 'prior_years': N(m.group(3)), 'y2025': N(m.group(4)), 'five_year': N(m.group(5)), 'pdf_page': pno}
                cur = None
                continue
            m = PROJ_START.match(l)
            if m and not FUND_ROW.search(l) and not re.match(r'^\s+\d{4,6}\s+[\d,]+$', l):
                if cur is not None and cur['cip_id'] == m.group(1) and cur['program_subprogram'] == prog:
                    cur.setdefault('pdf_pages', [cur['pdf_page']]).append(pno)  # continuation page (long location list)
                    continue
                cur = {'cip_id': m.group(1), 'name': m.group(2), 'program_subprogram': prog, 'phases': [], 'funds': [], 'location': None, 'pdf_page': pno, 'total': None}
                projects.append(cur); pending_loc = False
                continue
            if cur is None:
                continue
            for ph in PHASE.finditer(l):
                cur['phases'].append({'phase': ph.group(1), 'start': int(ph.group(2)), 'end': int(ph.group(3))})
            fm = FUND_ROW.search(l)
            if fm:
                cur['funds'].append({'fund_code': fm.group('code'), 'fund_type': fm.group('type'), 'total': N(fm.group('total')),
                                     'prior_years': N(fm.group('prior')), 'y2025': N(fm.group('y1')), 'five_year_2025_2029': N(fm.group('five'))})
                continue
            pt = PHASE_TOTAL.search(l)
            if pt and cur['total'] is None:
                cur['total'] = {'total': N(pt.group(1)), 'prior_years': N(pt.group(2)), 'y2025': N(pt.group(3)), 'five_year_2025_2029': N(pt.group(4))}
                pending_loc = True
                continue
            tm = TOTAL_ROW.match(l)
            if tm and cur['funds'] and cur['total'] is None:
                cur['total'] = {'total': N(tm.group(1)), 'prior_years': N(tm.group(2)), 'y2025': N(tm.group(3)), 'five_year_2025_2029': N(tm.group(4))}
                pending_loc = True
                continue
            if pending_loc and l.strip() and not l.startswith('      ' ) :
                cur['location'] = l.strip()[:200]; pending_loc = False
            elif pending_loc and l.strip():
                pass
    return projects, subtotals


def parse_fund_summary():
    """Fund summary pages: per program/subprogram/fund type/fund yearly amounts 2025..2029 + 5yr total.
    Columns are assigned by right-edge x position of each number relative to the header line."""
    rows, totals = [], []
    prog = sub = ftype = None
    for pno, page in enumerate(reader.pages, start=1):
        txt = page.extract_text(extraction_mode='layout')
        if 'Fund Summary by Capital Program' not in txt[:400]:
            continue
        lines = txt.splitlines()
        hdr = next((l for l in lines if 'Fund Source' in l), None)
        if hdr is None or not all(y in hdr for y in ('2025', '2026', '2027', '2028', '2029')):
            continue
        ends = [hdr.index(y) + 4 for y in ('2025', '2026', '2027', '2028', '2029')] + [len(hdr.rstrip())]
        keys = ['y2025', 'y2026', 'y2027', 'y2028', 'y2029', 'five_year']

        def assign(rest_line):
            out = {k: 0 for k in keys}
            for mm in re.finditer(r'[\d,]*\d', rest_line):
                e = mm.end()
                k = min(range(6), key=lambda i: abs(ends[i] - e))
                out[keys[k]] = N(mm.group())
            return out
        for l in lines:
            m = re.match(r'^\s*Program\s+(.+?)\s*$', l)
            if m: prog = m.group(1); continue
            m = re.match(r'^\s*Subprogram\s+(.+?)\s*$', l)
            if m: sub = m.group(1); continue
            m = re.match(r'^\s*Fund Type:\s*(.+?)\s*$', l)
            if m: ftype = m.group(1); continue
            m = re.match(r'^(\s*Total (.+?))(\s{2,}.*)$', l)
            if m:
                label = m.group(2).strip()
                vals = assign(l[len(m.group(1)):].replace('$', ' ') if False else l.replace('$', ' '))
                # strip label digits (labels like "Total Bond" have none)
                kind = 'fund_type' if label.split()[0] in ('Bond', 'City', 'Federal', 'State', 'TIF', 'Other', 'Private', 'Federal-WIFIA', 'State-IEPA') else ('subprogram' if label.upper() != (prog or '').upper() and not (prog or '').upper().startswith(label.upper()) else 'program')
                totals.append({'program': prog, 'subprogram': sub, 'fund_type_ctx': ftype, 'label': label, 'level': kind, **vals, 'pdf_page': pno})
                continue
            m = re.match(r'^\s*([0-9A-Z]{3,4})\s{2,}(\S.*?)\s{2,}[\$\d]', l)
            if m and prog and sub and ftype:
                tail = l[m.end(2):]
                vals = assign(tail.replace('$', ' '))
                rows.append({'program': prog, 'subprogram': sub, 'fund_type': ftype, 'fund_code': m.group(1), 'fund_name': m.group(2), **vals, 'pdf_page': pno})
    return rows, totals


def main():
    projects, subtotals = parse_projects()
    fs_rows, fs_tot = parse_fund_summary()
    print('projects', len(projects), 'fund summary rows', len(fs_rows), 'totals', len(fs_tot))
    # integrity 1: sum of project 5-year amounts per subprogram vs fund-summary printed subprogram 5-year total
    sub_tot = {(t['program'], t['label']): t for t in fs_tot if t['level'] == 'subprogram'}
    by_sub = collections.Counter(); by_sub_total = collections.Counter(); by_sub_y25 = collections.Counter()
    for p in projects:
        if p['total']:
            by_sub[p['program_subprogram']] += p['total']['five_year_2025_2029']
            by_sub_total[p['program_subprogram']] += p['total']['total']
            by_sub_y25[p['program_subprogram']] += p['total']['y2025']
    checks = []
    for sp in by_sub:
        prog, _, sub = sp.partition(' - ')
        t = sub_tot.get((prog, sub.strip()))
        checks.append({'program_subprogram': sp, 'projects_five_year': by_sub[sp], 'projects_2025': by_sub_y25[sp], 'projects_total_cost': by_sub_total[sp],
                       'fund_summary_five_year': t and t['five_year'], 'fund_summary_2025': t and t['y2025'],
                       'matches': bool(t) and t['five_year'] == by_sub[sp] and t['y2025'] == by_sub_y25[sp]})
    print('subprograms where project sum == fund summary (2025 and 5yr):', sum(c['matches'] for c in checks), '/', len(checks))
    for c in checks:
        if not c['matches']:
            print('  CHECK', c)
    # projects with no parsed total
    print('projects without total:', sum(1 for p in projects if not p['total']))
    # derive 2026-2029 remaining per project (project pages only give 2025 and 5-year columns)
    for p in projects:
        if p['total']:
            p['remaining_2026_2029'] = p['total']['five_year_2025_2029'] - p['total']['y2025']
    out = {'source': {'url': URL, 'document': 'City of Chicago 2025-2029 Capital Improvement Program Report (latest CIP on chicago.gov as of 2026-09-30)',
                      'project_pages_pdf': '30-348 (alternating with fund summary pages)'},
           'notes': ['Project pages give Total project cost, Prior Years, 2025, and 2025-2029 columns only. Single-year 2026 amounts exist only at fund summary level (fund_summary_rows / fund_summary_totals).',
                     'remaining_2026_2029 = five_year_2025_2029 - y2025 (derived, not printed).',
                     'The 2026-2030 CIP was not found on the chicago.gov Capital Publications page as of 2026-09-30.'],
           'projects': projects, 'integrity_checks': checks,
           'fund_summary_rows': fs_rows, 'fund_summary_totals': fs_tot}
    json.dump(out, open(os.path.join(ROOT, 'data', 'city_capital_2026.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
