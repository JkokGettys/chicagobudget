import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/lib/treemapLayout.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { layoutTreemap } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
const item = (id, amount_cents) => ({ id, amount_cents });
const area = r => r.width * r.height;
const overlap = (a, b) => Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));

test('area ratios follow exact positive cents, not net, without minimum rectangle area', () => {
  const map = layoutTreemap(70, [item('large', 99), item('tiny', 1), item('adjustment', -30), item('zero', 0)], { width: 100, height: 100 });
  assert.equal(map.positiveTotalCents, 100);
  assert.deepEqual(map.negative.map(n => n.id), ['adjustment']);
  assert.deepEqual(map.zero.map(n => n.id), ['zero']);
  assert.deepEqual(map.rectangles.map(area), [9900, 100]);
  assert.ok(Math.abs(layoutTreemap(1_000_000, [item('tiny', 1), item('large', 999_999)], { width: 100, height: 100 }).rectangles[0].width - .0001) < 1e-12);
});

test('deterministic partition covers map and never overlaps sibling regions', () => {
  const inputs = Array.from({ length: 30 }, (_, i) => item(`n${i}`, i + 1));
  const map = layoutTreemap(465, inputs, { width: 1200, height: 680, maxItems: 12 });
  assert.deepEqual(map, layoutTreemap(465, inputs, { width: 1200, height: 680, maxItems: 12 }));
  assert.equal(map.rectangles.length, 12);
  assert.equal(map.rectangles.at(-1).item.amount_cents, 465 - 66);
  assert.ok(Math.abs(map.rectangles.reduce((sum, rect) => sum + area(rect), 0) - 816000) < 1e-6);
  for (let i = 0; i < map.rectangles.length; i++) for (let j = i + 1; j < map.rectangles.length; j++) assert.ok(overlap(map.rectangles[i], map.rectangles[j]) < 1e-8);
});

test('nested children only fill reconciled positive parents', () => {
  const children = [item('exact', 60), item('partial', 40)];
  const nested = n => n.id === 'exact' ? [item('a', 30), item('b', 30)] : [item('c', 20), item('negative', -2)];
  const map = layoutTreemap(100, children, { nested });
  assert.equal(map.rectangles[0].children.length, 2);
  assert.equal(map.rectangles[1].children.length, 0);
  assert.equal(map.rectangles[0].children.reduce((sum, rect) => sum + area(rect), 0), area(map.rectangles[0]));
  assert.equal(area(map.rectangles[0].children[0]) / area(map.rectangles[0]), .5);
});

test('zero-only, empty and invalid values', () => {
  assert.deepEqual(layoutTreemap(0, [item('none', 0)]).rectangles, []);
  assert.deepEqual(layoutTreemap(1, []).rectangles, []);
  assert.throws(() => layoutTreemap(1.5, []), RangeError);
  assert.throws(() => layoutTreemap(1, [item('bad', NaN)]), RangeError);
  assert.throws(() => layoutTreemap(1, [item('bad', 2 ** 53)]), RangeError);
  assert.throws(() => layoutTreemap(1, [item('one', 1)], { width: 0 }), RangeError);
});
