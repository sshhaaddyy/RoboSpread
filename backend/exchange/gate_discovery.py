import json
import logging
import time
import urllib.request

logger = logging.getLogger(__name__)

CONTRACTS_URL = "https://api.gateio.ws/api/v4/futures/usdt/contracts"


def _native_to_canonical(name: str) -> str:
    """`BTC_USDT` → `BTCUSDT` (identity for the Binance-style convention)."""
    return name.replace("_", "")


def _fetch() -> list[dict]:
    req = urllib.request.Request(CONTRACTS_URL, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def discover_gate() -> tuple[dict[str, str], dict[str, float], dict[str, float]]:
    """Fetch Gate's USDT-margined perp universe.

    Returns:
      ({canonical: native}, {canonical: funding_interval_hours}, {canonical: funding_next_apply_unix_s})

    Gate's WS ticker push only ships `funding_rate` — NOT `funding_interval` or
    `funding_next_apply`. We grab both from REST here and advance the
    next-apply forward algorithmically in the connector.
    """
    try:
        contracts = _fetch()
    except Exception as e:
        logger.error(f"Gate discovery failed: {e}")
        return {}, {}, {}

    natives: dict[str, str] = {}
    intervals: dict[str, float] = {}
    next_applies: dict[str, float] = {}
    for c in contracts:
        name = c.get("name")
        if not name or c.get("in_delisting") or c.get("status") != "trading":
            continue
        canonical = _native_to_canonical(name)
        natives[canonical] = name
        try:
            intervals[canonical] = float(c.get("funding_interval") or 28800) / 3600.0
        except (TypeError, ValueError):
            intervals[canonical] = 8.0
        try:
            next_applies[canonical] = float(c.get("funding_next_apply") or 0)
        except (TypeError, ValueError):
            next_applies[canonical] = 0.0
    return natives, intervals, next_applies


_interval_cache: dict[str, float] = {}
_next_apply_cache: dict[str, float] = {}


def gate_interval_map() -> dict[str, float]:
    return _interval_cache


def current_next_funding(canonical: str, now: float | None = None) -> float | None:
    """Walk the cached funding-next-apply forward by `interval` until it's in
    the future. Updates the cache in place so subsequent ticks are O(1).
    Returns None if we don't have seed data for this symbol."""
    seed = _next_apply_cache.get(canonical)
    interval_h = _interval_cache.get(canonical)
    if not seed or not interval_h:
        return None
    interval_s = interval_h * 3600
    if now is None:
        now = time.time()
    while seed <= now:
        seed += interval_s
    _next_apply_cache[canonical] = seed
    return seed


def _set_caches(intervals: dict[str, float], next_applies: dict[str, float]):
    _interval_cache.clear()
    _interval_cache.update(intervals)
    _next_apply_cache.clear()
    _next_apply_cache.update(next_applies)
