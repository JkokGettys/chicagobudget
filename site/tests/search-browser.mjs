import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
const base = process.env.SEARCH_BASE_URL || 'http://localhost:4321';
try {
  const page = await browser.newPage();
  page.setDefaultTimeout(15000);
  let blocked = true;
  await page.route('**/data/search/**', route => blocked ? route.abort() : route.continue());
  await page.goto(`${base}/find?q=police`);
  await page.locator('#status').getByText('Search unavailable. Please retry.').waitFor();
  assert.equal(await page.locator('#results li').count(), 0);
  blocked = false;
  await page.getByRole('button', { name: 'Retry search' }).click();
  await page.locator('#results li').first().waitFor();
  assert.match(await page.locator('#status').textContent(), /results?\.?/);
  assert.equal(await page.locator('#retry').isVisible(), false);
  assert.match(await page.locator('#results a[href*="/box/"]').first().getAttribute('href'), /\/$/);

  await page.goto(`${base}/find?q=police`);
  let partial = true;
  await page.route('**/data/search/city.json', route => partial ? route.abort() : route.continue());
  await page.reload();
  await page.locator('#status').getByText(/Results incomplete/).waitFor();
  assert.ok(await page.locator('#results li').count() > 0);
  partial = false;
  await page.getByRole('button', { name: 'Retry search' }).click();
  await page.locator('#status').getByText(/^\d+ results?/).waitFor();
  await page.unroute('**/data/search/city.json');
  await page.locator('#query').fill('zzzz-unmatchable-987654');
  await page.locator('#status').getByText('No matching boxes. Try another name or department.').waitFor();
  for (const width of [320, 360, 390]) {
    await page.setViewportSize({ width, height: 800 });
    await page.locator('#government').selectOption('city');
    assert.equal(await page.locator('#government').inputValue(), 'city');
    const bounds = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, viewport: innerWidth, right: document.querySelector('#government').getBoundingClientRect().right }));
    assert.ok(bounds.scroll <= bounds.viewport && bounds.right <= bounds.viewport, `overflow at ${width}: ${JSON.stringify(bounds)}`);
  }
  console.log('Search unavailable, retry, partial recovery, zero matches, and 320/360/390px filter passed');
} finally {
  await browser.close();
}
