import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

INSTRUMENTS_URL = "https://www.okx.com/api/v5/public/instruments?instType=SWAP"


def _native_to_canonical(inst_id: str) -> str | None:
    """`BTC-USDT-SWAP` → `BTCUSDT`. Returns None if shape unexpected."""
    parts = inst_id.split("-")
    if len(parts) != 3 or parts[2] != "SWAP":
        return None
    return parts[0] + parts[1]


def _fetch() -> list[dict]:
    req = urllib.request.Request(
        INSTRUMENTS_URL,
        method="GET",
        headers={"User-Agent": "Mozilla/5.0 RoboSpread/1.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read())
    if payload.get("code") != "0":
        raise RuntimeError(f"OKX instruments error: {payload}")
    return payload.get("data") or []


def discover_okx() -> dict[str, str]:
    """Fetch OKX USDT-margined linear SWAP universe.

    Returns {canonical: native}, e.g. {"BTCUSDT": "BTC-USDT-SWAP"}.

    OKX's instruments endpoint does NOT publish funding interval — the field
    is only derivable from the `funding-rate` WS stream (fundingTime minus
    prevFundingTime). The connector seeds its own interval cache lazily on
    the first funding-rate push per symbol. Until then, `default_funding_
    interval_h = 8.0` from EXCHANGES["okx"] is used, which is correct for
    the vast majority of OKX perps.
    """
    try:
        instruments = _fetch()
    except Exception as e:
        logger.error(f"OKX discovery failed: {e}")
        return {}

    out: dict[str, str] = {}
    for inst in instruments:
        if inst.get("state") != "live":
            continue
        if inst.get("ctType") != "linear":
            continue
        if inst.get("settleCcy") != "USDT":
            continue
        native = inst.get("instId")
        if not native:
            continue
        canonical = _native_to_canonical(native)
        if not canonical:
            continue
        out[canonical] = native
    return out
