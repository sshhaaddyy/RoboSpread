import { useEffect, useState, useRef } from "react";
import { formatPrice, formatFunding, formatPct } from "../utils/format";
import { rawSpread } from "../utils/routes";
import { useExchanges } from "../hooks/useExchanges";
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

function ExchangeIcon({ meta }) {
  const [errored, setErrored] = useState(false);
  if (!meta) return null;

  if (errored || !meta.icon) {
    return (
      <span
        className="exchange-icon-badge"
        style={{ background: meta.color || "#555" }}
      >
        {meta.letter || "?"}
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

function DirectionLabel({ longEx, shortEx, exchanges }) {
  const longName = exchanges[longEx]?.name || longEx;
  const shortName = exchanges[shortEx]?.name || shortEx;
  return (
    <span className="dir-label">
      <span className="dir-long">
        <DirectionArrow isLong={true} />
        Long {longName}
      </span>
      <span className="dir-separator"> / </span>
      <span className="dir-short">
        <DirectionArrow isLong={false} />
        Short {shortName}
      </span>
    </span>
  );
}

function ExchangeBox({ exchangeKey, leg, isLong, meta }) {
  const resolved = meta || { name: exchangeKey };
  return (
    <div className="exchange-box">
      <div className="exchange-box-header">
        <span className={isLong ? "dir-long" : "dir-short"}>
          <DirectionArrow isLong={isLong} />
        </span>
        <ExchangeIcon meta={resolved} />
        <h3>{resolved.name}</h3>
      </div>
      <div className="box-row">
        <span>Mark Price</span>
        <span>{formatPrice(leg?.mark_price)}</span>
      </div>
      <div className="box-row">
        <span>Funding Rate</span>
        <span>{formatFunding(leg?.funding_rate)}</span>
      </div>
      <FundingCountdown
        nextFundingTime={leg?.next_funding_time}
        intervalH={leg?.funding_interval_h}
      />
    </div>
  );
}

function LegsStrip({ legs, exchanges }) {
  const entries = Object.entries(legs || {});
  if (entries.length === 0) return null;
  return (
    <div className="legs-strip">
      {entries.map(([ex, leg]) => {
        const meta = exchanges[ex] || { name: ex, letter: ex[0]?.toUpperCase() };
        const stale = leg.is_stale;
        return (
          <div key={ex} className={`legs-strip-chip ${stale ? "stale" : ""}`}>
            <ExchangeIcon meta={meta} />
            <span className="legs-strip-name">{meta.short_name || meta.name || ex}</span>
            <span className="legs-strip-price">{formatPrice(leg.mark_price)}</span>
            <span className="legs-strip-funding">{formatFunding(leg.funding_rate)}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function PairDetail({ symbol, pairData, onBack }) {
  const [history, setHistory] = useState(null);
  const [timeframe, setTimeframe] = useState("5m");
  const [loading, setLoading] = useState(true);
  const [flipped, setFlipped] = useState(false);
  const exchanges = useExchanges();
  const lastPairData = useRef(pairData);
  if (pairData) lastPairData.current = pairData;
  const data = pairData || lastPairData.current;

  useEffect(() => {
    setLoading(true);
    setHistory(null);

    const url =
      timeframe === "1s"
        ? `http://localhost:8000/api/history/${symbol}?timeframe=1s`
        : `http://localhost:8000/api/history/${symbol}?timeframe=${timeframe}&limit=${
            TIMEFRAMES.find((t) => t.value === timeframe)?.limit || 500
          }`;

    fetch(url)
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
  }, [symbol, timeframe]);

  if (!data) return null;

  const route = data.best_arb_route;
  const legs = data.legs || {};
  if (!route) return null;

  const longEx = flipped ? route.short_ex : route.long_ex;
  const shortEx = flipped ? route.long_ex : route.short_ex;

  const outVal = rawSpread(legs, longEx, shortEx);
  const inVal = rawSpread(legs, shortEx, longEx);

  const fundingApr = flipped ? -route.funding_apr_pct : route.funding_apr_pct;
  const instantEdge = route.instant_edge_pct;

  return (
    <div className="pair-detail">
      <div className="detail-header">
        <button onClick={onBack} className="back-btn">Back</button>
        <TokenIcon symbol={symbol} />
        <h2>{symbol}</h2>
        <div className="detail-spread-info">
          <span className="label">Net Spread</span>
          <span className={instantEdge > 0 ? "positive" : "negative"}>
            {formatPct(instantEdge)}
          </span>
        </div>
      </div>

      <div className="detail-direction-bar">
        <DirectionLabel longEx={longEx} shortEx={shortEx} exchanges={exchanges} />
        <button
          className={`flip-btn ${flipped ? "flipped" : ""}`}
          onClick={() => setFlipped(!flipped)}
          title="Flip direction"
        >
          <span className="flip-icon">&#8645;</span>
          Flip
        </button>
      </div>

      <LegsStrip legs={legs} exchanges={exchanges} />

      <div className="detail-columns">
        <div className="detail-col">
          <div className="in-out-box">
            <span className="label">In</span>
            <span className={inVal > 0 ? "positive" : "negative"}>
              {formatPct(inVal)}
            </span>
          </div>
          <ExchangeBox
            exchangeKey={longEx}
            leg={legs[longEx]}
            isLong={true}
            meta={exchanges[longEx]}
          />
        </div>

        <div className="detail-col">
          <div className="in-out-box">
            <span className="label">Out</span>
            <span className={outVal > 0 ? "positive" : "negative"}>
              {formatPct(outVal)}
            </span>
          </div>
          <ExchangeBox
            exchangeKey={shortEx}
            leg={legs[shortEx]}
            isLong={false}
            meta={exchanges[shortEx]}
          />
        </div>
      </div>

      <div className="funding-apr">
        <span className="label">Funding Spread APR</span>
        <span className={fundingApr > 0 ? "positive" : "negative"}>
          {formatPct(fundingApr)}
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
          key={symbol + timeframe + longEx + shortEx}
          history={history || []}
          liveData={data}
          longEx={longEx}
          shortEx={shortEx}
          isLive={timeframe === "1s"}
        />
      )}
    </div>
  );
}
