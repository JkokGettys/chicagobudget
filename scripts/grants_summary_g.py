#!/usr/bin/env python3
"""Parse 2026 Budget Recommendations, Grant Detail (PDF pp. 614-624, printed pp. 605-615)
and join to the budget ordinance (raw/city_appropriations_2026.json).

Source PDF: https://occprodstoragev1.blob.core.usgovcloudapi.net/matterattachmentspublic/ddaf5dca-b40a-4ed4-a99a-7a5962987d2b.pdf
Output: data/city_grants_2026.json
"""
import json, os, re, subprocess, sys, collections
import pypdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'raw', 'grants')
URL = 'https://occprodstoragev1.blob.core.usgovcloudapi.net/matterattachmentspublic/ddaf5dca-b40a-4ed4-a99a-7a5962987d2b.pdf'
PDF = os.path.join(RAW, 'summaryG.pdf')
FIRST, LAST = 614, 624  # 1-based PDF pages of Grant Detail

os.makedirs(RAW, exist_ok=True)
if not os.path.exists(PDF):
    subprocess.check_call(['curl', '-sL', '-o', PDF, URL])
reader = pypdf.PdfReader(PDF)

LINE = re.compile(r'^\s*(?P<fund>[0-9A-Z]{4}):(?P<auth>[0-9A-Z]{4}):(?P<name>.*?)\s{2,}(?P<nums>[\$\d,\s]+)$')
LINE_NONUM = re.compile(r'^\s*(?P<fund>[0-9A-Z]{4}):(?P<auth>[0-9A-Z]{4}):(?P<name>.*\S)\s*$')
DEPT = re.compile(r'^(?P<num>\d{3}) - (?P<name>.+\S)\s*$')
CATS = {'Finance and Administration', 'Infrastructure Services', 'Public Safety',
        'Community Services', 'City Development', 'Regulatory'}


def cols(layout_line):
    """Return dict of 4 numeric columns by x-position bucket."""
    out = {}
    for m in re.finditer(r'\$?[\d,]{1,}', layout_line):
        pass
    return out


def parse():
    rows, dept_totals, cat_totals = [], {}, {}
    cat = dept = dept_name = None
    page_dept = None
    for pno in range(FIRST, LAST + 1):
        txt = reader.pages[pno - 1].extract_text(extraction_mode='layout')
        # header x-positions for the 4 numeric columns
        hdr = [l for l in txt.splitlines() if '2025 Grant' in l]
        hx = None
        if hdr:
            h = hdr[0]
            hx = [h.index('2025 Grant'), h.index('2026 Anticipated'), h.index('Carryover'), h.index('2026 Total')]
        printed = re.search(r'Page (\d+)', txt)
        for line in txt.splitlines():
            s = line.strip()
            if not s:
                continue
            if s in CATS:
                cat = s
                continue
            m = re.match(r'^(\d{3}) - (.+?)\s*$', s)
            if m and not line.startswith('  '):
                dept, dept_name = m.group(1), m.group(2)
                continue
            m = re.match(r'^\s*Total - (\d{3}) - (.+?)\s{2,}(.*)$', line)
            if m:
                nums = [int(x.replace(',', '')) for x in re.findall(r'[\d,]+', m.group(3))]
                dept_totals[m.group(1)] = {'name': m.group(2), 'numbers': nums, 'line': s}
                continue
            m = re.match(r'^Total - (Finance and Administration|Infrastructure Services|Public Safety|Community Services|City Development|Regulatory|All Programs)\s{2,}(.*)$', s)
            if m:
                nums = [int(x.replace(',', '')) for x in re.findall(r'[\d,]+', m.group(2))]
                cat_totals[m.group(1)] = nums
                continue
            m = re.match(r'^\s*([0-9A-Z]{4}):([0-9A-Z]{4}):(.*)$', line)
            if m and dept:
                fund, auth, rest = m.groups()
                # split name from numbers: find first '$' or digit group after 2+ spaces
                nm = re.match(r'^(.*?)(\s{2,}.*)?$', rest)
                name = nm.group(1).strip()
                numpart = rest[len(nm.group(1)):] if nm.group(2) else ''
                vals = {'2025_grant': 0, '2026_anticipated': 0, 'carryover': 0, '2026_total': 0}
                if numpart.strip():
                    base = len(line) - len(rest) + len(nm.group(1))
                    keys = ['2025_grant', '2026_anticipated', 'carryover', '2026_total']
                    for mm in re.finditer(r'\$?[\d,]+', numpart):
                        end = base + mm.end()
                        # assign to nearest header column by right-edge
                        ends = [hx[0] + len('2025 Grant'), hx[1] + len('2026 Anticipated'),
                                hx[2] + len('Carryover'), hx[3] + len('2026 Total')]
                        k = min(range(4), key=lambda i: abs(ends[i] - end))
                        vals[keys[k]] = int(mm.group().replace('$', '').replace(',', ''))
                rows.append({'category': cat, 'dept_number': dept, 'dept_name': dept_name, 'fund_code': fund,
                             'authority_code': auth, 'grant_name': name, **vals, 'pdf_page': pno,
                             'printed_page': int(printed.group(1)) if printed else None})
    return rows, dept_totals, cat_totals


def main():
    rows, dept_totals, cat_totals = parse()
    # sanity: 4-column rows
    tot = sum(r['2026_total'] for r in rows)
    print('grant lines', len(rows), '2026 total', tot, 'expected', cat_totals.get('All Programs'))
    # check dept totals
    bad = 0
    byd = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        v = byd[r['dept_number']]
        v[0] += r['2025_grant']; v[1] += r['2026_anticipated']; v[2] += r['carryover']; v[3] += r['2026_total']
    for d, t in dept_totals.items():
        calc = byd.get(d, [0, 0, 0, 0])
        if t['numbers'] and t['numbers'][-1] != calc[3]:
            bad += 1
            print('MISMATCH dept', d, t['name'], t['numbers'], calc)
    print('dept mismatches', bad)

    # join to ordinance
    ordn = json.load(open(os.path.join(ROOT, 'raw', 'city_appropriations_2026.json')))
    ox = collections.defaultdict(list)
    for o in ordn:
        if o['fund_type'] == 'GRANTS':
            ox[(o['fund_code'], str(int(o['department_number'])).zfill(3), o['appropriation_authority'])].append(o)
    out_rows = []
    matched_keys = set()
    for r in rows:
        k = (r['fund_code'], r['dept_number'], r['authority_code'])
        lines = ox.get(k, [])
        matched_keys.add(k)
        ord_total = sum(float(x['_ordinance_amount_']) for x in lines)
        reserve = sum(float(x['_ordinance_amount_']) for x in lines if x['appropriation_account'] == '909A')
        r = dict(r)
        r['ordinance_total'] = int(ord_total)
        r['ordinance_reserve_balance'] = int(reserve)
        r['ordinance_accounts'] = [{'account': x['appropriation_account'], 'description': x['appropriation_account_description'],
                                   'amount': int(float(x['_ordinance_amount_']))} for x in lines]
        r['match'] = 'exact' if ord_total == r['2026_total'] else ('none' if not lines else 'diff')
        out_rows.append(r)
    unmatched_ord = []
    for k, lines in ox.items():
        if k not in matched_keys:
            for x in lines:
                unmatched_ord.append({'fund': k[0], 'dept': k[1], 'authority': k[2], 'desc': x['appropriation_authority_description'],
                                      'account': x['appropriation_account_description'], 'amount': int(float(x['_ordinance_amount_']))})
    stat = collections.Counter(r['match'] for r in out_rows)
    print('match stats', stat)
    print('ordinance grant $ in Summary G lines:', sum(r['ordinance_total'] for r in out_rows))
    print('ordinance grant $ unmatched:', sum(u['amount'] for u in unmatched_ord))
    res = {
        'source': {'url': URL, 'document': '2026 Budget Recommendations (Mayor Johnson), Grant Detail',
                   'pdf_pages': f'{FIRST}-{LAST}', 'printed_pages': '605-615',
                   'summary_pdf_page': 613, 'summary_printed_page': 604,
                   'ordinance_dataset': 'https://data.cityofchicago.org/resource/6694-f78c.json'},
        'notes': ['2026 Total = 2026 Anticipated Grant + Carryover. Carryover is calculated at Aug 1 of the prior fiscal year.',
                  'Amounts are authorizations to spend if awarded, not cash in hand.',
                  'Join key to ordinance: fund_code + department_number + appropriation_authority (authority code = grant code).'],
        'totals': {'all_programs_pdf': cat_totals.get('All Programs'), 'sum_of_lines_2026_total': tot,
                   'ordinance_grants_total': sum(float(o['_ordinance_amount_']) for o in ordn if o['fund_type'] == 'GRANTS')},
        'category_totals': cat_totals, 'department_totals': dept_totals,
        'grants': out_rows, 'unmatched_ordinance_grant_lines': unmatched_ord,
    }
    json.dump(res, open(os.path.join(ROOT, 'data', 'city_grants_2026.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
