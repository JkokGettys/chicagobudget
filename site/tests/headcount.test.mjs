import assert from 'node:assert/strict';
import {readFile, readdir} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import {test} from 'node:test';
import ts from 'typescript';
const source = await readFile(new URL('../src/lib/headcount.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
const {buildStaffingIndex, staffingText, staffingSources, isPersonnelNode} = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
const sources = [{name: '2026 Budget Ordinance Positions and Salaries'}, {dataset: 'CPS FY2026 budget positions by unit and job title'}, {doc: 'Chicago Park District 2026 Budget Appropriations'}];
const parent = {id:'city.test.pay-for-workers', root:'city', kind:'category'};
const position = (suffix, count, overrides = {}) => ({id:`${parent.id}.${suffix}`, parent_id:parent.id, root:'city', kind:'job_title', count, unit_label:'positions', source:0, basis:'tied', ...overrides});

test('known zero is retained, missing/invalid counts are unavailable rather than inferred', () => {
  for (const value of [null, undefined, -1, Infinity, NaN, '7']) {
    const n = position('title', value, {amount_cents:10000000});
    assert.deepEqual(buildStaffingIndex([n], sources)[n.id].counts, []);
  }
  const n = position('zero', 0);
  assert.equal(buildStaffingIndex([n],sources)[n.id].counts[0].value, 0);
  assert.match(staffingText(buildStaffingIndex([n],sources)[n.id]).lines[0], /^0 budgeted positions/);
});

test('aggregation stops at count frontier and deduplicates node IDs', () => {
  const title = position('title', 8);
  const child = position('title.rate', 8, {parent_id:title.id, kind:'pay_rate'});
  const other = position('other', 2);
  const index = buildStaffingIndex([parent,title,child,other,child],sources);
  assert.equal(index[parent.id].counts[0].value,10);
  assert.equal(index[parent.id].complete,true);
  assert.equal(index[title.id].counts[0].value,8);
  assert.match(staffingText(index[parent.id]).lines[0], /10 budgeted positions listed/);
});

test('hours, health enrollment, pension members and beneficiaries are not payroll headcounts', () => {
  const excluded = [position('hours',2080,{unit_label:'hours'}),position('health',424,{kind:'health_plan',unit_label:'people',basis:'proxy'}),position('pension',23350,{kind:'box',unit_label:'people paid by the pension fund',basis:'proxy'}),position('retirees',2125,{kind:'benefit_group',unit_label:'retirees',basis:'proxy'})];
  const index=buildStaffingIndex([parent,position('known',2),...excluded],sources);
  assert.equal(index[parent.id].counts[0].value,2);
  assert.equal(index[parent.id].complete,false);
  assert.match(staffingText(index[parent.id]).note,/Partial coverage/);
  for (const n of excluded) assert.deepEqual(index[n.id].counts,[]);
});

test('mixed hourly titles descend to real position children but remain partial', () => {
  const title=position('mixed',145626,{unit_label:'hours'});
  const index=buildStaffingIndex([title,position('mixed.positions',26,{parent_id:title.id,kind:'pay_rate'}),position('mixed.hours',145600,{parent_id:title.id,kind:'pay_rate',unit_label:'hours'})],sources);
  assert.equal(index[title.id].counts[0].value,26);
  assert.equal(index[title.id].complete,false);
});

test('counts keep explicit periods separate and do not invent missing source years', () => {
  const a=position('old',2,{period_label:'2025'}),b=position('new',3,{period_label:'2026'});
  const index=buildStaffingIndex([parent,a,b],sources);
  assert.deepEqual(index[parent.id].counts.map(c=>[c.period,c.value]),[['2025',2],['2026',3]]);
  assert.equal(buildStaffingIndex([a],sources)[a.id].counts[0].period,'2025');
  const unknown=position('unknown',1);
  assert.equal(buildStaffingIndex([unknown],[{name:'Undated positions'}])[unknown.id].counts[0].period,'Period not stated');
  assert.deepEqual(buildStaffingIndex([unknown],[])[unknown.id].counts,[]);
});

test('CPS uses precise source FTE including small-title groups, never group row counts', () => {
  const p={id:'cps.test.salaries',root:'cps'};
  const a={id:`${p.id}.a51100.teacher`,parent_id:p.id,root:'cps',kind:'job_title',basis:'proxy',source:1,count:5.3,unit_label:'positions (FTE)',extra:{fte:5.25}};
  const b={...a,id:`${p.id}.a51100.other-titles`,kind:'job_title_group',count:null,unit_label:null,extra:{fte:7.75,titles_in_group:6}};
  const summary=buildStaffingIndex([p,a,b],sources)[p.id];
  assert.equal(summary.counts[0].value,13);
  assert.equal(summary.counts[0].unit,'FTEs');
  assert.equal(summary.counts[0].period,'FY2026 (Jul 2025 to Jun 2026)');
  assert.match(staffingText(summary).note,/no fund breakdown/);
});

test('Parks preserves fractional FTEs and missing exports are not called zero', () => {
  const p={id:'parks.test.611005',root:'parks'};
  const n={id:`p.1`,parent_id:p.id,root:'parks',kind:'position',basis:'budget',source:2,count:0.6,unit_label:'full-time equivalents'};
  const unknown={...n,id:'p.2',count:null,unit_label:null};
  const summary=buildStaffingIndex([p,n,unknown],sources)[p.id];
  assert.equal(summary.counts[0].value,0.6);
  assert.equal(summary.complete,false);
});

test('unrelated pages receive no count summary or unavailable banner', () => {
  for (const id of ['city','city.health','city.retirement','parks','parks.retirement-pensions','cps.pensions','cps.citywide.food','city.test.contracts-and-services']) {
    assert.equal(isPersonnelNode({id}),false);
    assert.deepEqual(buildStaffingIndex([{id}],sources),{});
  }
});

test('missing child records make an aggregate partial; adjustments do not add positions', () => {
  const n=position('known',2);
  const adjustment={id:`parent.adjustment`,parent_id:parent.id,kind:'adjustment',basis:'adjustment',count:1000};
  assert.equal(buildStaffingIndex([{...parent,n_children:3},n,adjustment],sources)[parent.id].complete,false);
  const complete=buildStaffingIndex([{...parent,n_children:2},n,adjustment],sources)[parent.id];
  assert.equal(complete.complete,true);
  assert.equal(complete.counts[0].value,2);
});

const base=new URL('../public/data/',import.meta.url);
const realSources=JSON.parse(await readFile(new URL('sources.json',base),'utf8'));
const files=await readdir(new URL('chunks/',base));
const nodes=(await Promise.all(files.filter(f=>f.endsWith('.json')).map(async f=>JSON.parse(await readFile(new URL(`chunks/${f}`,base),'utf8')).nodes))).flat();
const index=buildStaffingIndex(nodes,realSources);

test('real O Hare node shows eight budgeted positions, not twelve in cross-fund payroll side facts', () => {
  const n=nodes.find(n=>n.id.endsWith('7020-general-manager-of-airport-operations') && n.id.includes('0740-2015-0005'));
  assert.ok(n);
  assert.equal(n.side.find(f=>f.kind==='pay_2025').extra.group.budget_2026_positions,12);
  assert.equal(index[n.id].counts[0].value,8);
  assert.match(staffingText(index[n.id]).lines[0],/^8 budgeted positions · 2026$/);
});

test('real salary pages have sourced counts with appropriate units and unrelated pages do not', () => {
  const cases=[['city.infrastructure-services.chicago-department-of-aviation.pay-for-workers','positions'],['parks.maintaining-the-parks.facilities-management-8460.corporate-fund.611005','FTEs'],['cps.central.operations-offices.u12510.salaries.a52100','FTEs']];
  for(const [id,unit] of cases){assert.ok(index[id].counts.length,id);assert.equal(index[id].counts[0].unit,unit);assert.ok(index[id].counts[0].sources.length);}
  assert.equal(index['city.health'],undefined);
  assert.equal(index['cps.pensions'],undefined);
  const encoded=JSON.stringify(index);
  console.log(`Staffing index: ${Object.keys(index).length} pages, ${Buffer.byteLength(encoded)} bytes JSON, ${gzipSync(encoded).length} bytes gzip`);
  for(const [id] of cases)console.log(id,JSON.stringify(index[id]));
});

test('adjustment subtrees cannot inflate staffing totals', () => {
  const adjustment=position('adjustment',1000,{kind:'adjustment',basis:'tied'});
  const child=position('adjustment.title',2000,{parent_id:adjustment.id});
  const summary=buildStaffingIndex([parent,position('real',2),adjustment,child],sources)[parent.id];
  assert.equal(summary.counts[0].value,2);
});

test('source links deduplicate documents and reject unsafe URLs', () => {
  const summary={counts:[{sources:[0,1,2,3,4,99]}]};
  const docs=[{name:'City positions',url:'https://example.org/positions'},{name:'City positions',url:'https://example.org/positions'},{name:'No public URL'},{name:'Unsafe URL',url:'javascript:alert(1)'},{name:'Parks FTEs',url:'https://example.org/parks'}];
  const citations=staffingSources(summary,docs,s=>s.url);
  assert.equal(citations.length,4);
  assert.equal(citations.filter(s=>s.url).length,2);
  assert.equal(citations.find(s=>s.label==='Unsafe URL').url,undefined);
});

test('CPS export never repeats the same unit/account/title source group across funds', () => {
  const seen=new Set();
  for (const n of nodes.filter(n=>n.root==='cps' && ['job_title','job_title_group'].includes(n.kind))) {
    const unit=n.id.match(/\.u(\d+)\./)?.[1];
    const account=n.id.match(/\.(a51100|a52100)\./)?.[1];
    assert.ok(unit && account,n.id);
    const key=JSON.stringify([unit,account,n.id.split('.').at(-1)]);
    assert.equal(seen.has(key),false,`Repeated source group requires revisiting aggregation: ${key}`);
    seen.add(key);
  }
});

test('both actual page renderers integrate counts without replacing title helpers', async () => {
  const staticPage=await readFile(new URL('../src/components/BoxPage.astro',import.meta.url),'utf8');
  const shell=await readFile(new URL('../src/pages/box-shell.astro',import.meta.url),'utf8');
  assert.match(staticPage,/<StaffingCount id=\{displayed.id\}/);
  assert.match(shell,/renderStaffingCount\(staffingElement,record.id,sources,sourceUrl\)/);
  assert.match(staticPage,/displayName\(displayed\)/);
  assert.match(shell,/displayName\(record\)/);
});
