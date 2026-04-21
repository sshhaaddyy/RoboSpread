import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

CONTRACTS_URL = "https://api-futures.kucoin.com/api/v1/contracts/active"

_interval_cache: dict[str, float] = {}
_next_apply_cache: dict[str, float] = {}


def _set_caches(intervals: dict[str, float], next_applies: dict[str, float]):
    _interval_cache.clear()
    _interval_cache.update(intervals)
    _next_apply_cache.clear()
    _next_apply_cache.update(next_applies)


def get_interval_h(canonical: str) -> float | None:
    return _interval_cache.get(canonical)


def get_next_funding_time(canonical: str) -> float | None:
    return _next_apply_cache.get(canonical)


def _native_to_canonical(symbol: str, base: str) -> str | None:
    # KuCoin perps are <BASE>USDTM (e.g. XBTUSDTM, ETHUSDTM, 1000BONKUSDTM).
    # KuCoin uses BitMEX-legacy XBT instead of BTC. Everything else matches
    # Binance's 1000-prefix convention.
    if not symbol.endswith("USDTM"):
        return None
    stem = base if base else symbol[: -len("USDTM")]
    if stem == "XBT":
        stem = "BTC"
    return stem + "USDT"


def discover_kucoin() -> tuple[dict[str, str], dict[str, float], dict[str, float]]:
    """Return ({canonical: native}, {canonical: interval_h}, {canonical: next_funding_time_s})."""
    req = urllib.request.Request(
        CONTRACTS_URL,
        method="GET",
        headers={"User-Agent": "Mozilla/5.0 RoboSpread/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        logger.error(f"KuCoin discovery failed: {e}")
        return {}, {}, {}

    items = payload.get("data") or []
    natives: dict[str, str] = {}
    intervals: dict[str, float] = {}
    next_applies: dict[str, float] = {}

    for c in items:
        if c.get("quoteCurrency") != "USDT":
            continue
        if c.get("settleCurrency") != "USDT":
            continue
        if c.get("status") != "Open":
            continue
        if c.get("type") != "FFWCSX":  # FFWCSX = linear perpetual
            continue
        if c.get("isInverse"):
            continue

        native = c.get("symbol")
        base = c.get("baseCurrency") or ""
        canonical = _native_to_canonical(native, base) if native else None
        if not canonical:
            continue

        natives[canonical] = native

        # fundingRateGranularity is in ms; convert to hours
        gran_ms = c.get("fundingRateGranularity")
        if gran_ms:
            try:
                intervals[canonical] = float(gran_ms) / 3_600_000.0
            except (TypeError, ValueError):
                pass

        nft_ms = c.get("nextFundingRateDateTime")
        if nft_ms:
            try:
                next_applies[canonical] = float(nft_ms) / 1000.0
            except (TypeError, ValueError):
                pass

    logger.info(f"KuCoin discovery: {len(natives)} perps")
    return natives, intervals, next_applies
