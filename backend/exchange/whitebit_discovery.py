import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

FUTURES_URL = "https://whitebit.com/api/v4/public/futures"


def _native_to_canonical(stock_currency: str) -> str:
    # WhiteBIT uses <BASE>_PERP naming with separate stock_currency and
    # money_currency fields. BASE already matches Binance's 1000-prefix
    # convention (1000PEPE_PERP, 1000SHIB_PERP), so canonical = <BASE>USDT.
    return stock_currency + "USDT"


def discover_whitebit() -> dict[str, str]:
    """Return {canonical: native} for WhiteBIT USDT-margined perps."""
    req = urllib.request.Request(
        FUTURES_URL,
        method="GET",
        headers={"User-Agent": "Mozilla/5.0 RoboSpread/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        logger.error(f"WhiteBIT discovery failed: {e}")
        return {}

    if not payload.get("success"):
        logger.error(f"WhiteBIT discovery returned success=false: {payload.get('message')}")
        return {}

    items = payload.get("result") or []
    natives: dict[str, str] = {}
    for c in items:
        if c.get("product_type") != "Perpetual":
            continue
        if c.get("money_currency") != "USDT":
            continue
        stock = c.get("stock_currency") or ""
        native = c.get("ticker_id") or ""
        if not stock or not native:
            continue
        canonical = _native_to_canonical(stock)
        natives[canonical] = native

    logger.info(f"WhiteBIT discovery: {len(natives)} perps")
    return natives
