import ccxt
import logging
import time

logger = logging.getLogger(__name__)

_binance = None
_bybit = None


def _get_exchanges():
    global _binance, _bybit
    if _binance is None:
        _binance = ccxt.binance({"options": {"defaultType": "future"}})
        _bybit = ccxt.bybit({"options": {"defaultType": "future"}})
    return _binance, _bybit


def fetch_historical_spread(symbol: str, timeframe: str = "1m", limit: int = 500) -> list[dict]:
    """
    Fetch historical mark price klines from both exchanges and compute spread history.
    Returns list of {timestamp, spread_ab, spread_ba, price_binance, price_bybit}.
    """
    binance, bybit = _get_exchanges()

    try:
        # Fetch klines (OHLCV) from both exchanges
        # Using mark price for futures
        bn_klines = binance.fetch_ohlcv(
            symbol.replace("USDT", "/USDT:USDT"),
            timeframe=timeframe,
            limit=limit,
            params={"price": "mark"},
        )
        bb_klines = bybit.fetch_ohlcv(
            symbol.replace("USDT", "/USDT:USDT"),
            timeframe=timeframe,
            limit=limit,
            params={"price": "mark"},
        )
    except Exception as e:
        logger.error(f"Failed to fetch history for {symbol}: {e}")
        return []

    # Index bybit klines by timestamp for fast lookup
    bb_map = {}
    for k in bb_klines:
        ts = k[0] // 1000  # ms to seconds
        bb_map[ts] = k[4]  # close price

    results = []
    for k in bn_klines:
        ts = k[0] // 1000
        price_bn = k[4]  # close price
        price_bb = bb_map.get(ts)

        if price_bn and price_bb and price_bn > 0 and price_bb > 0:
            spread_ab = ((price_bb - price_bn) / price_bn) * 100
            spread_ba = ((price_bn - price_bb) / price_bb) * 100
            results.append({
                "timestamp": ts,
                "spread_ab": round(spread_ab, 4),
                "spread_ba": round(spread_ba, 4),
                "price_binance": price_bn,
                "price_bybit": price_bb,
            })

    logger.info(f"Fetched {len(results)} historical points for {symbol} ({timeframe})")
    return results
