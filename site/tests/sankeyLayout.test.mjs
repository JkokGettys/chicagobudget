import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

// Node 20 in the project cannot import .ts directly. Compile this pure module
// in memory to keep tests independent of Astro and generated build files.
const source = await readFile(new URL('../src/lib/sankeyLayout.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const { layoutFlow } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

const item = (id, amount_cents) => ({ id, amount_cents, name: id });

test('proportional ribbon heights, explicit gaps, and exact cents', () => {
  const input = [item('city.a', 3), item('city.b', 1)];
  const result = layoutFlow(4, input, { width: 100, height: 104, gap: 4 });
  assert.equal(result.denominatorCents, 4);
  assert.equal(result.positiveTotalCents, 4);
  assert.equal(result.sourceHeight, 100);
  assert.equal(result.parentHeight, 100);
  assert.deepEqual(result.rows.map(row => row.height), [75, 25]);
  assert.deepEqual(result.rows.map(row => row.y), [0, 79]);
  assert.deepEqual(result.rows.map(row => row.sourceY), [0, 75]);
  assert.match(result.rows[1].path, /^M 0 75 C 50 75 50 79 100 79 L 100 104 /);
  assert.ok(result.rows[1].path.endsWith(' Z'));
  assert.deepEqual(result.children, input);
  assert.equal(result.explanation, null);
  assert.deepEqual(layoutFlow(4, input, { width: 100, height: 104, gap: 4 }), result);
});

test('subpixel children never receive an undisclosed minimum width', () => {
  const result = layoutFlow(1_000_000, [item('tiny', 1), item('big', 999_999)], { height: 100, gap: 0 });
  assert.equal(result.rows[0].height, 0.0001);
  assert.ok(Math.abs(result.rows[1].height / result.rows[0].height - 999_999) < 1e-6);
});

test('more than 20 positive children aggregate without hiding any child or deep ID', () => {
  const input = Array.from({ length: 23 }, (_, i) => item(`city.revenue.2026.source.deep.${i}`, i + 1));
  const result = layoutFlow(276, input, { maxVisualChildren: 12, gap: 0 });
  assert.equal(result.rows.length, 12);
  assert.deepEqual(result.rows.slice(0, 11).map(row => row.id), input.slice(0, 11).map(child => child.id));
  const more = result.rows.at(-1);
  assert.equal(more.isOverflow, true);
  assert.equal(more.children.length, 12);
  assert.equal(more.amount_cents, 210);
  assert.deepEqual(more.children.map(child => child.id), input.slice(11).map(child => child.id));
  assert.equal(result.rows.reduce((sum, row) => sum + row.amount_cents, 0), 276);
  assert.deepEqual(result.children, input);
  assert.deepEqual(input.map(child => child.amount_cents), Array.from({ length: 23 }, (_, i) => i + 1));
});

test('negative adjustments explain gross denominator and do not flow as positive area', () => {
  const result = layoutFlow(80, [item('plus', 100), item('less', -20), item('zero', 0)], { height: 100, gap: 0 });
  assert.equal(result.positiveTotalCents, 100);
  assert.equal(result.negativeTotalCents, -20);
  assert.equal(result.positiveTotalCents + result.negativeTotalCents, result.parentAmountCents);
  assert.equal(result.denominatorCents, 100);
  assert.equal(result.rows.length, 1);
  assert.equal(result.rows[0].height, 100);
  assert.equal(result.parentHeight, 80);
  assert.deepEqual(result.negativeChildren.map(child => child.id), ['less']);
  assert.deepEqual(result.zeroChildren.map(child => child.id), ['zero']);
  assert.match(result.explanation, /gross positives.*negative adjustments \(-20 cents\).*never drawn as area/);
});

test('unallocated parent, zero-only and empty cases do not invent ribbons', () => {
  const partial = layoutFlow(100, [item('some', 40)], { height: 100 });
  assert.equal(partial.rows[0].height, 40);
  assert.equal(partial.parentHeight, 100);
  assert.match(partial.explanation, /remainder has no ribbon/);
  const zero = layoutFlow(0, [item('zero', 0)]);
  assert.deepEqual(zero.rows, []);
  assert.equal(zero.sourceHeight, 0);
  assert.equal(zero.parentHeight, 0);
  assert.deepEqual(zero.zeroChildren.map(child => child.id), ['zero']);
  assert.deepEqual(layoutFlow(12, []).rows, []);
});

test('one-row cap and synthetic id collision retain drillable grouped children', () => {
  const input = [item('__more__', 1), item('b', 2), item('c', 3)];
  const result = layoutFlow(6, input, { maxVisualChildren: 1 });
  assert.equal(result.rows.length, 1);
  assert.equal(result.rows[0].id, '__more___');
  assert.deepEqual(result.rows[0].children, input);
  assert.equal(result.rows[0].amount_cents, 6);
});

test('invalid cents and geometry fail rather than silently corrupting the scale', () => {
  assert.throws(() => layoutFlow(1.5, []), RangeError);
  assert.throws(() => layoutFlow(1, [item('a', NaN)]), RangeError);
  assert.throws(() => layoutFlow(1, [item('a', 2 ** 53)]), RangeError);
  assert.throws(() => layoutFlow(1, [item('a', 1)], { height: 0 }), RangeError);
  assert.throws(() => layoutFlow(2, [item('a', 1), item('b', 1)], { height: 1, gap: 2 }), RangeError);
});
