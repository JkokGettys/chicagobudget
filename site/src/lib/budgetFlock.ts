export type Boid = { x: number; y: number; vx: number; vy: number; group: number };
export type Attractor = { x: number; y: number };

/** Hamilton allocation: equal-value dots, with no artificial minimum for small categories. */
export function allocateParticles(amounts: readonly number[], count = 240): number[] {
  const weights = amounts.map(n => Number.isFinite(n) && n > 0 ? n : 0);
  const max = Math.max(0, ...weights);
  const total = max ? weights.reduce((sum, n) => sum + n / max, 0) : 0;
  const seats = Number.isFinite(count) ? Math.max(0, Math.floor(count)) : 0;
  if (!total || !seats) return weights.map(() => 0);
  const quotas = weights.map(n => (n / max) / total * seats);
  const result = quotas.map(Math.floor);
  const order = quotas.map((q, i) => ({ i, remainder: q - result[i] }))
    .filter(({ i }) => weights[i] > 0)
    .sort((a, b) => b.remainder - a.remainder || a.i - b.i);
  const remaining = seats - result.reduce((sum, n) => sum + n, 0);
  for (let i = 0; i < remaining; i++) result[order[i % order.length].i]++;
  return result;
}

/** One immutable flock step. Separation crosses groups, alignment/cohesion stay within a category. */
export function stepBoids(boids: readonly Boid[], targets: readonly Attractor[], width: number, height: number, dt = 1): Boid[] {
  const w = Number.isFinite(width) ? Math.max(1, width) : 1;
  const h = Number.isFinite(height) ? Math.max(1, height) : 1;
  const t = Number.isFinite(dt) ? Math.max(0, Math.min(2, dt)) : 1;
  const finite = (n: number, fallback = 0) => Number.isFinite(n) ? n : fallback;
  const clamp = (n: number, limit: number) => Math.max(0, Math.min(limit, n));
  const clean = boids.map(b => ({ ...b, x: clamp(finite(b.x, w / 2), w), y: clamp(finite(b.y, h / 2), h), vx: finite(b.vx), vy: finite(b.vy) }));
  return clean.map((b, i) => {
    let sx = 0, sy = 0, ax = 0, ay = 0, cx = 0, cy = 0, neighbors = 0;
    for (let j = 0; j < clean.length; j++) {
      if (i === j) continue;
      const other = clean[j], dx = b.x - other.x, dy = b.y - other.y;
      const d2 = dx * dx + dy * dy;
      if (d2 < 225 && d2 > .0001) { sx += dx / d2; sy += dy / d2; }
      if (d2 < 3600 && other.group === b.group) {
        ax += other.vx; ay += other.vy; cx += other.x; cy += other.y; neighbors++;
      }
    }
    const target = targets[b.group] ?? { x: w / 2, y: h / 2 };
    const tx = finite(target.x, w / 2) - b.x, ty = finite(target.y, h / 2) - b.y;
    // A gentle tangential current keeps each flock circulating without moving its category center.
    const orbit = Math.max(24, Math.hypot(tx, ty));
    let vx = b.vx + (sx * 1.6 + tx * .0018 - ty / orbit * .022) * t;
    let vy = b.vy + (sy * 1.6 + ty * .0018 + tx / orbit * .022) * t;
    if (neighbors) {
      vx += ((ax / neighbors - b.vx) * .045 + (cx / neighbors - b.x) * .0009) * t;
      vy += ((ay / neighbors - b.vy) * .045 + (cy / neighbors - b.y) * .0009) * t;
    }
    const speed = Math.hypot(vx, vy);
    if (speed > 1.45) { vx = vx / speed * 1.45; vy = vy / speed * 1.45; }
    let x = b.x + vx * t, y = b.y + vy * t;
    if (x < 0 || x > w) vx *= -.7;
    if (y < 0 || y > h) vy *= -.7;
    x = clamp(x, w); y = clamp(y, h);
    return { x, y, vx, vy, group: b.group };
  });
}
