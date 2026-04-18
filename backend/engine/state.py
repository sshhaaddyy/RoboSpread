import time
from collections import deque
from dataclasses import dataclass, field

from config import HISTORY_MAX_LEN, STALE_THRESHOLD_SEC
from engine.spread_calc import SpreadResult, calc_spread, calc_funding_spread_apr


@dataclass
class SpreadSnapshot:
    timestamp: float
    spread_ab: float
    spread_ba: float
    price_binance: float
    price_bybit: float


@dataclass
class PairState:
    symbol: str
    price_binance: float = 0.0
    price_bybit: float = 0.0
    funding_binance: float = 0.0
    funding_bybit: float = 0.0
    next_funding_time_binance: float = 0.0
    next_funding_time_bybit: float = 0.0
    funding_interval_h_binance: float = 8.0
    funding_interval_h_bybit: float = 8.0
    last_update_binance: float = 0.0
    last_update_bybit: float = 0.0
    spread: SpreadResult | None = None
    funding_spread_apr: float = 0.0
    history: deque = field(default_factory=lambda: deque(maxlen=HISTORY_MAX_LEN))

    @property
    def is_stale(self) -> bool:
        now = time.time()
        return (
            (now - self.last_update_binance > STALE_THRESHOLD_SEC)
            or (now - self.last_update_bybit > STALE_THRESHOLD_SEC)
        )

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "price_binance": self.price_binance,
            "price_bybit": self.price_bybit,
            "funding_binance": self.funding_binance,
            "funding_bybit": self.funding_bybit,
            "next_funding_time_binance": self.next_funding_time_binance,
            "next_funding_time_bybit": self.next_funding_time_bybit,
            "funding_interval_h_binance": self.funding_interval_h_binance,
            "funding_interval_h_bybit": self.funding_interval_h_bybit,
            "spread": {
                "spread_ab": self.spread.spread_ab,
                "net_spread_ab": self.spread.net_spread_ab,
                "spread_ba": self.spread.spread_ba,
                "net_spread_ba": self.spread.net_spread_ba,
                "best_direction": self.spread.best_direction,
                "best_net_spread": self.spread.best_net_spread,
                "entry_cost": self.spread.entry_cost,
                "exit_cost": self.spread.exit_cost,
            } if self.spread else None,
            "funding_spread_apr": self.funding_spread_apr,
            "is_stale": self.is_stale,
        }


class AppState:
    def __init__(self):
        self.pairs: dict[str, PairState] = {}
        self._update_callbacks: list = []

    def init_pairs(self, symbols: list[str]):
        for symbol in symbols:
            self.pairs[symbol] = PairState(symbol=symbol)

    def on_update(self, callback):
        self._update_callbacks.append(callback)

    def update_price(
        self, exchange: str, symbol: str, price: float,
        funding_rate: float | None = None,
        next_funding_time: float | None = None,
        funding_interval_h: float | None = None,
    ):
        if symbol not in self.pairs:
            return

        pair = self.pairs[symbol]
        now = time.time()

        if exchange == "binance":
            pair.price_binance = price
            pair.last_update_binance = now
            if funding_rate is not None:
                pair.funding_binance = funding_rate
            if next_funding_time is not None:
                pair.next_funding_time_binance = next_funding_time
            if funding_interval_h is not None:
                pair.funding_interval_h_binance = funding_interval_h
        elif exchange == "bybit":
            pair.price_bybit = price
            pair.last_update_bybit = now
            if funding_rate is not None:
                pair.funding_bybit = funding_rate
            if next_funding_time is not None:
                pair.next_funding_time_bybit = next_funding_time
            if funding_interval_h is not None:
                pair.funding_interval_h_bybit = funding_interval_h

        if pair.price_binance > 0 and pair.price_bybit > 0:
            pair.spread = calc_spread(pair.price_binance, pair.price_bybit)
            pair.funding_spread_apr = calc_funding_spread_apr(
                pair.funding_binance, pair.funding_bybit,
                pair.funding_interval_h_binance, pair.funding_interval_h_bybit,
            )
            pair.history.append(SpreadSnapshot(
                timestamp=now,
                spread_ab=pair.spread.spread_ab,
                spread_ba=pair.spread.spread_ba,
                price_binance=pair.price_binance,
                price_bybit=pair.price_bybit,
            ))

        for cb in self._update_callbacks:
            cb(symbol, pair)

    def get_all_pairs(self) -> list[dict]:
        return [p.to_dict() for p in self.pairs.values() if p.spread is not None]

    def get_history(self, symbol: str) -> list[dict]:
        pair = self.pairs.get(symbol)
        if not pair:
            return []
        return [
            {
                "timestamp": s.timestamp,
                "spread_ab": s.spread_ab,
                "spread_ba": s.spread_ba,
                "price_binance": s.price_binance,
                "price_bybit": s.price_bybit,
            }
            for s in pair.history
        ]


state = AppState()
