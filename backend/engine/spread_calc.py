from dataclasses import dataclass
from itertools import permutations

from config import EXCHANGES, round_trip_fee_pct


@dataclass
class Route:
    long_ex: str
    short_ex: str
    raw_spread_pct: float       # (price_short - price_long) / price_long * 100
    instant_edge_pct: float     # raw_spread - round_trip_fee
    funding_apr_pct: float      # short_leg_apr - long_leg_apr
    breakeven_h: float | None   # hours funding must pay to cover fees; None if funding <= 0
    entry_cost_pct: float       # taker_long + taker_short (one side)
    exit_cost_pct: float        # same
    round_trip_fee_pct: float

    def to_dict(self) -> dict:
        return {
            "long_ex": self.long_ex,
            "short_ex": self.short_ex,
            "raw_spread_pct": round(self.raw_spread_pct, 4),
            "instant_edge_pct": round(self.instant_edge_pct, 4),
            "funding_apr_pct": round(self.funding_apr_pct, 4),
            "breakeven_h": round(self.breakeven_h, 2) if self.breakeven_h is not None else None,
            "entry_cost_pct": round(self.entry_cost_pct, 4),
            "exit_cost_pct": round(self.exit_cost_pct, 4),
            "round_trip_fee_pct": round(self.round_trip_fee_pct, 4),
        }


def _leg_funding_apr(leg) -> float:
    interval = leg.funding_interval_h or 8.0
    return leg.funding_rate * (24.0 / interval) * 365 * 100


def compute_route(legs: dict, long_ex: str, short_ex: str) -> Route | None:
    if long_ex == short_ex:
        return None
    long_leg = legs.get(long_ex)
    short_leg = legs.get(short_ex)
    if not long_leg or not short_leg:
        return None
    if long_leg.mark_price <= 0 or short_leg.mark_price <= 0:
        return None

    raw = ((short_leg.mark_price - long_leg.mark_price) / long_leg.mark_price) * 100
    rt_fee = round_trip_fee_pct(long_ex, short_ex)
    instant_edge = raw - rt_fee
    entry = EXCHANGES[long_ex]["taker_fee"] + EXCHANGES[short_ex]["taker_fee"]
    exit_cost = entry

    funding_apr = _leg_funding_apr(short_leg) - _leg_funding_apr(long_leg)
    breakeven = (rt_fee / (funding_apr / 8760)) if funding_apr > 0 else None

    return Route(
        long_ex=long_ex,
        short_ex=short_ex,
        raw_spread_pct=raw,
        instant_edge_pct=instant_edge,
        funding_apr_pct=funding_apr,
        breakeven_h=breakeven,
        entry_cost_pct=entry,
        exit_cost_pct=exit_cost,
        round_trip_fee_pct=rt_fee,
    )


def all_routes(legs: dict) -> list[Route]:
    """All ordered (long_ex, short_ex) permutations with valid prices on both legs."""
    out = []
    for long_ex, short_ex in permutations(legs.keys(), 2):
        r = compute_route(legs, long_ex, short_ex)
        if r is not None:
            out.append(r)
    return out


def best_arb_route(legs: dict) -> Route | None:
    """Highest instant_edge_pct across all pair permutations."""
    routes = all_routes(legs)
    if not routes:
        return None
    return max(routes, key=lambda r: r.instant_edge_pct)


def best_funding_route(legs: dict) -> Route | None:
    """Highest funding APR net of one-time round-trip fee."""
    routes = all_routes(legs)
    if not routes:
        return None
    return max(routes, key=lambda r: r.funding_apr_pct - r.round_trip_fee_pct)
