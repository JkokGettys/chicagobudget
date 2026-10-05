import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:4321';
const local = ['127.0.0.1', 'localhost'].includes(new URL(base).hostname);
const chunk = JSON.parse(await readFile(new URL('../public/data/chunks/fa8d2e9062d498fe.json', import.meta.url), 'utf8'));
const parent = 'city.infrastructure-services.chicago-department-of-transportation.construction.925f-federal-grant-fund';
const cases = [
  ['925f-281s-0540', 'Highway planning and construction'],
  ['925f-281u-0540', 'Federal transit grants'],
  ['925f-280g-0540', 'National priority safety'],
  ['925f-281n-0540', 'Community highway safety'],
].map(([suffix, label]) => ({ record: chunk.nodes.find(n => n.id === `${parent}.${suffix}`), label }));
const href = id => `/city/box/${encodeURIComponent(id)}/`;
const money = cents => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(cents / 100);
const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  // Astro dev does not implement Pages _redirects. Exercise the actual shell
  // response at the requested path, without mocking scripts or budget data.
  if (local) await page.route('**/city/box/**', async route => {
    if (!route.request().isNavigationRequest()) return route.continue();
    const response = await route.fetch({ url: `${base}/box-shell` });
    await route.fulfill({ response });
  });
  await page.goto(`${base}${href(parent)}`);
  await page.locator('#box .tiles .tile').first().waitFor();
  for (const { record, label } of cases) {
    const tile = page.locator(`#box .tile[href="${href(record.id)}"]`);
    assert.equal(await tile.locator('strong').innerText(), label);
    assert.equal(await tile.getAttribute('title'), record.name);
    assert.equal(await tile.locator('.tile-amount').innerText(), money(record.amount_cents));
    const row = page.locator(`#box tbody a[href="${href(record.id)}"]`);
    assert.equal(await row.innerText(), label);
    assert.equal(await row.getAttribute('title'), record.name);
  }
  await page.setViewportSize({ width: 375, height: 900 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  for (const { record, label } of cases) {
    await page.goto(`${base}${href(record.id)}`);
    await page.getByRole('heading', { name: label, exact: true }).waitFor();
    assert.equal(await page.locator('#box h1').getAttribute('title'), record.name);
    await page.getByText('Official budget title', { exact: true }).click();
    assert.equal(await page.locator('#box header details p').innerText(), record.name);
    assert.equal(await page.locator('#box header .amount').innerText(), money(record.amount_cents));
  }
  if (local) await page.unroute('**/city/box/**');
  // Static BoxPage and treemap, rendered by Astro dev without a production build.
  await page.goto(`${base}/city/box/city.infrastructure-services`);
  const department = page.locator('tbody a').filter({ hasText: /^Transportation$/ });
  assert.equal(await department.getAttribute('title'), 'Chicago Department of Transportation');
  assert.ok((await department.getAttribute('href')).endsWith('/'));
  assert.ok(await page.locator('svg a title').filter({ hasText: 'Chicago Department of Transportation' }).count());
  // Dev's trailingSlash: never routes differ from Pages canonical slash rewrites.
  if (local) await page.goto(`${base}${(await department.getAttribute('href')).replace(/\/$/, '')}`);
  else await department.click();
  assert.equal(await page.locator('main h1').innerText(), 'Transportation');
  await page.getByText('Official budget title', { exact: true }).click();
  assert.equal(await page.locator('.box-hero details p').innerText(), 'Chicago Department of Transportation');
  await page.goto(`${base}/?box=${encodeURIComponent(parent)}`);
  await page.locator('.flow-list-link').first().waitFor();
  const filter = page.getByRole('searchbox', { name: /Filter lines inside/ });
  for (const query of ['Federal transit grants', cases[1].record.name]) {
    await filter.fill(query);
    assert.equal(await page.locator('.flow-list-link').count(), 1);
    assert.equal(await page.locator('.flow-list-link .list-name > span').innerText(), 'Federal transit grants');
    assert.equal(await page.locator('.flow-list-link').getAttribute('title'), cases[1].record.name);
  }
  await page.locator('.flow-list-link').click();
  await page.getByRole('heading', { name: 'Federal transit grants', exact: true }).first().waitFor();
  await page.locator('[data-detail] summary').filter({ hasText: 'Official budget title' }).click();
  assert.equal(await page.locator('[data-detail] details p').first().innerText(), cases[1].record.name);
  for (const query of ['Federal transit grants', cases[1].record.name]) {
    await page.goto(`${base}/find?budget=city&q=${encodeURIComponent(query)}`);
    const result = page.locator(`#results a[href="${href(cases[1].record.id)}"]`);
    await result.waitFor();
    assert.equal(await result.innerText(), 'Federal transit grants');
    assert.equal(await result.getAttribute('title'), cases[1].record.name);
  }
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ passed: true, cases: cases.map(c => c.label), checks: 'shell cards/table/heading/details/amounts, mobile overflow, static BoxPage/treemap, explorer filter/details, global search, canonical trailing slash hrefs', localShellRewrite: local }));
} finally { await browser.close(); }
