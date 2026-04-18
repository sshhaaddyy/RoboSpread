import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import WebSocket

from config import HOST, PORT
from exchange.pair_discovery import discover_common_pairs
from exchange.binance_ws import BinanceWS
from exchange.bybit_ws import BybitWS
from engine.state import state
from api.ws_handler import ws_endpoint, setup_ws_push
from exchange.history import fetch_historical_spread

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="RoboSpread")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    logger.info("Starting RoboSpread...")

    # Discover common pairs
    common_pairs = discover_common_pairs()
    state.init_pairs(common_pairs)
    logger.info(f"Initialized {len(common_pairs)} pairs. First 10: {common_pairs[:10]}")

    # Start exchange WebSocket connections
    binance_ws = BinanceWS(common_pairs)
    bybit_ws = BybitWS(common_pairs)

    asyncio.create_task(binance_ws.run_forever())
    asyncio.create_task(bybit_ws.run_forever())

    logger.info("Exchange WebSocket tasks started.")

    # Start WebSocket push system for frontend
    setup_ws_push()


@app.get("/api/health")
async def health():
    return {"status": "ok", "pairs": len(state.pairs)}


@app.get("/api/pairs")
async def get_pairs():
    return state.get_all_pairs()


@app.get("/api/history/{symbol}")
async def get_history(symbol: str, timeframe: str = "1m", limit: int = 500):
    """
    Returns historical spread data.
    1s = in-memory live data only (collected since backend started).
    Other timeframes = fetch historical klines from exchanges + merge with live.
    """
    if timeframe == "1s":
        return state.get_history(symbol)

    live_history = state.get_history(symbol)
    historical = await asyncio.to_thread(fetch_historical_spread, symbol, timeframe, limit)

    if historical and live_history:
        last_hist_ts = historical[-1]["timestamp"]
        live_filtered = [p for p in live_history if p["timestamp"] > last_hist_ts]
        return historical + live_filtered

    return historical or live_history


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await ws_endpoint(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
