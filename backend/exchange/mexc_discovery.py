import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

CONTRACT_DETAIL_URL = "https://contract.mexc.com/api/v1/contract/detail"


def _native_to_canonical(native: str) -> str:
    """`BTC_USDT` → `BTCUSDT` (Binance-style canonical)."""
    return native.replace("_", "")


def _fetch() -> list[dict]:
    req = urllib.request.Request(CONTRACT_DETAIL_URL, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())
    if not payload.get("success"):
        raise RuntimeError(f"MEXC detail error: {payload.get('code')}")
    return payload.get("data") or []


def discover_mexc() -> dict[str, str]:
    """Fetch MEXC's USDT-margined perp universe.

    Returns {canonical: native}, e.g. {"BTCUSDT": "BTC_USDT"}.

    Funding interval and next settlement time are NOT in this endpoint —
    they live on `/api/v1/contract/funding_rate`, which the WS connector
    polls every 30s.
    """
    try:
        contracts = _fetch()
    except Exception as e:
        logger.error(f"MEXC discovery failed: {e}")
        return {}

    out: dict[str, str] = {}
    for c in contracts:
        native = c.get("symbol")
        if not native or c.get("quoteCoin") != "USDT":
            continue
        # state=0 is trading; anything else is paused/pre-market/delisted.
        if c.get("state") != 0:
            continue
        # Skip pre-market / hidden listings — these have no live spot pair yet
        # and typically aren't hedgeable against the other venues.
        if c.get("isHidden") or c.get("preMarket"):
            continue
        out[_native_to_canonical(native)] = native
    return out
