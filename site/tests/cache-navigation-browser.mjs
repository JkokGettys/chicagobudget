import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { once } from 'node:events';

// Synthetic HTTP-cache regression, NOT a deployed-site/component integration test.
// Run from site: node tests/cache-navigation-browser.mjs
// Uses Playwright, or PLAYWRIGHT_MODULE / CHROMIUM_PATH overrides.
// No routing, service workers, cache disabling, build, or deployment is involved.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const original = '/city/box/city.infrastructure-services';
const canonical = `${original}/`;
const heading = 'Streets & Infrastructure Services';
const scenarios = [
  { name: 'explicitly-fresh-308', headers: { 'Cache-Control': 'public, max-age=3600' }, stale: true },
  // Observe rather than assume Chromium heuristically caches a 308 without any
  // freshness headers. Node adds Date, as ordinary HTTP servers do.
  { name: 'default-308-no-cache-headers', headers: {} },
  { name: 'default-308-with-last-modified', headers: { 'Last-Modified': new Date(Date.now() - 86400000).toUTCString() } },
  { name: 'initial-no-cache-308', headers: { 'Cache-Control': 'no-cache' }, stale: false },
];
const results = [];
const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
try {
  for (const scenario of scenarios) {
    let corrected = false;
    const requests = [];
    const server = createServer((req, res) => {
      const pathname = new URL(req.url, 'http://localhost').pathname;
      requests.push({ path: pathname, corrected, cacheControl: req.headers['cache-control'] || null });
      if (pathname === original) {
        // A server-side no-cache correction cannot invalidate a response that a
        // browser continues serving locally without contacting this handler.
        res.writeHead(308, corrected
          ? { Location: canonical, 'Cache-Control': 'no-cache' }
          : { Location: '/box-shell/', ...scenario.headers });
        res.end();
      } else {
        res.setHeader('Cache-Control', 'no-store');
        res.setHeader('Content-Type', 'text/html; charset=utf-8');
        if (pathname === '/') {
          res.end(`<!doctype html><title>Navigation fixture</title><a id="original" href="${original}">Original Streets link</a><a id="canonical" href="${canonical}">Canonical Streets link</a>`);
        } else if (pathname === canonical) {
          res.end(`<!doctype html><title>Streets</title><main><h1>${heading}</h1></main>`);
        } else if (pathname === '/box-shell/') {
          res.end('<!doctype html><title>Broken shell</title><main><h1>Box not found</h1></main>');
        } else {
          res.writeHead(404);
          res.end('Not found');
        }
      }
    });
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    const base = `http://127.0.0.1:${server.address().port}`;
    const context = await browser.newContext({ serviceWorkers: 'block' });
    try {
      // Keep this page and context across poisoning, correction, and recovery.
      const page = await context.newPage();
      page.setDefaultTimeout(10000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      const follow = async (id, destination) => {
        await page.goto(base, { waitUntil: 'load' });
        await Promise.all([
          page.waitForURL(`${base}${destination}`, { waitUntil: 'load' }),
          page.locator(`#${id}`).click(),
        ]);
      };
      const originalHits = () => requests.filter(request => request.path === original).length;
      await follow('original', '/box-shell/');
      assert.equal(await page.locator('h1').textContent(), 'Box not found');
      assert.equal(originalHits(), 1, 'initial redirect came from the real server');
      corrected = true;
      await page.goto(base, { waitUntil: 'load' });
      await Promise.all([
        page.waitForURL(url => url.pathname === canonical || url.pathname === '/box-shell/', { waitUntil: 'load' }),
        page.locator('#original').click(),
      ]);
      const stale = new URL(page.url()).pathname === '/box-shell/';
      const hitsAfterCorrection = originalHits();
      assert.equal(hitsAfterCorrection, stale ? 1 : 2, 'request log distinguishes a cached redirect from a fresh server response');
      assert.equal(await page.locator('h1').textContent(), stale ? 'Box not found' : heading);
      if (scenario.stale !== undefined) assert.equal(stale, scenario.stale, scenario.name);
      if (stale) {
        await page.reload({ waitUntil: 'load' });
        assert.equal(new URL(page.url()).pathname, '/box-shell/', 'reloading broken destination does not recover original URL');
        assert.equal(originalHits(), hitsAfterCorrection, 'destination reload never requests original cache key');
        await follow('original', '/box-shell/');
        assert.equal(originalHits(), hitsAfterCorrection, 'original remains cached even after destination reload');
      }

      await follow('canonical', canonical);
      assert.equal(await page.locator('#canonical').count(), 0, 'navigation left fixture homepage');
      assert.equal(await page.locator('h1').textContent(), heading);
      assert.equal(originalHits(), hitsAfterCorrection, 'trailing slash link bypasses poisoned cache key entirely');
      assert.ok(requests.some(request => request.path === canonical && request.corrected), 'canonical content came from corrected server');

      // Reloading the *redirect destination* cannot refresh the original cache
      // key. An explicit no-cache request to the original URL can recover it.
      await page.setExtraHTTPHeaders({ 'Cache-Control': 'no-cache' });
      await page.goto(`${base}${original}`, { waitUntil: 'load' });
      assert.equal(new URL(page.url()).pathname, canonical, 'request-side no-cache recovers original URL');
      assert.equal(originalHits(), hitsAfterCorrection + 1, 'no-cache forces an original-URL network request');
      assert.equal(requests.filter(request => request.path === original).at(-1).cacheControl, 'no-cache');
      assert.equal(await page.locator('h1').textContent(), heading);
      await page.setExtraHTTPHeaders({});
      await follow('original', canonical);
      assert.equal(await page.locator('h1').textContent(), heading, 'original link remains recovered after request override is removed');
      assert.deepEqual(errors, []);
      results.push({ scenario: scenario.name, initialHeaders: scenario.headers, retainedBrokenRedirectAfterCorrection: stale, originalRequestsAfterCorrection: hitsAfterCorrection, trailingSlashBypass: 'passed', requestNoCacheRecovery: 'passed', requests });
    } finally {
      await context.close();
      const closed = new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
      server.closeAllConnections();
      await closed;
    }
  }
  console.log(JSON.stringify({ fixture: 'synthetic local HTTP server, not deployed application', browser: browser.version(), results }, null, 2));
} finally {
  await browser.close();
}
