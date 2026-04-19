// Route / leg helpers used by the table, detail view, and chart.

export function rawSpread(legs, longEx, shortEx) {
  const longP = legs?.[longEx]?.mark_price;
  const shortP = legs?.[shortEx]?.mark_price;
  if (!longP || !shortP) return 0;
  return ((shortP - longP) / longP) * 100;
}

export function reverseRawSpread(legs, route) {
  if (!route) return 0;
  return rawSpread(legs, route.short_ex, route.long_ex);
}

export function inOutFromRoute(legs, route, flipped) {
  // Out = raw spread in the best-arb direction (positive)
  // In  = raw spread in the opposite direction (negative mirror)
  // flipped swaps In/Out.
  if (!route) return { inVal: 0, outVal: 0 };
  const forward = route.raw_spread_pct;
  const reverse = reverseRawSpread(legs, route);
  return flipped
    ? { inVal: forward, outVal: reverse }
    : { inVal: reverse, outVal: forward };
}
