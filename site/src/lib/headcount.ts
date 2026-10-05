/** Counts describe budgeted capacity, never actual payroll headcount. */
export type StaffingNode = {
  id: string; parent_id?: string | null; root?: string; kind?: string; basis?: string;
  count?: number | null; unit_label?: string | null; period_label?: string | null;
  period?: string | null; source?: number | number[]; extra?: Record<string, unknown>;
  n_children?: number; amount_cents?: number;
};
export type StaffingCount = {value: number; unit: 'positions' | 'FTEs'; period: string; sources: number[]};
export type StaffingSummary = {counts: StaffingCount[]; complete: boolean; aggregate: boolean; cps: boolean};
export type StaffingIndex = Record<string, StaffingSummary>;
type Source = Record<string, unknown>;
const finiteCount = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0;

export function isPersonnelNode(node: StaffingNode): boolean {
  const root = node.root ?? node.id.split('.')[0];
  if (root === 'city') return /(?:^|\.)(?:pay-for-workers|[^.]+-0005)(?:\.|$)/.test(node.id);
  if (root === 'parks') return /\.611005(?:\.|$)/.test(node.id);
  if (root === 'cps') return /\.(?:salaries|a51100|a52100)(?:\.|$)/.test(node.id);
  return false;
}

function directCount(node: StaffingNode, sources: Source[]): StaffingCount | null {
  const root = node.root ?? node.id.split('.')[0];
  let value: unknown = node.count;
  let unit: StaffingCount['unit'];
  if (root === 'city' && ['job_title', 'pay_rate'].includes(node.kind ?? '') && node.unit_label === 'positions' && ['budget','tied'].includes(node.basis ?? '')) unit = 'positions';
  else if (root === 'parks' && node.kind === 'position' && node.unit_label === 'full-time equivalents' && ['budget','tied'].includes(node.basis ?? '')) unit = 'FTEs';
  else if (root === 'cps' && ['job_title','job_title_group'].includes(node.kind ?? '') && ['budget','tied','proxy'].includes(node.basis ?? '')) {
    // The group FTE is a source count, not the number of titles or rows.
    value = node.extra?.fte ?? (node.unit_label === 'positions (FTE)' ? node.count : undefined);
    unit = 'FTEs';
  } else return null;
  const citations = (Array.isArray(node.source) ? node.source : [node.source]).filter((i): i is number => typeof i === 'number' && Number.isInteger(i) && i >= 0 && !!sources[i]);
  if (!finiteCount(value) || !citations.length) return null;
  const sourceText = citations.map(i => JSON.stringify(sources[i])).join(' ');
  // Exported staffing nodes omit period. These source documents explicitly identify FY2026.
  const period = node.period_label || node.period || (/2026/.test(sourceText) ? (root === 'cps' ? 'FY2026 (Jul 2025 to Jun 2026)' : '2026') : 'Period not stated');
  return {value, unit, period, sources: citations};
}

/** Input must contain full exported nodes, not boundary stubs. Duplicate IDs are counted once.
 * Stop at a source count before descending, so title totals and pay-rate rows never both count.
 * Uncovered leaves (including hour-based pay and suppressed counts) make a rollup partial.
 */
export function buildStaffingIndex(input: StaffingNode[], sources: Source[]): StaffingIndex {
  const nodes = new Map(input.map(node => [node.id, node]));
  const children = new Map<string, StaffingNode[]>();
  for (const node of nodes.values()) if (node.parent_id) children.set(node.parent_id, [...(children.get(node.parent_id) ?? []), node]);
  const memo = new Map<string, StaffingSummary>();
  const visiting = new Set<string>();
  function summarize(node: StaffingNode): StaffingSummary {
    const cached = memo.get(node.id); if (cached) return cached;
    const cps = (node.root ?? node.id.split('.')[0]) === 'cps';
    if (node.kind === 'rounding' || node.kind === 'adjustment' || node.basis === 'adjustment') {
      const result = {counts: [], complete: true, aggregate: true, cps}; memo.set(node.id, result); return result;
    }
    const own = directCount(node, sources);
    if (own) {const result = {counts: [own], complete: true, aggregate: false, cps}; memo.set(node.id, result); return result;}
    if (visiting.has(node.id)) return {counts: [], complete: false, aggregate: true, cps};
    visiting.add(node.id);
    const descendants = children.get(node.id) ?? [];
    const ignored = node.kind === 'rounding' || node.kind === 'adjustment' || node.basis === 'adjustment';
    let complete = ignored || (descendants.length > 0 && descendants.length >= (node.n_children ?? 0));
    const grouped = new Map<string, StaffingCount>();
    for (const child of descendants) {
      const summary = summarize(child); complete = complete && summary.complete;
      for (const count of summary.counts) {
        const key = JSON.stringify([count.unit, count.period]);
        const previous = grouped.get(key);
        grouped.set(key, { ...count, value: (previous?.value ?? 0) + count.value, sources: [...new Set([...(previous?.sources ?? []), ...count.sources])] });
      }
    }
    const result = {counts: [...grouped.values()].map(count => ({...count, value: Math.round(count.value * 1e6) / 1e6})), complete, aggregate: true, cps};
    visiting.delete(node.id); memo.set(node.id, result); return result;
  }
  return Object.fromEntries([...nodes.values()].filter(isPersonnelNode).map(node => [node.id, summarize(node)]));
}

export function staffingText(summary: StaffingSummary): {lines: string[]; caption: string; note: string} {
  const lines = summary.counts.map(count => `${count.value.toLocaleString('en-US', {maximumFractionDigits: 6})} budgeted ${count.unit}${summary.aggregate ? ' listed' : ''} · ${count.period}`);
  if (!lines.length) return {lines: ['Staffing count not available for this box'], caption: 'Unknown, not zero employees.', note: 'The available budget data does not state a position or FTE count here. This does not mean zero employees.'};
  let note = 'Budgeted capacity, not the number of actual employees on payroll.';
  if (summary.counts.some(count => count.unit === 'FTEs')) note += ' FTEs are full-time equivalents, not individual people.';
  if (!summary.complete) note += ' Partial coverage: includes only listed position/FTE counts; hours and uncounted pay lines are excluded.';
  if (summary.cps) note += ' CPS position data has no fund breakdown; it may not match the exact salary dollars in this box.';
  return {lines, caption: `${summary.complete ? '' : 'Partial coverage · '}Budgeted, not actual employees`, note};
}

/** Source IDs are retained from the count frontier, then deduplicated by document URL. */
export function staffingSources(summary: StaffingSummary, sources: Source[], resolve: (source: Source) => string | undefined): {label: string; url?: string}[] {
  const citations = new Map<string, {label: string; url?: string}>();
  for (const id of new Set(summary.counts.flatMap(count => count.sources))) {
    const source = sources[id]; if (!source) continue;
    const href = resolve(source);
    const url = href && /^https?:\/\//i.test(href) ? href : undefined;
    const label = String(source.name ?? source.doc ?? source.dataset ?? `Source ${id + 1}`);
    citations.set(url ?? label, {label, url});
  }
  return [...citations.values()];
}

/** Dynamic pages fetch one compact precomputed index, never crawl budget chunks. */
let indexPromise: Promise<StaffingIndex> | undefined;
export async function renderStaffingCount(container: HTMLElement, id: string, sources: Source[], resolve: (source: Source) => string | undefined): Promise<void> {
  container.replaceChildren();
  if (!isPersonnelNode({id})) return;
  try {
    const index = await (indexPromise ??= fetch('/data/headcounts.json').then(response => {
      if (!response.ok) throw Error('Staffing counts unavailable');
      return response.json();
    }).catch(error => {indexPromise = undefined; throw error;}));
    if (!container.isConnected) return;
    const summary = index[id]; if (!summary) return;
    const text = staffingText(summary);
    for (const line of text.lines) {const p = document.createElement('p'); const strong = document.createElement('strong'); strong.textContent = line; p.append(strong); container.append(p);}
    const caption = document.createElement('p'); caption.className = 'staffing-note'; caption.textContent = text.caption; container.append(caption);
    const details = document.createElement('details'); const label = document.createElement('summary'); label.textContent = 'How this is counted'; details.append(label);
    const note = document.createElement('p'); note.textContent = text.note; details.append(note);
    for (const citation of staffingSources(summary, sources, resolve)) {
      const p = document.createElement('p');
      if (citation.url) {const link = document.createElement('a'); link.href = citation.url; link.rel = 'noopener noreferrer'; link.textContent = citation.label; p.append(link);}
      else p.textContent = citation.label;
      details.append(p);
    }
    container.append(details);
  } catch {
    if (container.isConnected) container.textContent = 'Staffing count could not be loaded. See the source budget for position counts.';
  }
}
