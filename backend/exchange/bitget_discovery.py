import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

CONTRACTS_URL = (
    "https://api.bitget.com/api/v2/mix/market/contracts?productType=USDT-FUTURES"
)


def _fetch() -> list[dict]:
    req = urllib.request.Request(
        CONTRACTS_URL,
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())
    if str(payload.get("code")) != "00000":
        raise RuntimeError(f"Bitget contracts error: {payload.get('msg')}")
    return payload.get("data") or []


def discover_bitget() -> tuple[dict[str, str], dict[str, float]]:
    """Fetch the USDT-FUTURES contract universe.

    Returns:
      ({canonical: native}, {canonical: funding_interval_hours})

    Bitget native symbols already match Binance canonical form (`BTCUSDT`), so
    the first map is an identity. The second map is the per-symbol funding
    interval straight from `fundInterval` — authoritative live value, used
    instead of the config default (intervals on Bitget range 1h/2h/4h/8h).
    """
    try:
        contracts = _fetch()
    except Exception as e:
        logger.error(f"Bitget discovery failed: {e}")
        return {}, {}

    natives: dict[str, str] = {}
    intervals: dict[str, float] = {}
    for c in contracts:
        symbol = c.get("symbol")
        status = c.get("symbolStatus")
        if not symbol or status != "normal":
            continue
        natives[symbol] = symbol
        try:
            intervals[symbol] = float(c.get("fundInterval") or 8)
        except (TypeError, ValueError):
            intervals[symbol] = 8.0
    return natives, intervals


# Cache so the WS connector can reach the interval map without re-fetching.
_interval_cache: dict[str, float] = {}


def bitget_interval_map() -> dict[str, float]:
    return _interval_cache


def _set_interval_cache(m: dict[str, float]):
    _interval_cache.clear()
    _interval_cache.update(m)
