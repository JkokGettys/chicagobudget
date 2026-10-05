import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4321';
const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
const output=process.env.SCREENSHOT_DIR||process.env.JCODE_SCRATCH_DIR;
try{
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const cases=[
    ['city','city.infrastructure-services.chicago-department-of-aviation.pay-for-workers', '2,256 budgeted positions',true],
    ['parks','parks.maintaining-the-parks.facilities-management-8460.corporate-fund.611005','16 budgeted FTEs',false],
    ['cps','cps.central.operations-offices.u12510.salaries.a52100','151 budgeted FTEs',false],
  ];
  for(const [root,id,label,partial]of cases){
    const response=await page.goto(`${base}/${root}/box/${id}/`);assert.equal(response.status(),200);
    const widget=page.locator('.staffing-count');
    await widget.locator('strong').first().waitFor();
    assert.ok((await widget.locator('strong').allTextContents()).some(t=>t.startsWith(label)));
    assert.match(await widget.locator('.staffing-note').innerText(),/Budgeted, not actual employees/);
    if(partial)assert.match(await widget.locator('.staffing-note').innerText(),/Partial coverage/);
    const details=widget.locator('details');assert.equal(await details.getAttribute('open'),null);
    await details.locator('summary').click();assert.ok(await details.getAttribute('open')!==null);
    if(root==='cps')assert.match(await details.innerText(),/fund breakdown/);
    assert.ok(await details.locator('a[href^="https:"]').count()>0,'source document link available');
    await details.locator('summary').click();
    for(const width of [1440,375,320]){
      await page.setViewportSize({width,height:1050});
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${root} fits ${width}`);
      if(output&&width===375){await mkdir(output,{recursive:true});await page.screenshot({path:join(output,`staffing-${root}-375.png`),fullPage:true});}
    }
  }
  const response=await page.request.get(`${base}/data/headcounts.json`);assert.ok(response.ok());
  const index=await response.json();
  const direct=Object.keys(index).find(id=>id.endsWith('7020-general-manager-of-airport-operations')&&id.includes('0740-2015-0005'));
  assert.ok(direct);await page.goto(`${base}/city/box/${direct}/`);
  await page.locator('.staffing-count strong').waitFor();
  assert.equal(await page.locator('.staffing-count strong').innerText(),'8 budgeted positions · 2026');
  await page.goto(`${base}/city/box/city.infrastructure-services/`);
  await page.locator('#box h1[title]').waitFor();
  assert.equal((await page.locator('.staffing-count').allTextContents()).join('').trim(),'');
  await page.route('**/data/headcounts.json',route=>route.abort());
  await page.goto(`${base}/city/box/${cases[0][1]}/`);
  await page.getByText('Staffing count could not be loaded. See the source budget for position counts.',{exact:true}).waitFor();
  assert.ok(await page.locator('#box h1').innerText());
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,cases:cases.map(c=>c[2]),checks:'correct units and source values, visible partial coverage, expandable methodology/source links, 320/375/1440 layouts, eight vs cross-fund twelve, unrelated spending omitted, fetch failure graceful'}));
}finally{await browser.close();}
