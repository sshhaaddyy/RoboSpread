import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

EXCHANGE_INFO_URL = "https://fapi.asterdex.com/fapi/v3/exchangeInfo"
FUNDING_INFO_URL = "https://fapi.asterdex.com/fapi/v3/fundingInfo"

_interval_cache: dict[str, float] = {}


def _set_interval_cache(intervals: dict[str, float]) -> None:
    _interval_cache.clear()
    _interval_cache.update(intervals)


def aster_interval_map() -> dict[str, float]:
    return _interval_cache


def _fetch_json(url: str):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def discover_aster() -> tuple[dict[str, str], dict[str, float]]:
    """Fetch Aster's USDT-margined perp universe.

    Aster is Binance-fapi compatible — native symbol == canonical (`BTCUSDT`).
    Funding interval is NOT on the mark-price WS, so we pull it from
    `/fapi/v3/fundingInfo` at discovery and cache per-symbol.

    Returns ({canonical: native}, {canonical: funding_interval_h}).
    """
    try:
        info = _fetch_json(EXCHANGE_INFO_URL)
    except Exception as e:
        logger.error(f"Aster exchangeInfo failed: {e}")
        return {}, {}

    natives: dict[str, str] = {}
    for s in info.get("symbols") or []:
        if (
            s.get("contractType") == "PERPETUAL"
            and s.get("status") == "TRADING"
            and s.get("quoteAsset") == "USDT"
        ):
            sym = s.get("symbol")
            if sym:
                natives[sym] = sym

    intervals: dict[str, float] = {}
    try:
        funding = _fetch_json(FUNDING_INFO_URL)
        for row in funding or []:
            sym = row.get("symbol")
            if not sym or sym not in natives:
                continue
            try:
                intervals[sym] = float(row.get("fundingIntervalHours") or 8)
            except (TypeError, ValueError):
                intervals[sym] = 8.0
    except Exception as e:
        logger.warning(f"Aster fundingInfo failed (will default 8h): {e}")

    return natives, intervals
