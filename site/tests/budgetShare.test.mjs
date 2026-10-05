import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';
const source = await readFile(new URL('../src/lib/budgetShare.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { budgetShare } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

test('infrastructure cards show shares of their actual containing budget', () => {
  const parent = 460957064000;
  assert.deepEqual([183747280300,166387852900,75852854700,34969076100].map(n => budgetShare(n,parent)), ['39.9%','36.1%','16.5%','7.6%']);
});
test('percentages preserve negative adjustments and values above 100 rather than using positive totals', () => {
  assert.equal(budgetShare(120,100),'120.0%');
  assert.equal(budgetShare(-20,100),'-20.0%');
  assert.equal(budgetShare(0,100),'0.0%');
});
test('tiny nonzero shares are not silently rounded to zero', () => {
  assert.equal(budgetShare(1,10000),'<0.1%');
  assert.equal(budgetShare(-1,10000),'-<0.1%');
});
test('undefined or nonpositive denominators never invent percentages', () => {
  for(const parent of [0,-1,NaN,Infinity]) assert.equal(budgetShare(10,parent),null);
  for(const value of [NaN,Infinity,-Infinity]) assert.equal(budgetShare(value,100),null);
});
