import time
from collections import deque
from dataclasses import dataclass, field

from config import HISTORY_MAX_LEN, STALE_THRESHOLD_SEC, EXCHANGES
from engine.spread_calc import Route, best_arb_route, best_funding_route
from exchange.asset_status import base_coin_candidates


@dataclass
class ExchangeLeg:
    exchange_id: str
    mark_price: float = 0.0
    funding_rate: float = 0.0
    funding_interval_h: float = 8.0
    next_funding_time: float = 0.0
    last_update: float = 0.0

    @property
    def is_stale(self) -> bool:
        if self.last_update == 0:
            return True
        return time.time() - self.last_update > STALE_THRESHOLD_SEC

    def to_dict(self) -> dict:
        return {
            "exchange_id": self.exchange_id,
            "mark_price": self.mark_price,
            "funding_rate": self.funding_rate,
            "funding_interval_h": self.funding_interval_h,
            "next_funding_time": self.next_funding_time,
            "last_update": self.last_update,
            "is_stale": self.is_stale,
        }


@dataclass
class PriceSnapshot:
    timestamp: float
    prices: dict[str, float]  # exchange_id -> mark_price at this tick


@dataclass
class PairState:
    symbol: str
    legs: dict[str, ExchangeLeg] = field(default_factory=dict)
    best_arb: Route | None = None
    best_funding: Route | None = None
    history: deque = field(default_factory=lambda: deque(maxlen=HISTORY_MAX_LEN))

    @property
    def is_stale(self) -> bool:
        # Pair is live whenever at least 2 of its legs have fresh data.
        # A single laggy venue shouldn't gray out a 3+-leg pair.
        fresh = [
            leg for leg in self.legs.values()
            if leg.last_update > 0 and not leg.is_stale
        ]
        return len(fresh) < 2

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "legs": {ex: leg.to_dict() for ex, leg in self.legs.items()},
            "best_arb_route": self.best_arb.to_dict() if self.best_arb else None,
            "best_funding_route": self.best_funding.to_dict() if self.best_funding else None,
            "is_stale": self.is_stale,
        }


class AppState:
    def __init__(self):
        self.pairs: dict[str, PairState] = {}
        self._update_callbacks: list = []
        self.coin_status: dict[str, dict[str, dict]] = {ex: {} for ex in EXCHANGES}

    def init_pairs(self, per_exchange: dict[str, dict[str, str]]):
        """Create PairState for the union of symbols across all exchanges.

        `per_exchange[exchange_id][canonical_symbol] = native_symbol` — a leg is
        only created for the exchanges that actually list the pair, so a 2-venue
        pair on Binance+Bybit stays 2-legged while a 3-venue pair grows a
        Hyperliquid leg.
        """
        all_symbols: set[str] = set()
        for m in per_exchange.values():
            all_symbols.update(m.keys())
        for symbol in sorted(all_symbols):
            pair = PairState(symbol=symbol)
            for ex, m in per_exchange.items():
                if symbol not in m:
                    continue
                pair.legs[ex] = ExchangeLeg(
                    exchange_id=ex,
                    funding_interval_h=EXCHANGES[ex]["default_funding_interval_h"],
                )
            self.pairs[symbol] = pair

    def on_update(self, callback):
        self._update_callbacks.append(callback)

    def update_coin_status(self, exchange: str, status: dict[str, dict]):
        self.coin_status[exchange] = status

    def coin_status_for(self, symbol: str) -> dict:
        candidates = base_coin_candidates(symbol)
        out: dict = {"coin": candidates[0]}
        for ex in EXCHANGES:
            ex_map = self.coin_status.get(ex, {})
            match = next((ex_map[c] for c in candidates if c in ex_map), None)
            out[f"{ex}_deposit"] = match["deposit"] if match else None
            out[f"{ex}_withdraw"] = match["withdraw"] if match else None
        return out

    def update_leg(
        self,
        exchange_id: str,
        symbol: str,
        mark_price: float,
        funding_rate: float | None = None,
        next_funding_time: float | None = None,
        funding_interval_h: float | None = None,
    ):
        pair = self.pairs.get(symbol)
        if not pair:
            return
        leg = pair.legs.get(exchange_id)
        if not leg:
            return

        now = time.time()
        leg.mark_price = mark_price
        leg.last_update = now
        if funding_rate is not None:
            leg.funding_rate = funding_rate
        if next_funding_time is not None:
            leg.next_funding_time = next_funding_time
        if funding_interval_h is not None:
            leg.funding_interval_h = funding_interval_h

        priced_legs = {ex: l for ex, l in pair.legs.items() if l.mark_price > 0}
        if len(priced_legs) >= 2:
            pair.best_arb = best_arb_route(priced_legs)
            pair.best_funding = best_funding_route(priced_legs)
            pair.history.append(PriceSnapshot(
                timestamp=now,
                prices={ex: l.mark_price for ex, l in priced_legs.items()},
            ))

        for cb in self._update_callbacks:
            cb(symbol, pair)

    def get_all_pairs(self) -> list[dict]:
        out = []
        for p in self.pairs.values():
            if p.best_arb is None:
                continue
            d = p.to_dict()
            d["coin_status"] = self.coin_status_for(p.symbol)
            out.append(d)
        return out

    def get_history(self, symbol: str) -> list[dict]:
        pair = self.pairs.get(symbol)
        if not pair:
            return []
        return [
            {"timestamp": s.timestamp, "prices": s.prices}
            for s in pair.history
        ]


state = AppState()
