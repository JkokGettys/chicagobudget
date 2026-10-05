import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/lib/budgetFlock.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const { allocateParticles, stepBoids } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

test('largest remainder sums exactly, preserves proportions and resolves ties stably', () => {
  assert.deepEqual(allocateParticles([3, 1], 240), [180, 60]);
  assert.deepEqual(allocateParticles([1, 1, 1], 10), [4, 3, 3]);
  assert.deepEqual(allocateParticles([999999, 1], 240), [240, 0]);
  const weights = [460957064000, 326655536000, 284322141400, 184697840500, 110117873300, 100873418100, 85220034000, 143110243200];
  const result = allocateParticles(weights);
  assert.equal(result.reduce((a, b) => a + b, 0), 240);
  result.forEach((n, i) => assert.ok(Math.abs(n - weights[i] / weights.reduce((a, b) => a + b, 0) * 240) < 1));
});

test('zeros, negative adjustments, empty and nonfinite inputs never receive dots', () => {
  assert.deepEqual(allocateParticles([0, -10, 3, NaN, Infinity], 12), [0, 0, 12, 0, 0]);
  assert.deepEqual(allocateParticles([0, -2]), [0, 0]);
  assert.deepEqual(allocateParticles([]), []);
  assert.deepEqual(allocateParticles([10, 20], 0), [0, 0]);
  assert.deepEqual(allocateParticles([10, 20], -4), [0, 0]);
  assert.deepEqual(allocateParticles([10, 20], NaN), [0, 0]);
  assert.deepEqual(allocateParticles([1e308, 1e308], 10), [5, 5]);
});

test('allocation is deterministic, nonmutating and within one dot for many distributions', () => {
  for (let n = 1; n < 50; n++) {
    const weights = Array.from({ length: n }, (_, i) => (i * 127 + n * 19) % 997);
    const original = [...weights], result = allocateParticles(weights, 241);
    assert.deepEqual(weights, original);
    assert.deepEqual(result, allocateParticles(weights, 241));
    assert.equal(result.reduce((a, b) => a + b, 0), 241);
    result.forEach((v, i) => assert.ok(Math.abs(v - weights[i] / weights.reduce((a, b) => a + b) * 241) < 1));
  }
});

test('flock stays finite and bounded with stable group identities over 600 steps', () => {
  let boids = Array.from({ length: 80 }, (_, i) => ({ x: i * 9, y: i * 5, vx: Math.cos(i), vy: Math.sin(i), group: i % 3 }));
  const original = structuredClone(boids);
  const targets = [{ x: 150, y: 120 }, { x: 550, y: 150 }, { x: 350, y: 330 }];
  assert.deepEqual(stepBoids(boids, targets, 720, 440), stepBoids(boids, targets, 720, 440));
  assert.deepEqual(boids, original);
  for (let frame = 0; frame < 600; frame++) {
    boids = stepBoids(boids, targets, 720, 440, frame % 30 === 0 ? 100 : 1);
    boids.forEach((b, i) => {
      assert.ok([b.x, b.y, b.vx, b.vy].every(Number.isFinite));
      assert.ok(b.x >= 0 && b.x <= 720 && b.y >= 0 && b.y <= 440);
      assert.ok(Math.hypot(b.vx, b.vy) <= 1.4500001);
      assert.equal(b.group, i % 3);
    });
  }
});

test('separation, alignment, cohesion and category attraction affect motion', () => {
  const b = { x: 50, y: 50, vx: 0, vy: 0, group: 0 };
  assert.ok(stepBoids([b], [{ x: 80, y: 50 }], 100, 100)[0].vx > 0);
  const separated = stepBoids([b, { ...b, x: 51, group: 1 }], [{ x: 50, y: 50 }], 100, 100);
  assert.ok(separated[0].vx < 0);
  const aligned = stepBoids([b, { ...b, x: 80, vx: 1 }], [{ x: 50, y: 50 }], 100, 100);
  assert.ok(aligned[0].vx > 0);
  assert.deepEqual(stepBoids([], [], 0, 0), []);
});

test('invalid coordinates and missing targets recover without nonfinite outputs', () => {
  const result = stepBoids([{ x: Infinity, y: NaN, vx: NaN, vy: Infinity, group: 4 }], [], NaN, -4, NaN);
  assert.ok(Object.values(result[0]).every(Number.isFinite));
  assert.ok(result[0].x >= 0 && result[0].x <= 1 && result[0].y >= 0 && result[0].y <= 1);
});
