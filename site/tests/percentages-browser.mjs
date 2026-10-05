import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:4321';
const browser = await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
const output = process.env.SCREENSHOT_DIR || process.env.JCODE_SCRATCH_DIR;
try {
  const page = await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`${base}/city/box/city.infrastructure-services/`);
  await page.locator('#box .budget-share').first().waitFor();
  const shares=await page.locator('#box .tiles .budget-share').allTextContents();
  assert.deepEqual(shares,['39.9%','36.1%','16.5%','7.6%']);
  assert.match(await page.locator('#box .share-context').innerText(),/Streets, water, trash and airports/);
  assert.equal(await page.getByText('In the budget',{exact:true}).count(),0);
  assert.equal(await page.getByRole('columnheader',{name:'How we know',exact:true}).count(),0);
  assert.deepEqual(await page.locator('#inside tbody td:last-child').allTextContents(),shares);
  for(const width of [1440,768,375,320]){
    await page.setViewportSize({width,height:1050});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`no overflow at ${width}`);
    for(const tile of await page.locator('#box .tile').all()) assert.ok(await tile.evaluate(el=>el.scrollWidth<=el.clientWidth+1),`card fits at ${width}`);
    if(output && [1440,375].includes(width)){await mkdir(output,{recursive:true});await page.screenshot({path:join(output,`budget-shares-${width}.png`),fullPage:true});}
  }
  await page.locator('#box .tile').first().click();
  await page.waitForFunction(()=>document.querySelector('#box h1')?.getAttribute('title')==='Chicago Department of Transportation');
  const parent=Number((await page.locator('#box header .amount').innerText()).replace(/[$,]/g,''));
  for(const row of await page.locator('#inside tbody tr').all()){
    const amount=Number((await row.locator('td').first().innerText()).replace(/[$,]/g,''));
    const ratio=amount/parent*100;
    const expected=ratio!==0&&Math.abs(ratio)<.1?`${ratio<0?'-':''}<0.1%`:`${ratio.toFixed(1)}%`;
    assert.equal(await row.locator('td').last().innerText(),expected);
  }
  for(const root of ['city','cps','parks']){
    await page.goto(`${base}/${root}/`);
    assert.equal(await page.getByRole('columnheader',{name:'How we know',exact:true}).count(),0);
    assert.equal(await page.locator('main .badge[data-basis="budget"]').count(),0);
    assert.ok(await page.getByRole('columnheader',{name:'% of this budget',exact:true}).count());
  }
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,shares,viewports:[1440,768,375,320],checks:'card percentages, table parity, parent denominator after drilldown, removed default labels, static roots, no overflow/client exceptions'}));
}finally{await browser.close();}
