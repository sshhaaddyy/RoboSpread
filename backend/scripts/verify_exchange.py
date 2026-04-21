"""
verify_exchange.py — dev-UX helper used by the /verify-exchange skill.

Boots ONE exchange connector in isolation, streams for N seconds, then
reports which fields are populated on BTCUSDT (or first-available symbol).

Usage:
    ./venv/bin/python -m scripts.verify_exchange okx           # 60s default
    ./venv/bin/python -m scripts.verify_exchange gate --seconds 90

Checks:
    • mark_price / funding_rate / funding_interval_h / next_funding_time
      all non-null on BTCUSDT within the window.
    • funding_interval_h not stuck on the default (smells like missing cache).
    • Echoes fee_source_url for human eyeball — if the URL looks generic
      (homepage), go fix it before shipping.
"""
import argparse
import asyncio
import importlib
import logging
import sys
import time

from config import EXCHANGES
from engine.state import state
from exchange.pair_discovery import _DISCOVERY_FUNCS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


_WS_CLASS = {
    "binance": ("exchange.binance_ws", "BinanceWS"),
    "bybit": ("exchange.bybit_ws", "BybitWS"),
    "hyperliquid": ("exchange.hyperliquid_ws", "HyperliquidWS"),
    "bitget": ("exchange.bitget_ws", "BitgetWS"),
    "gate": ("exchange.gate_ws", "GateWS"),
    "mexc": ("exchange.mexc_ws", "MexcWS"),
    "aster": ("exchange.aster_ws", "AsterWS"),
    "okx": ("exchange.okx_ws", "OkxWS"),
    "kucoin": ("exchange.kucoin_ws", "KucoinWS"),
    "bingx": ("exchange.bingx_ws", "BingxWS"),
    "whitebit": ("exchange.whitebit_ws", "WhitebitWS"),
}


def _load_ws_class(exchange_id: str):
    if exchange_id not in _WS_CLASS:
        raise SystemExit(
            f"No WS class registered for {exchange_id!r}. "
            f"Add it to _WS_CLASS in verify_exchange.py."
        )
    mod, cls = _WS_CLASS[exchange_id]
    return getattr(importlib.import_module(mod), cls)


async def _run(exchange_id: str, seconds: int):
    entry = EXCHANGES.get(exchange_id)
    if entry is None:
        raise SystemExit(f"Unknown exchange: {exchange_id}")

    print("━" * 68)
    print(f"Verifying {entry['name']}  ({exchange_id})")
    print(f"  fee_source_url: {entry.get('fee_source_url', '<MISSING>')}")
    print(f"  maker/taker:    {entry.get('maker_fee')}% / {entry.get('taker_fee')}%")
    print(f"  default fih:    {entry.get('default_funding_interval_h')}h")
    print("━" * 68)

    discover = _DISCOVERY_FUNCS.get(exchange_id)
    if discover is None:
        raise SystemExit(f"No discovery fn for {exchange_id}")

    print(f"[1/3] Discovery... ", end="", flush=True)
    t0 = time.time()
    natives = discover()
    print(f"{len(natives)} perps in {time.time() - t0:.1f}s")
    if not natives:
        raise SystemExit("Discovery returned 0 perps — fix discovery first.")

    # Seed pair state so state.update_leg has somewhere to write.
    state.init_pairs({exchange_id: natives})

    WSClass = _load_ws_class(exchange_id)
    connector = WSClass(natives)

    print(f"[2/3] Streaming for {seconds}s...")
    task = asyncio.create_task(connector.run_forever())
    try:
        await asyncio.sleep(seconds)
    finally:
        task.cancel()

    print("[3/3] Checking leg state...")
    sample_canonical = "BTCUSDT" if "BTCUSDT" in natives else next(iter(natives))
    pair = state.pairs.get(sample_canonical)
    leg = pair.legs.get(exchange_id) if pair else None
    if leg is None:
        print(f"  ✗ No leg recorded for {sample_canonical} — connector never fired")
        return 1

    default_fih = entry.get("default_funding_interval_h")
    fih = getattr(leg, "funding_interval_h", None)
    fih_is_default = fih == default_fih

    rows = [
        ("mark_price", leg.mark_price, lambda v: v and v > 0),
        ("funding_rate", leg.funding_rate, lambda v: v is not None),
        ("next_funding_time", leg.next_funding_time, lambda v: v is not None),
        ("funding_interval_h", fih, lambda v: v is not None),
    ]
    ok = True
    print(f"  Sample: {sample_canonical}")
    for k, v, check in rows:
        status = "✓" if check(v) else "✗"
        ok = ok and check(v)
        print(f"    {status} {k} = {v}")

    # Non-default interval sanity
    print()
    off_default_count = sum(
        1 for c, p in state.pairs.items()
        if (p.legs.get(exchange_id)
            and getattr(p.legs[exchange_id], "funding_interval_h", None) not in (None, default_fih))
    )
    total_with_fih = sum(
        1 for c, p in state.pairs.items()
        if p.legs.get(exchange_id)
        and getattr(p.legs[exchange_id], "funding_interval_h", None) is not None
    )
    print(f"  Interval-cache sanity: {off_default_count}/{total_with_fih} symbols off the {default_fih}h default")
    if total_with_fih > 0 and off_default_count == 0:
        print("    ⚠ Every symbol resolved to the default — discovery interval cache likely missing")

    print()
    print("━" * 68)
    print(f"Result: {'PASS' if ok else 'FAIL'}")
    print("━" * 68)
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("exchange", help="Exchange id (e.g. okx)")
    p.add_argument("--seconds", type=int, default=60)
    args = p.parse_args()
    sys.exit(asyncio.run(_run(args.exchange, args.seconds)))


if __name__ == "__main__":
    main()
