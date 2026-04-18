from dataclasses import dataclass
from config import BINANCE_TAKER_FEE, BYBIT_TAKER_FEE, ROUND_TRIP_FEE


@dataclass
class SpreadResult:
    # Long Binance / Short Bybit
    spread_ab: float        # raw spread %
    net_spread_ab: float    # after fees %
    # Long Bybit / Short Binance
    spread_ba: float        # raw spread %
    net_spread_ba: float    # after fees %
    # Best direction
    best_direction: str     # "long_binance" or "long_bybit"
    best_net_spread: float  # best net spread %
    entry_cost: float       # cost to enter %
    exit_cost: float        # cost to exit %


def calc_spread(price_binance: float, price_bybit: float) -> SpreadResult:
    """
    Calculate spread between two exchanges in both directions.

    Long Binance / Short Bybit: you buy on Binance (lower price), sell on Bybit (higher price)
      → spread = (bybit - binance) / binance * 100

    Long Bybit / Short Binance: opposite direction
      → spread = (binance - bybit) / bybit * 100

    Entry cost = taker fee on both exchanges (one buy, one sell)
    Exit cost = same (close both positions)
    Total round-trip = 2 * (binance_fee + bybit_fee)
    """
    if price_binance <= 0 or price_bybit <= 0:
        return SpreadResult(0, 0, 0, 0, "none", 0, 0, 0)

    # Raw spreads
    spread_ab = ((price_bybit - price_binance) / price_binance) * 100
    spread_ba = ((price_binance - price_bybit) / price_bybit) * 100

    # Fee costs (entry = open both sides, exit = close both sides)
    entry_cost = BINANCE_TAKER_FEE + BYBIT_TAKER_FEE  # 0.095%
    exit_cost = BINANCE_TAKER_FEE + BYBIT_TAKER_FEE    # 0.095%

    # Net spreads after round-trip fees
    net_spread_ab = spread_ab - ROUND_TRIP_FEE
    net_spread_ba = spread_ba - ROUND_TRIP_FEE

    if net_spread_ab >= net_spread_ba:
        best_direction = "long_binance"
        best_net = net_spread_ab
    else:
        best_direction = "long_bybit"
        best_net = net_spread_ba

    return SpreadResult(
        spread_ab=round(spread_ab, 4),
        net_spread_ab=round(net_spread_ab, 4),
        spread_ba=round(spread_ba, 4),
        net_spread_ba=round(net_spread_ba, 4),
        best_direction=best_direction,
        best_net_spread=round(best_net, 4),
        entry_cost=round(entry_cost, 4),
        exit_cost=round(exit_cost, 4),
    )


def calc_funding_spread_apr(
    funding_binance: float, funding_bybit: float,
    interval_h_binance: float = 8.0, interval_h_bybit: float = 8.0,
) -> float:
    """
    Calculate annualized funding spread, normalized by each exchange's interval.
    Annual rate = raw_rate * (24 / interval_hours) * 365 * 100
    """
    annual_bn = funding_binance * (24 / interval_h_binance) * 365 * 100
    annual_bb = funding_bybit * (24 / interval_h_bybit) * 365 * 100
    return round(annual_bn - annual_bb, 4)
