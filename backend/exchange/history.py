import ccxt
import logging

logger = logging.getLogger(__name__)

_clients: dict[str, object] = {}


def _get_client(exchange_id: str):
    if exchange_id in _clients:
        return _clients[exchange_id]
    if exchange_id == "binance":
        _clients[exchange_id] = ccxt.binance({"options": {"defaultType": "future"}})
    elif exchange_id == "bybit":
        _clients[exchange_id] = ccxt.bybit({"options": {"defaultType": "future"}})
    else:
        raise ValueError(f"No ccxt client configured for {exchange_id}")
    return _clients[exchange_id]


def _fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str, limit: int) -> list:
    client = _get_client(exchange_id)
    return client.fetch_ohlcv(
        symbol.replace("USDT", "/USDT:USDT"),
        timeframe=timeframe,
        limit=limit,
        params={"price": "mark"},
    )


def fetch_historical_spread(symbol: str, timeframe: str = "1m", limit: int = 500) -> list[dict]:
    """
    Fetch historical mark-price klines from every registered exchange and return
    a list of snapshots: [{timestamp, prices: {exchange_id: close_price}}].
    Timestamps without a value from every exchange are still returned — the frontend
    filters legs it needs for the chosen route.
    """
    from config import EXCHANGES

    per_ex: dict[str, dict[int, float]] = {}
    for ex in EXCHANGES.keys():
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

    # Outer-join timestamps across all exchanges
    all_ts = sorted({ts for m in per_ex.values() for ts in m.keys()})
    results = []
    for ts in all_ts:
        prices = {ex: m[ts] for ex, m in per_ex.items() if ts in m}
        if len(prices) >= 2:
            results.append({"timestamp": ts, "prices": prices})

    logger.info(f"Fetched {len(results)} historical points for {symbol} ({timeframe})")
    return results
