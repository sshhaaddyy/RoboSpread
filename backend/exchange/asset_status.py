import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)

BINANCE_URL = "https://www.binance.com/bapi/capital/v1/public/capital/getNetworkCoinAll"
POLL_INTERVAL_SEC = 60.0
REQUEST_TIMEOUT_SEC = 15.0

MULTIPLIER_PREFIXES = ("1000000", "10000", "1000")


def extract_base_coin(symbol: str) -> str:
    """Primary base-coin guess (strips the common multiplier prefix when present)."""
    base = symbol[:-4] if symbol.endswith("USDT") else symbol
    for prefix in MULTIPLIER_PREFIXES:
        if base.startswith(prefix) and len(base) > len(prefix) and base[len(prefix)].isalpha():
            return base[len(prefix):]
    return base


def base_coin_candidates(symbol: str) -> list[str]:
    """All reasonable coin-name candidates, in priority order.

    Some exchanges list multiplier-prefixed futures as their own spot entry
    (e.g. `1000CAT`), while others strip the prefix (`PEPE` for `1000PEPEUSDT`).
    Try the raw form first, then the stripped form.
    """
    raw = symbol[:-4] if symbol.endswith("USDT") else symbol
    stripped = extract_base_coin(symbol)
    return [raw] if raw == stripped else [raw, stripped]


async def fetch_binance_coin_status(session: aiohttp.ClientSession) -> dict[str, dict]:
    """Returns {coin: {"deposit": bool, "withdraw": bool}} from Binance's public bapi endpoint."""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.binance.com/",
    }
    async with session.get(BINANCE_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SEC)) as resp:
        resp.raise_for_status()
        payload = await resp.json(content_type=None)

    result: dict[str, dict] = {}
    for entry in payload.get("data") or []:
        coin = entry.get("coin")
        if not coin:
            continue
        result[coin.upper()] = {
            "deposit": bool(entry.get("depositAllEnable")),
            "withdraw": bool(entry.get("withdrawAllEnable")),
        }
    return result


async def run_coin_status_poller(state):
    """Background task: refresh coin status periodically."""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                binance = await fetch_binance_coin_status(session)
                state.update_coin_status("binance", binance)
                logger.info(f"Coin status refreshed: Binance={len(binance)} coins")
            except Exception as e:
                logger.warning(f"Binance coin status fetch failed: {e}")
            await asyncio.sleep(POLL_INTERVAL_SEC)
