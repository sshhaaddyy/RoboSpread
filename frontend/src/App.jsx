import { useState, useMemo } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import SpreadTable from "./components/SpreadTable";
import PairDetail from "./components/PairDetail";

export default function App() {
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const { pairs, connected } = useWebSocket();

  const pairList = useMemo(() => Object.values(pairs), [pairs]);

  return (
    <div className="app">
      <header className="app-header">
        <h1 onClick={() => setSelectedSymbol(null)} style={{ cursor: "pointer" }}>
          RoboSpread
          <span className="header-tag">v1</span>
        </h1>
        <div className="status">
          <span className={`dot ${connected ? "connected" : "disconnected"}`} />
          {connected ? "Live" : "Reconnecting..."}
          {pairList.length > 0 && ` // ${pairList.length} pairs`}
        </div>
      </header>

      <main>
        {selectedSymbol ? (
          <PairDetail
            symbol={selectedSymbol}
            pairData={pairs[selectedSymbol]}
            onBack={() => setSelectedSymbol(null)}
          />
        ) : (
          <SpreadTable pairs={pairList} onSelectPair={setSelectedSymbol} />
        )}
      </main>
    </div>
  );
}
