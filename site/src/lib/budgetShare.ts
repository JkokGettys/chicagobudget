// Signed share of the containing budget, not of the sum of positive children.
// A non-positive/missing parent has no meaningful percentage denominator.
export function budgetShare(amount: number, parentAmount: number): string | null {
  if (!Number.isFinite(amount) || !Number.isFinite(parentAmount) || parentAmount <= 0) return null;
  const share = amount / parentAmount * 100;
  if (!Number.isFinite(share)) return null;
  if (share !== 0 && Math.abs(share) < 0.1) return `${share < 0 ? '-' : ''}<0.1%`;
  return `${share.toFixed(1)}%`;
}
