import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';
const source = await readFile(new URL('../src/lib/displayName.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { displayName, nameSearchText } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
const programs = [
  ['DOT - FHWA - IDOT - CTY - Highway Planning and Construction (20.205)', 'Highway planning and construction'],
  ['DOT - FTA - Federal Transit Formula Grants (20.507)', 'Federal transit grants'],
  ['DOT - NHTSA - IDOT - National Priority Safety Programs (20.616)', 'National priority safety'],
  ['DOT - NHTSA - IDOT - State and Community Highway Safety (20.600)', 'Community highway safety'],
];
const construction = program => `Construction of Buildings and Other Structures (${program})`;

test('screenshot construction titles have four distinctive program names, not identical prefixes', () => {
  const labels = programs.map(([program, expected]) => {
    const item = { name: construction(program), short_name: 'Construction of Buildings and Other Structures…' };
    assert.equal(displayName(item), expected);
    return displayName(item);
  });
  assert.equal(new Set(labels).size, 4);
});
test('standalone official program titles use the same aliases', () => {
  for (const [name, expected] of [
    ['Highway Planning and Construction (20.205)', 'Highway planning and construction'],
    ['Federal Transit Formula Grants (20.507)', 'Federal transit grants'],
    ['National Priority Safety Programs (20.616)', 'National priority safety'],
    ['State and Community Highway Safety (20.600)', 'Community highway safety'],
  ]) assert.equal(displayName({ name }), expected);
});
test('unknown programs, grant numbers and spending categories are never stripped', () => {
  for (const name of [
    'Construction of Buildings and Other Structures (Unfamiliar Program (20.999))',
    construction(programs[0][0]).replace('20.205', '20.206'),
    `Equipment (${programs[0][0]})`,
    'A long unfamiliar official title (with important qualifiers)',
    'toString', '',
  ]) assert.equal(displayName({ name }), name);
});
test('existing meaningful short names work, but empty and generated truncated prefixes do not', () => {
  assert.equal(displayName({ name: 'Official name', short_name: 'Useful label' }), 'Useful label');
  for (const short_name of [null, undefined, '', '   ', 'Official…', 'Official...']) {
    assert.equal(displayName({ name: 'Official name', short_name }), 'Official name');
  }
  assert.equal(displayName({ name: 'Chicago Department of Transportation' }), 'Transportation');
});
test('spending categories in the same grant retain meaningful distinctions', () => {
  const program = programs[0][0];
  const names = [construction(program), `Reserve Balance (${program})`, `Fringe Benefits (${program})`, `For Professional and Technical Services and Other Third Party Benefit Agreements (${program})`];
  const labels = names.map(name => displayName({ name }));
  assert.equal(new Set(labels).size, names.length);
  assert.match(labels[1], /Reserve balance$/);
  assert.match(labels[2], /Fringe benefits$/);
});
test('official titles, amounts, IDs, source links and duplicate records are preserved', () => {
  const records = ['first', 'second'].map(id => Object.freeze({ id, name: construction(programs[1][0]), amount_cents: 12345, source: 'https://example.org/source', short_name: null }));
  const before = JSON.stringify(records);
  assert.equal(displayName(records[0]), displayName(records[1]));
  assert.notEqual(records[0].id, records[1].id);
  for (const item of records) {
    const text = nameSearchText(item);
    assert.ok(text.includes(item.name.toLocaleLowerCase()));
    assert.ok(text.includes('20.507'));
    assert.ok(text.includes('federal transit grants'));
  }
  assert.equal(JSON.stringify(records), before);
});
test('every program remains searchable by both official title and visible alias', () => {
  for (const [program, alias] of programs) {
    const item = { name: construction(program) };
    assert.ok(nameSearchText(item).includes(item.name.toLocaleLowerCase()));
    assert.ok(nameSearchText(item).includes(alias.toLocaleLowerCase()));
  }
});
