import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { join } from 'node:path';

// Run against an actual dev server or isolated preview. Override the module/executable
// only when using an existing local Playwright installation rather than npm's default.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:4321';
const output = process.env.SCREENSHOT_DIR || process.env.JCODE_SCRATCH_DIR;
if (output) await mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
const errors = [];
const results = [];
const check = (label, passed) => { assert.ok(passed, label); results.push(label); };
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1300 } });
  page.on('pageerror', error => errors.push(error.message));
  const response = await page.goto(base, { waitUntil: 'networkidle' });
  check('homepage responds successfully', response.status() === 200);
  await page.locator('budget-flock.is-ready').waitFor();
  const flock = page.locator('budget-flock');
  const canvas = flock.locator('canvas');
  const image = () => canvas.evaluate(c => c.toDataURL());
  const data = await flock.evaluate(el => JSON.parse(el.dataset.budgets));
  check('three independent data-backed budgets', data.length === 3 && data.map(b => b.root).join(',') === 'city,cps,parks');
  check('City scale retains net vs positive distinction', data[0].scale.includes('net budget') && data[0].adjustments.length > 0);
  check('static fallback contains 240 equally weighted dots', await flock.locator('.static-flock circle').count() === 240);
  await canvas.scrollIntoViewIfNeeded();
  await delay(150);
  const moving = await image(); await delay(180);
  check('real canvas flock changes over time', moving !== await image());
  await flock.locator('.motion-button').click();
  check('pause control changes to resume', (await flock.locator('.motion-button').textContent()).includes('Resume'));
  const paused = await image(); await delay(200);
  check('paused canvas remains unchanged', paused === await image());
  await flock.locator('[data-budget="1"]').click();
  check('Schools tab exposes the correct budget and selected state', (await flock.locator('[data-total]').textContent()).includes('10.25') && await flock.locator('[data-budget="1"]').getAttribute('aria-pressed') === 'true');
  check('Schools full-budget link is correct', await flock.locator('[data-explore]').getAttribute('href') === '/cps');
  const schoolRow = flock.locator('[data-panel="1"] .legend-row').first();
  await schoolRow.focus();
  check('keyboard focus highlights and describes category', (await flock.locator('[data-selection]').textContent()).includes('Schools'));
  await flock.locator('[data-budget="2"]').click();
  check('Parks tab exposes correct amount and period', (await flock.locator('[data-total]').textContent()).includes('637.6') && (await flock.locator('[data-period]').textContent()).includes('2026'));
  await flock.locator('[data-panel="2"] summary').click();
  check('Other categories disclose their linked members', await flock.locator('[data-panel="2"] details').getAttribute('open') !== null && await flock.locator('[data-panel="2"] .other-categories a').count() > 0);
  await flock.locator('[data-budget="0"]').click();
  await flock.locator('.motion-button').click();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.waitForFunction(() => document.querySelector('budget-flock .motion-button')?.disabled);
  check('reduced motion disables continuous animation', await flock.locator('.motion-button').isDisabled());
  const reduced = await image(); await delay(200);
  check('reduced motion is visually static', reduced === await image());
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.waitForFunction(() => !document.querySelector('budget-flock .motion-button')?.disabled);
  await page.evaluate(() => scrollTo({ top: document.body.scrollHeight, behavior: 'instant' }));
  await delay(150);
  const offscreen = await image(); await delay(180);
  check('offscreen canvas stops advancing', offscreen === await image());
  await page.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }));
  await delay(200);
  if (output) await page.screenshot({ path: join(output, 'james-desktop.png') });
  for (const width of [1024, 800, 768, 375, 320]) {
    await page.setViewportSize({ width, height: 1000 });
    await delay(120);
    const dimensions = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, viewport: innerWidth }));
    check(`no horizontal overflow at ${width}px`, dimensions.scroll <= dimensions.viewport);
  }
  await page.setViewportSize({ width: 375, height: 1100 });
  await page.evaluate(() => scrollTo(0, 0));
  if (output) await page.screenshot({ path: join(output, 'james-mobile.png'), fullPage: true });
  await page.goto(`${base}/?box=city#explore`, { waitUntil: 'networkidle' });
  await page.locator('[data-sankey-explorer] [data-main]:not([hidden])').waitFor();
  check('existing deep explorer remains available', await page.locator('[data-sankey-explorer] [data-panel]').textContent() !== '');
  const noJs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1280, height: 900 } });
  const fallback = await noJs.newPage();
  await fallback.goto(base);
  check('no-JS City legend and all budget links remain usable', await fallback.locator('.budget-panel[data-panel="0"]').isVisible() && await fallback.locator('.flock-footer a').count() === 3);
  check('no-JS fallback graph is visible and controls hidden', await fallback.locator('.static-flock').isVisible() && !await fallback.locator('.flock-controls').isVisible());
  await noJs.close();
  check('no client-side exceptions', errors.length === 0);
  console.log(JSON.stringify({ passed: results.length, results, errors, screenshots: output }, null, 2));
} finally {
  await browser.close();
}
