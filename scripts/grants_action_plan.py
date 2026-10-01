#!/usr/bin/env python3
"""Parse AP-15 (expected resources) and AP-38 (project summaries) from the City's 2026 HUD Annual Action Plan.
Source: https://www.chicago.gov/content/dam/city/depts/obm/supp_info/Grants_Management/2026%20Annual%20Action%20Plan%20Final.pdf
Output: appended to data/city_grants_2026.json under 'hud_action_plan_2026'.
"""
import json, os, re, subprocess
import pypdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'raw', 'grants')
URL = 'https://www.chicago.gov/content/dam/city/depts/obm/supp_info/Grants_Management/2026%20Annual%20Action%20Plan%20Final.pdf'
PDF = os.path.join(RAW, 'action_plan_2026.pdf')
os.makedirs(RAW, exist_ok=True)
if not os.path.exists(PDF):
    subprocess.check_call(['curl', '-sL', '-A', 'Mozilla/5.0', '-o', PDF, URL])
r = pypdf.PdfReader(PDF)
pages = [p.extract_text() or '' for p in r.pages]

# AP-15 programs (pdf pages 20-24): annual allocation, program income, prior year, total
res = []
for i in range(19, 25):
    t = pages[i]
    for m in re.finditer(r'\b(CDBG|HOME|HOPWA|ESG|Other|General Fund|Section 108)\b.*?([\d,]+\.\d\d)\s+([\d,]+\.\d\d)\s+([\d,]+\.\d\d)\s+([\d,]+\.\d\d)\s+([\d,]+\.\d\d)', t, re.S):
        res.append({'program': m.group(1), 'annual_allocation': float(m.group(2).replace(',', '')), 'program_income': float(m.group(3).replace(',', '')),
                    'prior_year': float(m.group(4).replace(',', '')), 'total_2026': float(m.group(5).replace(',', '')),
                    'remainder_of_conplan': float(m.group(6).replace(',', '')), 'pdf_page': i + 1})

# AP-38 project summaries (pdf pages 34-80)
txt = '\n'.join(f'[[PAGE {i+1}]]\n' + re.sub(r'\s*Annual Action Plan\s*\n\s*2026\s*\n\s*\d+\s*\nOMB Control No:[^\n]*\n', '\n', pages[i]) for i in range(33, len(pages)))
projects = []
parts = re.split(r'\n(?=\d{1,3} Project Name )', txt)
for part in parts[1:]:
    m = re.match(r'(\d{1,3}) Project Name\s+(.+?)\n(?:Target Area|Goals)', part, re.S)
    if not m:
        continue
    name = re.sub(r'\s+', ' ', m.group(2)).strip()
    f = re.search(r'Funding\s+(.+?)\n(?:Description)', part, re.S)
    funds = []
    if f:
        for fm in re.finditer(r'(CDBG|HOME|HOPWA|ESG|CDBG-DR|Other|General Fund)\s*:\s*\$([\d,]+(?:\.\d\d)?)', f.group(1)):
            funds.append({'source': fm.group(1), 'amount': float(fm.group(2).replace(',', ''))})
    pg = re.findall(r'\[\[PAGE (\d+)\]\]', part)
    first_page = None
    pm = re.search(r'\[\[PAGE (\d+)\]\]', txt[:txt.find(part)][-4000:][::-1][::-1]) if False else None
    projects.append({'project_number': int(m.group(1)), 'name': name, 'funding': funds, 'total': sum(x['amount'] for x in funds),
                     'target_date': (re.search(r'Target Date\s+(\S+)', part) or [None, None])[1]})
# attach pdf page: locate each name in pages
for p in projects:
    for i in range(33, len(pages)):
        if re.search(r'Project Name\s+' + re.escape(p['name'][:25]), re.sub(r'\s+', ' ', pages[i]).replace('Project Name ', 'Project Name  ')) or p['name'][:30] in re.sub(r'\s+', ' ', pages[i]):
            p['pdf_page'] = i + 1; break
by_src = {}
for p in projects:
    for f in p['funding']:
        by_src[f['source']] = by_src.get(f['source'], 0) + f['amount']
print('AP-15 rows', len(res)); 
for x in res: print('  ', x)
print('AP-38 projects', len(projects), 'by source', {k: round(v, 2) for k, v in by_src.items()})
path = os.path.join(ROOT, 'data', 'city_grants_2026.json')
d = json.load(open(path))
d['hud_action_plan_2026'] = {'source': {'url': URL, 'document': 'City of Chicago 2026 Annual Action Plan (HUD CDBG, HOME, ESG, HOPWA)', 'ap15_pdf_pages': '19-24', 'ap38_pdf_pages': '33-80'},
                             'expected_resources': res, 'projects': projects, 'project_totals_by_source': by_src}
json.dump(d, open(path, 'w'), indent=1)
