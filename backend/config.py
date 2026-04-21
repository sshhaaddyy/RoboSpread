# ─────────────────────────────────────────────────────────────────
# Exchange registry — single source of truth for fees, WS URLs,
# funding intervals, and display metadata. New exchanges register here.
# ─────────────────────────────────────────────────────────────────
# Every exchange entry MUST carry a non-empty `fee_source_url` citing the
# public page the maker_fee/taker_fee were copied from. Enforced at import
# time by ExchangeWS.__init_subclass__ — see backend/exchange/base.py.
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
        "fee_source_url": "https://www.binance.com/en/fee/futureFee",
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
        "fee_source_url": "https://www.bybit.com/en/help-center/article/Trading-Fee-Structure",
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
        "fee_source_url": "https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees",
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
        "fee_source_url": "https://www.bitget.com/contract-fee",
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
        "fee_source_url": "https://www.gate.io/fee",
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
        "fee_source_url": "https://www.mexc.com/fee",
        "default_funding_interval_h": 8.0,
        "ws_url": "wss://contract.mexc.com/edge",
    },
    "aster": {
        "id": "aster",
        "name": "Aster Futures",
        "short_name": "Aster",
        "icon": "https://assets.coingecko.com/markets/images/1830/small/aster.png",
        "color": "#ff6b35",
        "letter": "A",
        "maker_fee": 0.01,
        "taker_fee": 0.035,
        "fee_source_url": "https://docs.asterdex.com",
        "default_funding_interval_h": 8.0,
        "ws_url": "wss://fstream.asterdex.com/stream?streams=!markPrice@arr@1s",
    },
    "okx": {
        "id": "okx",
        "name": "OKX Futures",
        "short_name": "OKX",
        "icon": "https://assets.coingecko.com/markets/images/96/small/WeChat_Image_20220117220452.png",
        "color": "#3186ff",
        "letter": "O",
        "maker_fee": 0.02,
        "taker_fee": 0.05,
        "fee_source_url": "https://www.okx.com/fees-trading",
        "default_funding_interval_h": 8.0,
        "ws_url": "wss://ws.okx.com:8443/ws/v5/public",
    },
    "kucoin": {
        "id": "kucoin",
        "name": "KuCoin Futures",
        "short_name": "KuCoin",
        "icon": "https://assets.coingecko.com/markets/images/61/small/kucoin.png",
        "color": "#01bc8d",
        "letter": "K",
        "maker_fee": 0.02,
        "taker_fee": 0.06,
        "fee_source_url": "https://www.kucoin.com/vip/privilege",
        "default_funding_interval_h": 4.0,  # most common on KuCoin; per-symbol cached
        "ws_url": "",  # dynamic — resolved via POST /bullet-public at connect time
    },
    "bingx": {
        "id": "bingx",
        "name": "BingX Futures",
        "short_name": "BingX",
        "icon": "https://assets.coingecko.com/markets/images/787/small/bingx.jpg",
        "color": "#2a5ada",
        "letter": "Bx",
        "maker_fee": 0.02,
        "taker_fee": 0.05,
        "fee_source_url": "https://bingx.com/en/support/articles/360016559759",
        "default_funding_interval_h": 8.0,
        "ws_url": "https://open-api.bingx.com/openApi/swap/v2/quote/premiumIndex",  # REST-poll (Archetype 5)
    },
    "whitebit": {
        "id": "whitebit",
        "name": "WhiteBIT Futures",
        "short_name": "WhiteBIT",
        "icon": "https://assets.coingecko.com/markets/images/388/small/whitebit.jpg",
        "color": "#4878ff",
        "letter": "W",
        "maker_fee": 0.01,
        "taker_fee": 0.055,
        "fee_source_url": "https://blog.whitebit.com/en/whitebit-trading-fee/",
        "default_funding_interval_h": 8.0,
        "ws_url": "https://whitebit.com/api/v4/public/futures",  # REST-poll (Archetype 5)
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
