import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

CONTRACTS_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/contracts"


def _native_to_canonical(asset: str) -> str:
    # BingX uses 1000-prefix like Binance (1000PEPE-USDT, 1000SHIB-USDT).
    # The `asset` field is the base currency (e.g. "BTC", "1000PEPE"), so
    # canonical = asset + "USDT".
    return asset + "USDT"


def discover_bingx() -> dict[str, str]:
    """Return {canonical: native} for BingX USDT-margined perps in trading status.

    Does NOT seed a funding-interval cache — BingX's /premiumIndex bulk
    endpoint includes fundingIntervalHours per symbol on every poll, so the
    connector reads it inline.
    """
    req = urllib.request.Request(
        CONTRACTS_URL,
        method="GET",
        headers={"User-Agent": "Mozilla/5.0 RoboSpread/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        logger.error(f"BingX discovery failed: {e}")
        return {}

    items = payload.get("data") or []
    natives: dict[str, str] = {}
    for c in items:
        if c.get("currency") != "USDT":  # quote currency filter
            continue
        if c.get("status") != 1:  # 1 = trading
            continue
        asset = c.get("asset") or ""
        native = c.get("symbol") or ""
        if not asset or not native:
            continue
        canonical = _native_to_canonical(asset)
        natives[canonical] = native

    logger.info(f"BingX discovery: {len(natives)} perps")
    return natives
