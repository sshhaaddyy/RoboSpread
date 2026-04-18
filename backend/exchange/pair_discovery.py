import ccxt
import logging

logger = logging.getLogger(__name__)


def discover_common_pairs() -> list[str]:
    """Find all USDT perpetual futures pairs common to both Binance and Bybit."""
    logger.info("Discovering common USDT perpetual pairs...")

    binance = ccxt.binance({"options": {"defaultType": "future"}})
    bybit = ccxt.bybit({"options": {"defaultType": "future"}})

    binance_markets = binance.load_markets()
    bybit_markets = bybit.load_markets()

    binance_perps = set()
    for symbol, market in binance_markets.items():
        if (
            market.get("linear")
            and market.get("active")
            and market.get("settle") == "USDT"
            and market.get("type") == "swap"
        ):
            binance_perps.add(market["id"])  # e.g. "BTCUSDT"

    bybit_perps = set()
    for symbol, market in bybit_markets.items():
        if (
            market.get("linear")
            and market.get("active")
            and market.get("settle") == "USDT"
            and market.get("type") == "swap"
        ):
            bybit_perps.add(market["id"])  # e.g. "BTCUSDT"

    common = sorted(binance_perps & bybit_perps)
    logger.info(f"Found {len(binance_perps)} Binance, {len(bybit_perps)} Bybit, {len(common)} common pairs")

    return common
