import json
import logging
import urllib.parse
import urllib.request

import ccxt

from engine.state import state

logger = logging.getLogger(__name__)

_clients: dict[str, object] = {}


def _get_client(exchange_id: str):
    if exchange_id in _clients:
        return _clients[exchange_id]
    if exchange_id == "binance":
        _clients[exchange_id] = ccxt.binance({"options": {"defaultType": "future"}})
    elif exchange_id == "bybit":
        _clients[exchange_id] = ccxt.bybit({"options": {"defaultType": "future"}})
    elif exchange_id == "hyperliquid":
        _clients[exchange_id] = ccxt.hyperliquid()
    elif exchange_id == "bitget":
        _clients[exchange_id] = ccxt.bitget({"options": {"defaultType": "swap"}})
    elif exchange_id == "gate":
        _clients[exchange_id] = ccxt.gate({"options": {"defaultType": "swap"}})
    elif exchange_id == "mexc":
        _clients[exchange_id] = ccxt.mexc({"options": {"defaultType": "swap"}})
    else:
        raise ValueError(f"No ccxt client configured for {exchange_id}")
    return _clients[exchange_id]


def _ccxt_symbol(exchange_id: str, canonical: str) -> str | None:
    """Translate our canonical Binance-style id (BTCUSDT, 1000PEPEUSDT) into the
    ccxt symbol string the target exchange expects."""
    if exchange_id in ("binance", "bybit", "bitget", "gate", "mexc"):
        return canonical.replace("USDT", "/USDT:USDT")
    if exchange_id == "hyperliquid":
        pair = state.pairs.get(canonical)
        leg = pair.legs.get("hyperliquid") if pair else None
        if leg is None:
            return None
        # We don't store the native symbol on the leg, so recover it from
        # the canonical via the inverse of _hl_canonical_from_native.
        base = canonical[:-4] if canonical.endswith("USDT") else canonical
        if base.startswith("1000"):
            native = "k" + base[4:]
        else:
            native = base
        return f"{native}/USDC:USDC"
    return None


_ASTER_INTERVAL = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h",
    "12h": "12h", "1d": "1d", "3d": "3d", "1w": "1w", "1M": "1M",
}


def _fetch_aster_klines(canonical: str, timeframe: str, limit: int) -> list:
    """Native Aster kline fetch (ccxt doesn't ship an Aster adapter).
    Aster is Binance-fapi compatible — /fapi/v1/markPriceKlines returns
    [openTime, open, high, low, close, ...]."""
    interval = _ASTER_INTERVAL.get(timeframe)
    if not interval:
        return []
    url = "https://fapi.asterdex.com/fapi/v1/markPriceKlines?" + urllib.parse.urlencode({
        "symbol": canonical, "interval": interval, "limit": min(limit, 1500),
    })
    with urllib.request.urlopen(url, timeout=15) as resp:
        rows = json.loads(resp.read())
    return [[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), 0] for r in rows]


def _fetch_ohlcv(exchange_id: str, canonical_symbol: str, timeframe: str, limit: int) -> list:
    if exchange_id == "aster":
        return _fetch_aster_klines(canonical_symbol, timeframe, limit)
    client = _get_client(exchange_id)
    symbol = _ccxt_symbol(exchange_id, canonical_symbol)
    if not symbol:
        return []
    params = {"price": "mark"} if exchange_id in ("binance", "bybit", "bitget", "gate") else {}
    return client.fetch_ohlcv(
        symbol,
        timeframe=timeframe,
        limit=limit,
        params=params,
    )


def fetch_historical_spread(symbol: str, timeframe: str = "1m", limit: int = 500) -> list[dict]:
    """Fetch mark-price klines from every exchange that lists the pair, outer-join
    timestamps, and return [{timestamp, prices: {exchange_id: close}}]."""
    pair = state.pairs.get(symbol)
    if not pair:
        return []

    per_ex: dict[str, dict[int, float]] = {}
    for ex in pair.legs.keys():
        try:
            klines = _fetch_ohlcv(ex, symbol, timeframe, limit)
        except Exception as e:
            logger.error(f"Failed to fetch history for {symbol} from {ex}: {e}")
            continue
        by_ts = {}
        for k in klines:
            ts = k[0] // 1000
            close = k[4]
            if close and close > 0:
                by_ts[ts] = close
        per_ex[ex] = by_ts

    if not per_ex:
        return []

    all_ts = sorted({ts for m in per_ex.values() for ts in m.keys()})
    results = []
    for ts in all_ts:
        prices = {ex: m[ts] for ex, m in per_ex.items() if ts in m}
        if len(prices) >= 2:
            results.append({"timestamp": ts, "prices": prices})

    logger.info(f"Fetched {len(results)} historical points for {symbol} ({timeframe})")
    return results
