# Exchange WebSocket URLs
BINANCE_WS_URL = "wss://fstream.binance.com/stream?streams=!markPrice@arr@1s"
BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/linear"

# Taker fees (percentage)
BINANCE_TAKER_FEE = 0.04
BYBIT_TAKER_FEE = 0.055

# Round-trip fee: open on both exchanges + close on both exchanges
ROUND_TRIP_FEE = 2 * (BINANCE_TAKER_FEE + BYBIT_TAKER_FEE)  # 0.19%

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
