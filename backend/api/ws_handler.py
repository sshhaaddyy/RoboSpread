import asyncio
import json
import logging
from fastapi import WebSocket, WebSocketDisconnect

from config import FRONTEND_PUSH_INTERVAL
from engine.state import state

logger = logging.getLogger(__name__)

_clients: set[WebSocket] = set()
_pending: dict[str, dict] = {}
_has_updates = asyncio.Event()


async def _push_loop():
    """Push batched updates to all connected clients."""
    global _pending, _clients
    logger.info("Push loop started")

    while True:
        await asyncio.sleep(FRONTEND_PUSH_INTERVAL)

        if not _pending or not _clients:
            continue

        updates = list(_pending.values())
        _pending = {}

        try:
            msg = json.dumps({"type": "update", "pairs": updates})
        except Exception as e:
            logger.error(f"JSON encode error: {e}")
            continue

        dead = set()
        for ws in list(_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)

        if dead:
            _clients -= dead
            logger.info(f"Removed {len(dead)} dead clients. Total: {len(_clients)}")


def _on_pair_update(symbol: str, pair):
    """Called by state on every price update. Just buffers the data."""
    try:
        _pending[symbol] = pair.to_dict()
    except Exception:
        pass


def setup_ws_push():
    """Initialize the push system. Call once on startup."""
    state.on_update(_on_pair_update)
    loop = asyncio.get_event_loop()
    loop.create_task(_push_loop())
    logger.info("WebSocket push system initialized")


async def ws_endpoint(websocket: WebSocket):
    """WebSocket endpoint for frontend clients."""
    await websocket.accept()
    _clients.add(websocket)
    logger.info(f"Client connected. Total: {len(_clients)}")

    try:
        snapshot = state.get_all_pairs()
        await websocket.send_text(json.dumps({"type": "snapshot", "pairs": snapshot}))
        logger.info(f"Sent snapshot: {len(snapshot)} pairs")

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        _clients.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(_clients)}")
