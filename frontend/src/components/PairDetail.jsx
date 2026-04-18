import { useEffect, useState, useRef, useCallback } from "react";
import { formatPrice, formatFunding, formatPct } from "../utils/format";
import SpreadChart from "./SpreadChart";

function useFundingCountdown(nextFundingTimeSec) {
  const [remaining, setRemaining] = useState("");

  useEffect(() => {
    if (!nextFundingTimeSec) {
      setRemaining("");
      return;
    }

    function update() {
      const diff = Math.max(0, Math.floor(nextFundingTimeSec - Date.now() / 1000));
      const h = Math.floor(diff / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      setRemaining(
        `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
      );
    }

    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [nextFundingTimeSec]);

  return remaining;
}

function FundingCountdown({ nextFundingTime, intervalH }) {
  const countdown = useFundingCountdown(nextFundingTime);
  const label = intervalH ? `${intervalH}h` : "";

  if (!countdown) return null;

  return (
    <div className="funding-countdown">
      <span className="funding-interval-tag">{label}</span>
      <span className="funding-timer">{countdown}</span>
    </div>
  );
}

const TIMEFRAMES = [
  { label: "1s", value: "1s", limit: 600 },
  { label: "1m", value: "1m", limit: 500 },
  { label: "5m", value: "5m", limit: 500 },
  { label: "15m", value: "15m", limit: 500 },
  { label: "1h", value: "1h", limit: 500 },
  { label: "4h", value: "4h", limit: 500 },
  { label: "1d", value: "1d", limit: 365 },
];

function getBaseToken(symbol) {
  return symbol.replace(/(USDT|BUSD|USDC|USD)$/i, "").toLowerCase();
}

function TokenIcon({ symbol }) {
  const base = getBaseToken(symbol);
  const [errored, setErrored] = useState(false);

  if (errored) {
    return (
      <span className="token-icon-fallback">
        {base.slice(0, 3).toUpperCase()}
      </span>
    );
  }

  return (
    <img
      className="token-icon"
      src={`https://cdn.jsdelivr.net/gh/nicklatkovich/crypto-icons@master/icons/${base}.png`}
      alt={base}
      onError={() => setErrored(true)}
    />
  );
}

const EXCHANGE_META = {
  binance: {
    name: "Binance Futures",
    icon: "https://assets.coingecko.com/markets/images/52/small/binance.jpg",
    color: "#f0b90b",
    letter: "B",
  },
  bybit: {
    name: "Bybit Futures",
    icon: "https://assets.coingecko.com/markets/images/698/small/bybit_spot.png",
    color: "#f7a600",
    letter: "By",
  },
};

function DirectionArrow({ isLong }) {
  return (
    <svg className="dir-arrow" viewBox="0 0 16 16" width="14" height="14">
      {isLong ? (
        <path d="M8 3 L12 8 L9.5 8 L9.5 13 L6.5 13 L6.5 8 L4 8 Z" fill="currentColor" />
      ) : (
        <path d="M8 13 L12 8 L9.5 8 L9.5 3 L6.5 3 L6.5 8 L4 8 Z" fill="currentColor" />
      )}
    </svg>
  );
}

function ExchangeIcon({ exchangeKey }) {
  const meta = EXCHANGE_META[exchangeKey];
  const [errored, setErrored] = useState(false);
  if (!meta) return null;

  if (errored || !meta.icon) {
    return (
      <span
        className="exchange-icon-badge"
        style={{ background: meta.color }}
      >
        {meta.letter}
      </span>
    );
  }

  return (
    <img
      className="exchange-icon"
      src={meta.icon}
      alt={meta.name}
      onError={() => setErrored(true)}
    />
  );
}

function DirectionLabel({ dirLabel }) {
  const parts = dirLabel.split(" / ");
  return (
    <span className="dir-label">
      {parts.map((part, i) => {
        const isLong = part.startsWith("Long");
        return (
          <span key={i}>
            {i > 0 && <span className="dir-separator"> / </span>}
            <span className={isLong ? "dir-long" : "dir-short"}>
              <DirectionArrow isLong={isLong} />
              {part}
            </span>
          </span>
        );
      })}
    </span>
  );
}

export default function PairDetail({ symbol, pairData, onBack }) {
  const [history, setHistory] = useState(null);
  const [timeframe, setTimeframe] = useState("5m");
  const [loading, setLoading] = useState(true);
  const [flipped, setFlipped] = useState(false);
  const lastPairData = useRef(pairData);
  if (pairData) lastPairData.current = pairData;
  const data = pairData || lastPairData.current;

  useEffect(() => {
    setLoading(true);
    setHistory(null);

    if (timeframe === "1s") {
      fetch(`http://localhost:8000/api/history/${symbol}?timeframe=1s`)
        .then((r) => r.json())
        .then((result) => {
          setHistory(result);
          setLoading(false);
        })
        .catch((e) => {
          console.error("History fetch error:", e);
          setHistory([]);
          setLoading(false);
        });
    } else {
      const tf = TIMEFRAMES.find((t) => t.value === timeframe);
      fetch(`http://localhost:8000/api/history/${symbol}?timeframe=${timeframe}&limit=${tf?.limit || 500}`)
        .then((r) => r.json())
        .then((result) => {
          setHistory(result);
          setLoading(false);
        })
        .catch((e) => {
          console.error("History fetch error:", e);
          setHistory([]);
          setLoading(false);
        });
    }
  }, [symbol, timeframe]);

  if (!data) return null;

  const spread = data.spread;
  const isBn = spread?.best_direction === "long_binance";

  let inVal, outVal, dirLabel, leftExchange, rightExchange, leftIsLong;
  if (!flipped) {
    inVal = isBn ? spread?.spread_ba : spread?.spread_ab;
    outVal = isBn ? spread?.spread_ab : spread?.spread_ba;
    dirLabel = isBn ? "Long Binance / Short Bybit" : "Long Bybit / Short Binance";
    leftExchange = isBn ? "binance" : "bybit";
    rightExchange = isBn ? "bybit" : "binance";
    leftIsLong = true;
  } else {
    inVal = isBn ? spread?.spread_ab : spread?.spread_ba;
    outVal = isBn ? spread?.spread_ba : spread?.spread_ab;
    dirLabel = isBn ? "Long Bybit / Short Binance" : "Long Binance / Short Bybit";
    leftExchange = isBn ? "bybit" : "binance";
    rightExchange = isBn ? "binance" : "bybit";
    leftIsLong = true;
  }

  return (
    <div className="pair-detail">
      <div className="detail-header">
        <button onClick={onBack} className="back-btn">Back</button>
        <TokenIcon symbol={symbol} />
        <h2>{symbol}</h2>
        {spread && (
          <div className="detail-spread-info">
            <span className="label">Net Spread</span>
            <span className={spread.best_net_spread > 0 ? "positive" : "negative"}>
              {formatPct(spread.best_net_spread)}
            </span>
          </div>
        )}
      </div>

      <div className="detail-direction-bar">
        <DirectionLabel dirLabel={dirLabel} />
        <button
          className={`flip-btn ${flipped ? "flipped" : ""}`}
          onClick={() => setFlipped(!flipped)}
          title="Flip direction"
        >
          <span className="flip-icon">&#8645;</span>
          Flip
        </button>
      </div>

      <div className="detail-columns">
        <div className="detail-col">
          <div className="in-out-box">
            <span className="label">In</span>
            <span className={inVal > 0 ? "positive" : "negative"}>
              {formatPct(inVal)}
            </span>
          </div>
          <div className="exchange-box">
            <div className="exchange-box-header">
              <span className={leftIsLong ? "dir-long" : "dir-short"}>
                <DirectionArrow isLong={leftIsLong} />
              </span>
              <ExchangeIcon exchangeKey={leftExchange} />
              <h3>{EXCHANGE_META[leftExchange]?.name || leftExchange}</h3>
            </div>
            <div className="box-row">
              <span>Mark Price</span>
              <span>{formatPrice(data[`price_${leftExchange}`])}</span>
            </div>
            <div className="box-row">
              <span>Funding Rate</span>
              <span>{formatFunding(data[`funding_${leftExchange}`])}</span>
            </div>
            <FundingCountdown
              nextFundingTime={data[`next_funding_time_${leftExchange}`]}
              intervalH={data[`funding_interval_h_${leftExchange}`]}
            />
          </div>
        </div>

        <div className="detail-col">
          <div className="in-out-box">
            <span className="label">Out</span>
            <span className={outVal > 0 ? "positive" : "negative"}>
              {formatPct(outVal)}
            </span>
          </div>
          <div className="exchange-box">
            <div className="exchange-box-header">
              <span className={!leftIsLong ? "dir-long" : "dir-short"}>
                <DirectionArrow isLong={!leftIsLong} />
              </span>
              <ExchangeIcon exchangeKey={rightExchange} />
              <h3>{EXCHANGE_META[rightExchange]?.name || rightExchange}</h3>
            </div>
            <div className="box-row">
              <span>Mark Price</span>
              <span>{formatPrice(data[`price_${rightExchange}`])}</span>
            </div>
            <div className="box-row">
              <span>Funding Rate</span>
              <span>{formatFunding(data[`funding_${rightExchange}`])}</span>
            </div>
            <FundingCountdown
              nextFundingTime={data[`next_funding_time_${rightExchange}`]}
              intervalH={data[`funding_interval_h_${rightExchange}`]}
            />
          </div>
        </div>
      </div>

      <div className="funding-apr">
        <span className="label">Funding Spread APR</span>
        <span className={(flipped ? -data.funding_spread_apr : data.funding_spread_apr) > 0 ? "positive" : "negative"}>
          {formatPct(flipped ? -data.funding_spread_apr : data.funding_spread_apr)}
        </span>
      </div>

      <div className="timeframe-bar">
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf.value}
            className={`tf-btn ${timeframe === tf.value ? "active" : ""}`}
            onClick={() => setTimeframe(tf.value)}
          >
            {tf.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="chart-loading">Loading spread data...</div>
      ) : (
        <SpreadChart
          key={symbol + timeframe + flipped}
          history={history || []}
          symbol={symbol}
          liveData={data}
          flipped={flipped}
          isLive={timeframe === "1s"}
        />
      )}
    </div>
  );
}
