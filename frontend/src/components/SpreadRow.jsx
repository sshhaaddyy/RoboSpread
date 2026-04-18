import { memo } from "react";
import { formatPct, formatPrice, formatFunding } from "../utils/format";

const SpreadRow = memo(function SpreadRow({ pair, flipped, onClick }) {
  const spread = pair.spread;
  if (!spread) return null;

  const isHot = Math.abs(spread.best_net_spread) >= 5;
  const isWarm = Math.abs(spread.best_net_spread) >= 2;

  // Default direction: best direction found by spread_calc
  // "In" = entry cost (the spread against you when entering)
  // "Out" = exit cost (the spread when closing)
  const isBn = spread.best_direction === "long_binance";

  // In default mode (Long BN / Short BB):
  //   In = spread_ba (you enter against this spread — typically negative)
  //   Out = spread_ab (you exit capturing this spread — typically positive)
  // Flipped reverses In/Out
  let inVal, outVal;
  if (!flipped) {
    inVal = isBn ? spread.spread_ba : spread.spread_ab;
    outVal = isBn ? spread.spread_ab : spread.spread_ba;
  } else {
    inVal = isBn ? spread.spread_ab : spread.spread_ba;
    outVal = isBn ? spread.spread_ba : spread.spread_ab;
  }

  return (
    <tr
      className={`spread-row ${isHot ? "hot" : isWarm ? "warm" : ""} ${pair.is_stale ? "stale" : ""}`}
      onClick={() => onClick(pair.symbol)}
    >
      <td className="symbol">{pair.symbol}</td>
      <td>{formatPrice(pair.price_binance)}</td>
      <td>{formatPrice(pair.price_bybit)}</td>
      <td className={spread.best_net_spread > 0 ? "positive" : "negative"}>
        {formatPct(spread.best_net_spread)}
      </td>
      <td className={inVal > 0 ? "positive" : "negative"}>
        {formatPct(inVal)}
      </td>
      <td className={outVal > 0 ? "positive" : "negative"}>
        {formatPct(outVal)}
      </td>
      <td>{formatFunding(pair.funding_binance)}</td>
      <td>{formatFunding(pair.funding_bybit)}</td>
      <td className={pair.funding_spread_apr > 0 ? "positive" : "negative"}>
        {formatPct(pair.funding_spread_apr)}
      </td>
      <td>{pair.is_stale ? "STALE" : "LIVE"}</td>
    </tr>
  );
});

export default SpreadRow;
