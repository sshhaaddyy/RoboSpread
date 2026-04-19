# ─────────────────────────────────────────────────────────────────
# Exchange registry — single source of truth for fees, WS URLs,
# funding intervals, and display metadata. New exchanges register here.
# ─────────────────────────────────────────────────────────────────
EXCHANGES: dict[str, dict] = {
    "binance": {
        "id": "binance",
        "name": "Binance Futures",
        "short_name": "Binance",
        "icon": "https://assets.coingecko.com/markets/images/52/small/binance.jpg",
        "color": "#f0b90b",
        "letter": "B",
        "maker_fee": 0.02,
        "taker_fee": 0.04,
        "default_funding_interval_h": 8.0,
        "ws_url": "wss://fstream.binance.com/stream?streams=!markPrice@arr@1s",
    },
    "bybit": {
        "id": "bybit",
        "name": "Bybit Futures",
        "short_name": "Bybit",
        "icon": "https://assets.coingecko.com/markets/images/698/small/bybit_spot.png",
        "color": "#f7a600",
        "letter": "By",
        "maker_fee": 0.01,
        "taker_fee": 0.055,
        "default_funding_interval_h": 8.0,
        "ws_url": "wss://stream.bybit.com/v5/public/linear",
    },
    "hyperliquid": {
        "id": "hyperliquid",
        "name": "Hyperliquid",
        "short_name": "Hyperliquid",
        "icon": "https://assets.coingecko.com/markets/images/1131/small/hyperliquid.png",
        "color": "#97fce4",
        "letter": "H",
        "maker_fee": 0.01,
        "taker_fee": 0.035,
        "default_funding_interval_h": 1.0,
        "ws_url": "wss://api.hyperliquid.xyz/ws",
        "info_url": "https://api.hyperliquid.xyz/info",
    },
    "bitget": {
        "id": "bitget",
        "name": "Bitget Futures",
        "short_name": "Bitget",
        "icon": "https://assets.coingecko.com/markets/images/540/small/bitget_logo.jpg",
        "color": "#00f0ff",
        "letter": "Bg",
        "maker_fee": 0.02,
        "taker_fee": 0.06,
        "default_funding_interval_h": 8.0,
        "ws_url": "wss://ws.bitget.com/v2/ws/public",
    },
    "gate": {
        "id": "gate",
        "name": "Gate Futures",
        "short_name": "Gate",
        "icon": "https://assets.coingecko.com/markets/images/60/small/gate_io_logo.jpg",
        "color": "#2cb9e8",
        "letter": "G",
        "maker_fee": 0.02,
        "taker_fee": 0.05,
        "default_funding_interval_h": 8.0,
        "ws_url": "wss://fx-ws.gateio.ws/v4/ws/usdt",
    },
    "mexc": {
        "id": "mexc",
        "name": "MEXC Futures",
        "short_name": "MEXC",
        "icon": "https://assets.coingecko.com/markets/images/409/small/mexc-logo.png",
        "color": "#00b897",
        "letter": "M",
        "maker_fee": 0.00,
        "taker_fee": 0.02,
        "default_funding_interval_h": 8.0,
        "ws_url": "wss://contract.mexc.com/edge",
    },
}

# Minimum number of exchanges a symbol must be listed on to be tracked.
# Start at 2 while we have 3 venues; raise once there are more to cut noise.
MIN_EXCHANGES_PER_PAIR = 2

# Hyperliquid funding poll interval (funding only changes hourly, so 30s is plenty)
HYPERLIQUID_FUNDING_POLL_SEC = 30


def round_trip_fee_pct(long_ex: str, short_ex: str) -> float:
    """Total fees for opening + closing a long/short pair using taker on both legs."""
    return 2 * (EXCHANGES[long_ex]["taker_fee"] + EXCHANGES[short_ex]["taker_fee"])


# Alert threshold (spread %)
ALERT_THRESHOLD = 5.0

# Spread history: max data points per symbol (1 per second)
HISTORY_MAX_LEN = 3600  # 1 hour

# Staleness: mark pair as stale if no update for this many seconds
STALE_THRESHOLD_SEC = 10

# Bybit subscription batch size and delay
BYBIT_SUB_BATCH_SIZE = 10
BYBIT_SUB_BATCH_DELAY = 0.05  # seconds between batches
BYBIT_PING_INTERVAL = 20  # seconds

# WebSocket reconnection
WS_RECONNECT_BASE_DELAY = 1  # seconds
WS_RECONNECT_MAX_DELAY = 30  # seconds

# Frontend push throttle
FRONTEND_PUSH_INTERVAL = 0.5  # seconds

# Server
HOST = "0.0.0.0"
PORT = 8000
