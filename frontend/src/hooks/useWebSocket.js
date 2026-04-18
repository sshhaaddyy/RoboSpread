import { useEffect, useRef, useState } from "react";

const WS_URL = "ws://localhost:8000/ws";
const RECONNECT_DELAY = 2000;

export function useWebSocket() {
  const wsRef = useRef(null);
  const pairsRef = useRef({});
  const [pairs, setPairs] = useState({});
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      console.log("[WS] Connecting...");
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WS] Connected");
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "snapshot") {
            console.log(`[WS] Snapshot: ${msg.pairs.length} pairs`);
            const map = {};
            for (const p of msg.pairs) map[p.symbol] = p;
            pairsRef.current = map;
            setPairs({ ...map });
          } else if (msg.type === "update") {
            const current = pairsRef.current;
            for (const p of msg.pairs) current[p.symbol] = p;
            setPairs({ ...current });
          }
        } catch (e) {
          console.error("[WS] Parse error:", e);
        }
      };

      ws.onclose = () => {
        console.log("[WS] Disconnected");
        setConnected(false);
        if (!cancelled) setTimeout(connect, RECONNECT_DELAY);
      };

      ws.onerror = () => ws.close();
    }

    connect();

    return () => {
      cancelled = true;
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return { pairs, connected };
}
