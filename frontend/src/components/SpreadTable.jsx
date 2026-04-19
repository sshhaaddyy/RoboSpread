import { useState, useMemo } from "react";
import SpreadRow from "./SpreadRow";
import { inOutFromRoute } from "../utils/routes";

const COLUMNS = [
  { key: "symbol", label: "Pair" },
  { key: "price_binance", label: "Binance Price" },
  { key: "price_bybit", label: "Bybit Price" },
  { key: "instant_edge", label: "Net Spread" },
  { key: "in", label: "In" },
  { key: "out", label: "Out" },
  { key: "funding_binance", label: "Fund Binance" },
  { key: "funding_bybit", label: "Fund Bybit" },
  { key: "funding_apr", label: "Fund APR" },
  { key: "wallet", label: "Wallet D/W" },
  { key: "status", label: "Status" },
];

function getSortValue(pair, key, flipped) {
  const route = pair.best_arb_route;
  const legs = pair.legs || {};
  switch (key) {
    case "symbol":
      return pair.symbol;
    case "price_binance":
      return legs.binance?.mark_price ?? 0;
    case "price_bybit":
      return legs.bybit?.mark_price ?? 0;
    case "instant_edge":
      return Math.abs(route?.instant_edge_pct ?? 0);
    case "in":
      return inOutFromRoute(legs, route, flipped).inVal;
    case "out":
      return inOutFromRoute(legs, route, flipped).outVal;
    case "funding_binance":
      return legs.binance?.funding_rate ?? 0;
    case "funding_bybit":
      return legs.bybit?.funding_rate ?? 0;
    case "funding_apr":
      return (flipped ? -1 : 1) * (route?.funding_apr_pct ?? 0);
    default:
      return 0;
  }
}

export default function SpreadTable({ pairs, onSelectPair }) {
  const [sortKey, setSortKey] = useState("instant_edge");
  const [sortDesc, setSortDesc] = useState(true);
  const [filter, setFilter] = useState("");
  const [flipped, setFlipped] = useState(false);

  const sortedPairs = useMemo(() => {
    let filtered = pairs;
    if (filter) {
      const f = filter.toUpperCase();
      filtered = pairs.filter((p) => p.symbol.includes(f));
    }
    return [...filtered].sort((a, b) => {
      const va = getSortValue(a, sortKey, flipped);
      const vb = getSortValue(b, sortKey, flipped);
      if (typeof va === "string") {
        return sortDesc ? vb.localeCompare(va) : va.localeCompare(vb);
      }
      return sortDesc ? vb - va : va - vb;
    });
  }, [pairs, sortKey, sortDesc, filter, flipped]);

  const handleSort = (key) => {
    if (key === sortKey) {
      setSortDesc(!sortDesc);
    } else {
      setSortKey(key);
      setSortDesc(true);
    }
  };

  return (
    <div className="spread-table-container">
      <div className="table-header">
        <input
          type="text"
          placeholder="Filter pairs..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="filter-input"
        />
        <div className="table-header-right">
          <button
            className={`flip-btn ${flipped ? "flipped" : ""}`}
            onClick={() => setFlipped(!flipped)}
            title="Flip In/Out direction"
          >
            <span className="flip-icon">&#8645;</span>
            {flipped ? "Reversed" : "Default"}
          </button>
          <span className="pair-count">{sortedPairs.length} pairs</span>
        </div>
      </div>
      <div className="table-scroll">
        <table className="spread-table">
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className={sortKey === col.key ? "sorted" : ""}
                >
                  {col.label}
                  {sortKey === col.key && (sortDesc ? " ▼" : " ▲")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedPairs.map((pair) => (
              <SpreadRow
                key={pair.symbol}
                pair={pair}
                flipped={flipped}
                onClick={onSelectPair}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
