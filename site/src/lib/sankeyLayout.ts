/** Geometry for a single budget box and its immediate children. No DOM or data loading. */
export type FlowChild = { id: string; amount_cents: number };

export type FlowOptions = {
  width?: number;
  height?: number;
  gap?: number;
  /** Includes the optional "N more" row. All omitted children remain in children. */
  maxVisualChildren?: number;
};

export type FlowRow<T extends FlowChild> = {
  id: string;
  amount_cents: number;
  y: number;
  height: number;
  sourceY: number;
  /** Closed, filled SVG ribbon from (0, sourceY) to (width, y). */
  path: string;
  isOverflow: boolean;
  /** One original child, or every member of the synthetic overflow row. */
  children: T[];
};

export type FlowLayout<T extends FlowChild> = {
  rows: FlowRow<T>[];
  children: T[];
  negativeChildren: T[];
  zeroChildren: T[];
  parentAmountCents: number;
  positiveTotalCents: number;
  negativeTotalCents: number;
  /** Scale is gross positive when adjustments make positives exceed the net parent. */
  denominatorCents: number;
  /** Height occupied by outgoing positive ribbons, not necessarily the net parent. */
  sourceHeight: number;
  /** Height of the net parent on the same scale. */
  parentHeight: number;
  width: number;
  height: number;
  gap: number;
  /** Non-null when the visual needs a net/gross or unallocated-area explanation. */
  explanation: string | null;
};

function cents(value: number, name: string): number {
  if (!Number.isSafeInteger(value)) throw new RangeError(`${name} must be a safe integer number of cents`);
  return value;
}

function dimension(value: number, name: string, allowZero = false): number {
  if (!Number.isFinite(value) || (allowZero ? value < 0 : value <= 0))
    throw new RangeError(`${name} must be ${allowZero ? 'nonnegative' : 'positive'} and finite`);
  return value;
}

function ribbon(width: number, sourceY: number, y: number, thickness: number): string {
  const bend = width / 2;
  return `M 0 ${sourceY} C ${bend} ${sourceY} ${bend} ${y} ${width} ${y} L ${width} ${y + thickness} C ${bend} ${y + thickness} ${bend} ${sourceY + thickness} 0 ${sourceY + thickness} Z`;
}

/**
 * Layout one drill-down step. The caller supplies three independent roots as
 * three separate calls, never as one artificially combined budget.
 *
 * Area is linear in exact positive cents. Tiny amounts may be subpixel and
 * must not be enlarged silently. Negative adjustments and zeros are returned
 * separately and never become positive ribbons. Input order is preserved.
 */
export function layoutFlow<T extends FlowChild>(
  parentAmountCents: number,
  children: readonly T[],
  opts: FlowOptions = {},
): FlowLayout<T> {
  cents(parentAmountCents, 'parentAmountCents');
  const width = dimension(opts.width ?? 560, 'width');
  const height = dimension(opts.height ?? 320, 'height');
  const gap = dimension(opts.gap ?? 4, 'gap', true);
  const maxVisualChildren = opts.maxVisualChildren ?? 16;
  if (!Number.isSafeInteger(maxVisualChildren) || maxVisualChildren < 1)
    throw new RangeError('maxVisualChildren must be a positive integer');

  const all = Array.from(children);
  const positive: T[] = [];
  const negativeChildren: T[] = [];
  const zeroChildren: T[] = [];
  let positiveTotalCents = 0;
  let negativeTotalCents = 0;
  for (const child of all) {
    const amount = cents(child.amount_cents, `amount_cents for ${child.id}`);
    if (amount > 0) {
      positive.push(child);
      positiveTotalCents = cents(positiveTotalCents + amount, 'positiveTotalCents');
    } else if (amount < 0) {
      negativeChildren.push(child);
      negativeTotalCents = cents(negativeTotalCents + amount, 'negativeTotalCents');
    } else zeroChildren.push(child);
  }

  const denominatorCents = Math.max(0, parentAmountCents, positiveTotalCents);
  const groups: T[][] = positive.length > maxVisualChildren
    ? [...positive.slice(0, maxVisualChildren - 1).map(child => [child]), positive.slice(maxVisualChildren - 1)]
    : positive.map(child => [child]);
  const usableHeight = height - gap * Math.max(0, groups.length - 1);
  if (usableHeight < 0) throw new RangeError('height is too small for the requested rows and gap');
  const unit = denominatorCents === 0 ? 0 : usableHeight / denominatorCents;
  const occupied = new Set(all.map(child => child.id));
  let overflowId = '__more__';
  while (occupied.has(overflowId)) overflowId += '_';
  let sourceY = 0;
  let y = 0;
  const rows: FlowRow<T>[] = groups.map((group, index) => {
    const amount_cents = group.reduce((sum, child) => sum + child.amount_cents, 0);
    const rowHeight = amount_cents * unit;
    const isOverflow = group.length > 1;
    const row: FlowRow<T> = {
      id: isOverflow ? overflowId : group[0].id,
      amount_cents,
      y,
      height: rowHeight,
      sourceY,
      path: ribbon(width, sourceY, y, rowHeight),
      isOverflow,
      children: group,
    };
    sourceY += rowHeight;
    y += rowHeight + (index < groups.length - 1 ? gap : 0);
    return row;
  });

  let explanation: string | null = null;
  if (positiveTotalCents > Math.max(0, parentAmountCents)) {
    explanation = `Positive branches total ${positiveTotalCents} cents, more than the net parent (${parentAmountCents} cents). `
      + `Ribbon heights use gross positives as their denominator; negative adjustments (${negativeTotalCents} cents) are listed separately, never drawn as area.`;
  } else if (negativeChildren.length) {
    explanation = `Negative adjustments total ${negativeTotalCents} cents and are listed separately, never drawn as positive area.`;
  } else if (positiveTotalCents < parentAmountCents && positive.length) {
    explanation = `Shown positive branches total ${positiveTotalCents} cents of the ${parentAmountCents}-cent parent; the remainder has no ribbon.`;
  }
  return {
    rows, children: all, negativeChildren, zeroChildren, parentAmountCents,
    positiveTotalCents, negativeTotalCents, denominatorCents,
    sourceHeight: sourceY,
    parentHeight: Math.max(0, parentAmountCents) * unit,
    width, height, gap, explanation,
  };
}
