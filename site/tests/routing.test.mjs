import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('Cloudflare box rewrites preserve paths by targeting the canonical shell directory', () => {
  const rules = readFileSync(new URL('../public/_redirects', import.meta.url), 'utf8')
    .split('\n').map(line => line.trim()).filter(line => line && !line.startsWith('#'));
  for (const government of ['city', 'cps', 'parks']) {
    assert.ok(rules.includes(`/${government}/box/* /box-shell/ 200`),
      `${government} needs an internal rewrite to /box-shell/; omitting its slash redirects away the box ID`);
  }
  assert.ok(!rules.some(rule => /\s\/box-shell\s/.test(rule)));
});
