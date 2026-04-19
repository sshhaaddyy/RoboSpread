import { useEffect, useState } from "react";

const API_URL = "http://localhost:8000/api/exchanges";

// Module-level cache so a component mount race doesn't re-fetch.
let cached = null;
let inflight = null;

export function useExchanges() {
  const [exchanges, setExchanges] = useState(cached);

  useEffect(() => {
    if (cached) return;
    if (!inflight) {
      inflight = fetch(API_URL)
        .then((r) => r.json())
        .catch((e) => {
          console.error("[exchanges] fetch failed:", e);
          return {};
        });
    }
    let active = true;
    inflight.then((data) => {
      cached = data;
      if (active) setExchanges(data);
    });
    return () => {
      active = false;
    };
  }, []);

  return exchanges || {};
}
