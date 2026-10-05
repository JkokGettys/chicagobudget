import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {buildStaffingIndex, type StaffingIndex, type StaffingNode} from './headcount';
let cached: StaffingIndex | undefined;
/** One build-time pass across canonical node records. Never aggregate boundary stubs. */
export function staffingIndex(): StaffingIndex {
  if (cached) return cached;
  const base = join(process.cwd(), 'public/data');
  const read = (file: string) => JSON.parse(readFileSync(join(base, file), 'utf8'));
  const manifest = read('manifest.json');
  const nodes: StaffingNode[] = [];
  for (const file of new Set<string>(Object.values(manifest.chunks))) {
    nodes.push(...read(`chunks/${file.replace(/^chunks\//, '')}`).nodes);
  }
  cached = buildStaffingIndex(nodes, read('sources.json'));
  return cached;
}
