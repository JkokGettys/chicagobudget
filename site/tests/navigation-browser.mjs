import assert from 'node:assert/strict';

// Run against an actual preview, including its redirects, not a filesystem server.
// PREVIEW_URL=https://<deployment>.chicagobudget.pages.dev node tests/navigation-browser.mjs
// Match motion-browser.mjs overrides for an existing Playwright/Chromium install.
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:4321';
const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}) });
const results = [];
const errors = [];
const coverage = { categories: {}, adjustments: {}, otherMembers: {}, drilldowns: {}, shellRoutes: [], nonPrerenderedRoutes: [] };
const check = (label, passed) => { assert.ok(passed, label); results.push(label); };
const normalize = value => value.replace(/\s+/g, ' ').trim();
const path = url => decodeURIComponent(new URL(url, base).pathname).replace(/\/$/, '') || '/';
const selector = href => `a[href=${JSON.stringify(href)}]`;

try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, reducedMotion: 'reduce' });
  page.setDefaultTimeout(15000);
  page.on('pageerror', error => errors.push({ url: page.url(), message: error.message }));
  const home = async () => {
    const response = await page.goto(base, { waitUntil: 'domcontentloaded' });
    check('homepage responds successfully', response?.status() === 200);
    await page.locator('budget-flock.is-ready').waitFor();
  };
  // Click the real rendered anchor and wait for its actual destination, including
  // canonical redirects. Do not navigate directly to an expected category URL.
  const follow = async link => {
    const href = await link.getAttribute('href');
    assert.ok(href, 'navigation anchor has an href');
    const destination = new URL(href, page.url());
    const previous = page.url();
    await link.click();
    if (previous !== destination.href) await page.waitForURL(url => url.href !== previous, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('domcontentloaded');
    check(`URL retains ${destination.pathname}`, path(page.url()) === path(destination.href));
    check(`navigation remains on preview origin for ${href}`, new URL(page.url()).origin === new URL(base).origin);
    if (destination.hash) check(`navigation retains ${destination.hash}`, new URL(page.url()).hash === destination.hash);
    return href;
  };
  const verifyBox = async record => {
    await page.waitForFunction(() => {
      const heading = document.querySelector('main h1');
      return heading && !heading.textContent.includes('Opening this box');
    });
    const heading = normalize(await page.locator('main h1').innerText());
    check(`${record.href}: not an error page`, !/Box not found|Could not open this box|404/i.test(heading));
    check(`${record.href}: correct heading (${record.name})`, heading === normalize(record.name));
    // Static pages have a compact headline plus an exact strong value. The
    // dynamic shell uses the exact amount as its headline. Never match a child.
    const amounts = await page.locator('main header .amount, main header p strong').allTextContents();
    check(`${record.href}: exact amount ${record.exact}`, amounts.some(amount => normalize(amount) === normalize(record.exact)));
    check(`${record.href}: correct government/id path`, path(page.url()) === path(record.href));
    if (await page.locator('main #box').count()) coverage.shellRoutes.push(path(page.url()));
  };
  await home();
  const budgets = await page.locator('budget-flock').evaluate(el => JSON.parse(el.dataset.budgets));
  assert.deepEqual(budgets.map(b => b.root), ['city', 'cps', 'parks'], 'dataset exposes all three governments');
  // Validate the schema before deriving coverage, so a missing/empty collection
  // cannot silently turn this exhaustive check into a passing no-op.
  for (const budget of budgets) {
    assert.ok(budget.title && budget.exact && budget.href === `/${budget.root}`);
    assert.ok(Array.isArray(budget.rows) && budget.rows.length > 0);
    assert.ok(Array.isArray(budget.adjustments));
    const members = budget.rows.flatMap(row => {
      assert.ok(row.label && row.exact && Number.isFinite(row.amount));
      assert.ok(Array.isArray(row.members) && row.members.length > 0);
      return row.members;
    });
    for (const member of [...members, ...budget.adjustments]) {
      assert.ok(typeof member.name === 'string' && member.name.length > 0);
      assert.match(member.exact, /^-?\$[\d,]+\.\d{2}$/);
      assert.ok(member.href.startsWith(`/${budget.root}/box/`), `category has government/box/id URL: ${member.href}`);
    }
    assert.equal(new Set(members.map(member => member.href)).size, members.length, 'categories are unique');
    coverage.categories[budget.root] = 0;
    coverage.adjustments[budget.root] = 0;
    coverage.otherMembers[budget.root] = 0;
  }
  console.log(JSON.stringify({ preview: base, schema: budgets.map(b => ({ root: b.root, categories: b.rows.flatMap(r => r.members).length, otherMembers: b.rows.filter(r => r.members.length > 1).flatMap(r => r.members).length, adjustments: b.adjustments.length })) }, null, 2));

  for (const [index, budget] of budgets.entries()) {
    const visit = async (record, other = false) => {
      await home();
      const flock = page.locator('budget-flock');
      await flock.locator(`[data-budget="${index}"]`).click();
      const panel = flock.locator(`[data-panel="${index}"]`);
      if (other) {
        const details = panel.locator('details').filter({ has: page.locator(selector(record.href)) });
        await details.locator('summary').click();
        check(`${record.name}: Other disclosure opens`, await details.getAttribute('open') !== null);
      }
      const link = panel.locator(selector(record.href));
      assert.equal(await link.count(), 1, `exactly one homepage link for ${record.name}`);
      await follow(link);
      await verifyBox(record);
    };
    for (const row of budget.rows) {
      for (const member of row.members) {
        await visit(member, row.members.length > 1);
        coverage.categories[budget.root]++;
        if (row.members.length > 1) coverage.otherMembers[budget.root]++;
      }
    }
    for (const adjustment of budget.adjustments) {
      await visit(adjustment);
      coverage.adjustments[budget.root]++;
    }

    // Find a representative branch through actual rendered child links. Going
    // several levels down ensures the dynamic, non-prerendered shell is tested.
    coverage.drilldowns[budget.root] = 0;
    for (const member of budget.rows.flatMap(row => row.members)) {
      const row = budget.rows.find(candidate => candidate.members.includes(member));
      await visit(member, row.members.length > 1);
      let parent = member;
      for (let depth = 0; depth < 8; depth++) {
        const childRow = page.locator('#inside table tbody tr').filter({ has: page.locator('th a') }).first();
        if (!await childRow.count()) break;
        const child = {
          href: await childRow.locator('th a').getAttribute('href'),
          name: normalize(await childRow.locator('th a').innerText()),
          exact: normalize(await childRow.locator('td').first().innerText()),
        };
        await follow(childRow.locator('th a'));
        await verifyBox(child);
        coverage.drilldowns[budget.root]++;
        const shell = await page.locator('main #box').count();
        await follow(page.getByRole('link', { name: '↑ Up one level', exact: true }));
        await verifyBox(parent);
        await follow(page.locator('#inside table tbody th').locator(selector(child.href)));
        await verifyBox(child);
        await follow(page.getByRole('navigation', { name: 'Breadcrumb', exact: true }).locator(selector(parent.href)));
        await verifyBox(parent);
        if (shell) break;
        await follow(page.locator('#inside table tbody th').locator(selector(child.href)));
        await verifyBox(child);
        parent = child;
      }
      if (coverage.drilldowns[budget.root]) break;
    }
    check(`${budget.root}: child, up, and breadcrumb navigation exercised`, coverage.drilldowns[budget.root] > 0);
  }
  // Discover a deep target from the deployed data, using the actual prerender
  // rule (depth <= 4 OR at least $1m). A #box shell alone is not proof: the
  // preview's wildcard rewrite can serve shallow, prerendered routes too.
  const manifestResponse = await page.request.get(new URL('/data/manifest.json', base).href);
  assert.ok(manifestResponse.ok(), 'deployed manifest is available');
  const manifest = await manifestResponse.json();
  let deepTarget;
  for (const file of new Set(Object.values(manifest.chunks))) {
    const response = await page.request.get(new URL(`/data/${file}`, base).href);
    assert.ok(response.ok(), `deployed chunk ${file} is available`);
    const chunk = await response.json();
    deepTarget = chunk.nodes.find(node => node.depth > 4 && Math.abs(node.amount_cents) < 100_000_000 && budgets.some(b => b.root === node.root && b.rows.some(row => row.members.some(member => node.id.startsWith(`${decodeURIComponent(member.href.split('/box/')[1])}.`)))));
    if (deepTarget) break;
  }
  assert.ok(deepTarget, 'deployed dataset contains a genuinely non-prerendered deep box');
  const budgetIndex = budgets.findIndex(b => b.root === deepTarget.root);
  const deepBudget = budgets[budgetIndex];
  const deepRow = deepBudget.rows.find(row => row.members.some(member => deepTarget.id.startsWith(`${decodeURIComponent(member.href.split('/box/')[1])}.`)));
  const category = deepRow.members.find(member => deepTarget.id.startsWith(`${decodeURIComponent(member.href.split('/box/')[1])}.`));
  await home();
  await page.locator(`budget-flock [data-budget="${budgetIndex}"]`).click();
  const deepPanel = page.locator(`budget-flock [data-panel="${budgetIndex}"]`);
  if (deepRow.members.length > 1) await deepPanel.locator('details').filter({ has: page.locator(selector(category.href)) }).locator('summary').click();
  await follow(deepPanel.locator(selector(category.href)));
  await verifyBox(category);
  for (let depth = 0; depth < 30; depth++) {
    const currentId = decodeURIComponent(new URL(page.url()).pathname.split('/box/')[1]).replace(/\/$/, '');
    if (currentId === deepTarget.id) break;
    const links = await page.locator('#inside table tbody th a').evaluateAll(anchors => anchors.map(a => ({ href: a.getAttribute('href'), name: a.textContent.trim(), exact: a.closest('tr').querySelector('td').textContent.trim() })));
    const child = links.find(link => {
      const id = decodeURIComponent(link.href.split('/box/')[1] || '');
      return id && (id === deepTarget.id || deepTarget.id.startsWith(`${id}.`));
    });
    assert.ok(child, `real child link advances toward deep target ${deepTarget.id}`);
    await follow(page.locator('#inside table tbody th').locator(selector(child.href)));
    await verifyBox(child);
  }
  const deepHref = `/${deepTarget.root}/box/${encodeURIComponent(deepTarget.id)}`;
  await verifyBox({ href: deepHref, name: deepTarget.name, exact: new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(deepTarget.amount_cents / 100) });
  check('non-prerendered deep box renders through the dynamic shell', await page.locator('main #box').count() === 1);
  coverage.nonPrerenderedRoutes.push({ href: deepHref, depth: deepTarget.depth, amount_cents: deepTarget.amount_cents });

  const navTargets = [
    ...budgets.map(b => ({ href: b.href, heading: b.title, budget: b })),
    { href: '/find', heading: 'Find a box' },
    { href: '/about', heading: 'About this budget explorer' },
    { href: '/#explore', heading: 'A city in motion.A budget you can see.' },
  ];
  for (const target of navTargets) {
    await follow(page.getByRole('navigation', { name: 'Main navigation', exact: true }).locator(selector(target.href)));
    if (target.budget) await verifyBox({ ...target.budget, name: target.budget.title });
    else if (target.href === '/#explore') {
      await page.locator('budget-flock.is-ready').waitFor();
      check('Explore navigation reaches homepage explorer', await page.locator('#explore').isVisible());
      check('Explore navigation reaches correct homepage heading', (await page.locator('main h1').textContent()).replace(/\s/g, '') === target.heading.replace(/\s/g, ''));
    } else check(`${target.href}: correct primary page`, normalize(await page.locator('main h1').innerText()) === target.heading);
  }
  await follow(page.getByRole('link', { name: 'Chicago Budget home', exact: true }));
  await page.locator('budget-flock.is-ready').waitFor();
  check('no client-side exceptions', errors.length === 0);
  coverage.shellRoutes = [...new Set(coverage.shellRoutes)];
  console.log(JSON.stringify({ preview: base, passed: results.length, coverage, errors, results }, null, 2));
} catch (error) {
  console.error(JSON.stringify({ preview: base, passed: results.length, coverage, errors, failure: error.message, lastChecks: results.slice(-8) }, null, 2));
  throw error;
} finally {
  await browser.close();
}
