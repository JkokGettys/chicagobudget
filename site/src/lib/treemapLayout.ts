/** Pure, deterministic area layout. Coordinates are SVG viewBox units, not CSS pixels. */
export type Weighted = { id: string; amount_cents: number };
export type Rectangle<T extends Weighted> = { item: T; x: number; y: number; width: number; height: number; children: Rectangle<T>[] };
export type Treemap<T extends Weighted> = { rectangles: Rectangle<T>[]; positiveTotalCents: number; negative: T[]; zero: T[]; denominatorCents: number };
export type Options<T extends Weighted> = { width?: number; height?: number; maxItems?: number; nested?: (item: T) => readonly T[]; maxDepth?: number };

function finiteCents(n: number): number {
  if (!Number.isSafeInteger(n)) throw new RangeError('Amounts must be safe integer cents');
  return n;
}

/** Subdivide a rectangle without padding or minimum sizes, so area stays linear in cents. */
function partition<T extends Weighted>(items: readonly T[], x: number, y: number, width: number, height: number): Rectangle<T>[] {
  const total = items.reduce((sum, item) => sum + item.amount_cents, 0);
  if (!total || !width || !height) return [];
  const result: Rectangle<T>[] = [];
  // Deterministic recursive slice-dice, splitting near half the weight along the longer edge.
  function divide(group: readonly T[], gx: number, gy: number, gw: number, gh: number, sum: number): void {
    if (group.length === 1) { result.push({ item: group[0], x: gx, y: gy, width: gw, height: gh, children: [] }); return; }
    let split = 1, subtotal = group[0].amount_cents;
    while (split < group.length - 1 && subtotal + group[split].amount_cents <= sum / 2) subtotal += group[split++].amount_cents;
    const fraction = subtotal / sum;
    if (gw >= gh) {
      const first = gw * fraction;
      divide(group.slice(0, split), gx, gy, first, gh, subtotal);
      divide(group.slice(split), gx + first, gy, gw - first, gh, sum - subtotal);
    } else {
      const first = gh * fraction;
      divide(group.slice(0, split), gx, gy, gw, first, subtotal);
      divide(group.slice(split), gx, gy + first, gw, gh - first, sum - subtotal);
    }
  }
  divide(items, x, y, width, height, total);
  return result;
}

/** Positives fill the map using their gross total. Negatives and zeros never acquire area.
 * An overflow rectangle groups every unshown positive, preserving its exact combined area.
 * Nested children are drawn only when their positive sum exactly reconciles to the parent
 * and there are no negative/zero children, never stretching partial data to fill a region.
 */
export function layoutTreemap<T extends Weighted>(parentAmountCents: number, children: readonly T[], options: Options<T> = {}): Treemap<T> {
  finiteCents(parentAmountCents);
  const width = options.width ?? 1200, height = options.height ?? 680;
  const maxItems = options.maxItems ?? 24, maxDepth = options.maxDepth ?? 1;
  if (![width, height].every(n => Number.isFinite(n) && n > 0) || !Number.isSafeInteger(maxItems) || maxItems < 1 || !Number.isSafeInteger(maxDepth) || maxDepth < 0) throw new RangeError('Invalid treemap dimensions or limits');
  const positive: T[] = [], negative: T[] = [], zero: T[] = [];
  for (const child of children) {
    const amount = finiteCents(child.amount_cents);
    if (amount > 0) positive.push(child);
    else if (amount < 0) negative.push(child);
    else zero.push(child);
  }
  const positiveTotalCents = finiteCents(positive.reduce((sum, item) => sum + item.amount_cents, 0));
  function build(items: T[], x: number, y: number, w: number, h: number, depth: number): Rectangle<T>[] {
    const shown = items.length > maxItems
      ? [...items.slice(0, maxItems - 1), { id: '__treemap_other__', amount_cents: items.slice(maxItems - 1).reduce((sum, item) => sum + item.amount_cents, 0) } as T]
      : items;
    const rectangles = partition(shown, x, y, w, h);
    if (depth >= maxDepth || !options.nested) return rectangles;
    for (const rect of rectangles) {
      if (rect.item.id === '__treemap_other__' || rect.width < 80 || rect.height < 70) continue;
      const sub = options.nested(rect.item);
      if (!sub.length || sub.length > maxItems || sub.some(item => finiteCents(item.amount_cents) <= 0)) continue;
      if (finiteCents(sub.reduce((sum, item) => sum + item.amount_cents, 0)) !== rect.item.amount_cents) continue;
      rect.children = build([...sub], rect.x, rect.y, rect.width, rect.height, depth + 1);
    }
    return rectangles;
  }
  return { rectangles: build(positive, 0, 0, width, height, 0), positiveTotalCents, negative, zero, denominatorCents: positiveTotalCents };
}
