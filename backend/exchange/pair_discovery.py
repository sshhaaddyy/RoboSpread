import json
import logging
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import ccxt

from config import EXCHANGES, MIN_EXCHANGES_PER_PAIR
from exchange.bitget_discovery import discover_bitget, _set_interval_cache as _bitget_set_intervals
from exchange.gate_discovery import discover_gate, _set_caches as _gate_set_caches
from exchange.mexc_discovery import discover_mexc
from exchange.aster_discovery import discover_aster, _set_interval_cache as _aster_set_intervals
from exchange.okx_discovery import discover_okx
from exchange.kucoin_discovery import discover_kucoin, _set_caches as _kucoin_set_caches
from exchange.bingx_discovery import discover_bingx
from exchange.whitebit_discovery import discover_whitebit

logger = logging.getLogger(__name__)


def _discover_binance() -> dict[str, str]:
    """Return {canonical_symbol: native_symbol}. Binance native == canonical."""
    client = ccxt.binance({"options": {"defaultType": "future"}})
    markets = client.load_markets()
    out: dict[str, str] = {}
    for m in markets.values():
        if (
            m.get("linear")
            and m.get("active")
            and m.get("settle") == "USDT"
            and m.get("type") == "swap"
        ):
            out[m["id"]] = m["id"]  # "BTCUSDT"
    return out


def _discover_bybit() -> dict[str, str]:
    """Return {canonical_symbol: native_symbol}. Bybit native == canonical."""
    client = ccxt.bybit({"options": {"defaultType": "future"}})
    markets = client.load_markets()
    out: dict[str, str] = {}
    for m in markets.values():
        if (
            m.get("linear")
            and m.get("active")
            and m.get("settle") == "USDT"
            and m.get("type") == "swap"
        ):
            out[m["id"]] = m["id"]
    return out


def _hl_canonical_from_native(native: str) -> str:
    """Convert a Hyperliquid coin name to canonical Binance-style symbol.

    Hyperliquid uses a `k` prefix for 1000x supply wrappers (kPEPE, kSHIB).
    Binance/Bybit use `1000PEPE`, so map `kXXX` -> `1000XXX`.
    """
    if len(native) > 1 and native[0] == "k" and native[1].isupper():
        return "1000" + native[1:] + "USDT"
    return native + "USDT"


def _discover_hyperliquid() -> dict[str, str]:
    """Fetch Hyperliquid's perp universe directly (ccxt drops the k-prefix).

    Returns {canonical_symbol: native_coin_name}, e.g. "1000PEPEUSDT" -> "kPEPE".
    Only USDC-settled perps are returned — HL also lists USDH/USDE/USDT0-settled
    variants, which we treat as separate venues and ignore for now.
    """
    url = EXCHANGES["hyperliquid"]["info_url"]
    req = urllib.request.Request(
        url,
        data=json.dumps({"type": "meta"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        logger.error(f"Hyperliquid meta fetch failed: {e}")
        return {}

    out: dict[str, str] = {}
    for coin in data.get("universe", []):
        if coin.get("isDelisted"):
            continue
        native = coin.get("name")
        if not native:
            continue
        canonical = _hl_canonical_from_native(native)
        out[canonical] = native
    return out


def _discover_bitget_wrapped() -> dict[str, str]:
    natives, intervals = discover_bitget()
    _bitget_set_intervals(intervals)
    return natives


def _discover_gate_wrapped() -> dict[str, str]:
    natives, intervals, next_applies = discover_gate()
    _gate_set_caches(intervals, next_applies)
    return natives


def _discover_aster_wrapped() -> dict[str, str]:
    natives, intervals = discover_aster()
    _aster_set_intervals(intervals)
    return natives


def _discover_kucoin_wrapped() -> dict[str, str]:
    natives, intervals, next_applies = discover_kucoin()
    _kucoin_set_caches(intervals, next_applies)
    return natives


_DISCOVERY_FUNCS = {
    "binance": _discover_binance,
    "bybit": _discover_bybit,
    "hyperliquid": _discover_hyperliquid,
    "bitget": _discover_bitget_wrapped,
    "gate": _discover_gate_wrapped,
    "mexc": discover_mexc,
    "aster": _discover_aster_wrapped,
    "okx": discover_okx,
    "kucoin": _discover_kucoin_wrapped,
    "bingx": discover_bingx,
    "whitebit": discover_whitebit,
}


def discover_pairs() -> tuple[list[str], dict[str, dict[str, str]]]:
    """Return (common_canonical_symbols, per_exchange_native_map).

    A symbol is included if it is listed on at least MIN_EXCHANGES_PER_PAIR venues.
    per_exchange_native_map[exchange_id][canonical] = native_symbol.
    """
    logger.info("Discovering perp universes across %d exchanges (parallel)...", len(EXCHANGES))
    t0 = time.time()

    def _run_one(ex_id: str) -> tuple[str, dict[str, str]]:
        fn = _DISCOVERY_FUNCS.get(ex_id)
        if not fn:
            logger.warning("No discovery function for %s, skipping", ex_id)
            return ex_id, {}
        try:
            return ex_id, fn()
        except Exception as e:
            logger.error("  %s discovery failed: %s", ex_id, e)
            return ex_id, {}

    exchange_maps: dict[str, dict[str, str]] = {}
    with ThreadPoolExecutor(max_workers=len(EXCHANGES) or 1) as pool:
        for ex_id, natives in pool.map(_run_one, list(EXCHANGES.keys())):
            exchange_maps[ex_id] = natives
            logger.info("  %s: %d perps", ex_id, len(natives))
    logger.info("Discovery complete in %.1fs", time.time() - t0)

    counter: Counter = Counter()
    for m in exchange_maps.values():
        counter.update(m.keys())

    common = sorted(s for s, n in counter.items() if n >= MIN_EXCHANGES_PER_PAIR)

    per_ex = {
        ex: {s: m[s] for s in common if s in m}
        for ex, m in exchange_maps.items()
    }

    logger.info(
        "Found %d symbols listed on %d+ exchanges (union across %d venues)",
        len(common),
        MIN_EXCHANGES_PER_PAIR,
        len(exchange_maps),
    )
    return common, per_ex


# Backwards-compat shim; keep while callers migrate.
def discover_common_pairs() -> list[str]:
    symbols, _ = discover_pairs()
    return symbols
