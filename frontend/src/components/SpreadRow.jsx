import { memo } from "react";
import { formatPct, formatPrice, formatFunding } from "../utils/format";
import { inOutFromRoute } from "../utils/routes";

function statusClass(v) {
  if (v === true) return "status-badge ok";
  if (v === false) return "status-badge bad";
  return "status-badge unknown";
}

function StatusCell({ label, exchangeKey, status }) {
  if (!status) {
    return (
      <div className="status-cell">
        <span className="status-ex-label">{label}</span>
        <span className="status-badge unknown">D</span>
        <span className="status-badge unknown">W</span>
      </div>
    );
  }
  const dep = status[`${exchangeKey}_deposit`];
  const wd = status[`${exchangeKey}_withdraw`];
  return (
    <div className="status-cell">
      <span className="status-ex-label">{label}</span>
      <span className={statusClass(dep)} title={`Deposit ${dep === true ? "open" : dep === false ? "closed" : "unknown"}`}>D</span>
      <span className={statusClass(wd)} title={`Withdraw ${wd === true ? "open" : wd === false ? "closed" : "unknown"}`}>W</span>
    </div>
  );
}

const SpreadRow = memo(function SpreadRow({ pair, flipped, onClick }) {
  const route = pair.best_arb_route;
  if (!route) return null;

  const legs = pair.legs || {};
  const bnLeg = legs.binance;
  const bbLeg = legs.bybit;

  const edge = route.instant_edge_pct;
  const isHot = Math.abs(edge) >= 5;
  const isWarm = Math.abs(edge) >= 2;

  const { inVal, outVal } = inOutFromRoute(legs, route, flipped);

  const fundingApr = flipped ? -route.funding_apr_pct : route.funding_apr_pct;

  return (
    <tr
      className={`spread-row ${isHot ? "hot" : isWarm ? "warm" : ""} ${pair.is_stale ? "stale" : ""}`}
      onClick={() => onClick(pair.symbol)}
    >
      <td className="symbol">{pair.symbol}</td>
      <td>{formatPrice(bnLeg?.mark_price)}</td>
      <td>{formatPrice(bbLeg?.mark_price)}</td>
      <td className={edge > 0 ? "positive" : "negative"}>
        {formatPct(edge)}
      </td>
      <td className={inVal > 0 ? "positive" : "negative"}>
        {formatPct(inVal)}
      </td>
      <td className={outVal > 0 ? "positive" : "negative"}>
        {formatPct(outVal)}
      </td>
      <td>{formatFunding(bnLeg?.funding_rate)}</td>
      <td>{formatFunding(bbLeg?.funding_rate)}</td>
      <td className={fundingApr > 0 ? "positive" : "negative"}>
        {formatPct(fundingApr)}
      </td>
      <td>
        <div className="status-cell-group">
          <StatusCell label="BN" exchangeKey="binance" status={pair.coin_status} />
          <StatusCell label="BB" exchangeKey="bybit" status={pair.coin_status} />
        </div>
      </td>
      <td>{pair.is_stale ? "STALE" : "LIVE"}</td>
    </tr>
  );
});

export default SpreadRow;
