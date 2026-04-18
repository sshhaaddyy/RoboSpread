import { useEffect, useRef, useState } from "react";
import { createChart, LineSeries } from "lightweight-charts";

export default function SpreadChart({ history, symbol, liveData, flipped, isLive }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesInRef = useRef(null);
  const seriesOutRef = useRef(null);
  const lastTimeRef = useRef(0);
  const readyRef = useRef(false);
  const [error, setError] = useState(null);

  // Create chart
  useEffect(() => {
    if (!containerRef.current) return;

    lastTimeRef.current = 0;
    readyRef.current = false;
    setError(null);

    try {
      const chart = createChart(containerRef.current, {
        layout: {
          background: { color: "#10101c" },
          textColor: "#4a4a5e",
          fontFamily: "'Geist Mono', 'JetBrains Mono', monospace",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "rgba(255, 255, 255, 0.03)" },
          horzLines: { color: "rgba(255, 255, 255, 0.03)" },
        },
        width: containerRef.current.clientWidth,
        height: 400,
        timeScale: {
          timeVisible: true,
          secondsVisible: true,
          rightOffset: 5,
          borderColor: "rgba(255, 255, 255, 0.04)",
        },
        rightPriceScale: {
          borderColor: "rgba(255, 255, 255, 0.04)",
        },
        crosshair: {
          mode: 0,
          vertLine: {
            color: "rgba(99, 102, 241, 0.3)",
            labelBackgroundColor: "#6366f1",
          },
          horzLine: {
            color: "rgba(99, 102, 241, 0.3)",
            labelBackgroundColor: "#6366f1",
          },
        },
      });

      const seriesOut = chart.addSeries(LineSeries, {
        color: "#ef4444",
        lineWidth: 2,
        title: "Out",
        priceFormat: { type: "custom", formatter: (v) => v.toFixed(3) + "%" },
      });

      const seriesIn = chart.addSeries(LineSeries, {
        color: "#22c55e",
        lineWidth: 2,
        title: "In",
        priceFormat: { type: "custom", formatter: (v) => v.toFixed(3) + "%" },
      });

      chartRef.current = chart;
      seriesInRef.current = seriesIn;
      seriesOutRef.current = seriesOut;

      const handleResize = () => {
        if (containerRef.current && chartRef.current) {
          chart.applyOptions({ width: containerRef.current.clientWidth });
        }
      };
      window.addEventListener("resize", handleResize);

      return () => {
        window.removeEventListener("resize", handleResize);
        chartRef.current = null;
        seriesInRef.current = null;
        seriesOutRef.current = null;
        readyRef.current = false;
        try { chart.remove(); } catch (_) {}
      };
    } catch (e) {
      console.error("Chart creation error:", e);
      setError(e.message);
    }
  }, []);

  // Load history data
  useEffect(() => {
    if (!seriesInRef.current || !history || history.length === 0) return;

    try {
      const seen = new Set();
      const clean = history
        .filter((h) => {
          const t = Math.floor(h.timestamp);
          if (seen.has(t)) return false;
          seen.add(t);
          return true;
        })
        .sort((a, b) => a.timestamp - b.timestamp);

      const inData = clean.map((h) => ({
        time: Math.floor(h.timestamp),
        value: flipped ? h.spread_ab : h.spread_ba,
      }));
      const outData = clean.map((h) => ({
        time: Math.floor(h.timestamp),
        value: flipped ? h.spread_ba : h.spread_ab,
      }));

      if (inData.length === 0) return;

      seriesInRef.current.setData(inData);
      seriesOutRef.current.setData(outData);
      lastTimeRef.current = inData[inData.length - 1].time;
      readyRef.current = true;

      // Zero line
      seriesOutRef.current.createPriceLine({
        price: 0,
        color: "rgba(255, 255, 255, 0.08)",
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: false,
      });

      chartRef.current?.timeScale().fitContent();
    } catch (e) {
      console.error("Chart setData error:", e);
    }
  }, [history, flipped]);

  // Live updates (always active for 1s, append for others)
  useEffect(() => {
    if (!seriesInRef.current || !liveData?.spread) return;
    if (!readyRef.current) return;

    try {
      const time = Math.floor(Date.now() / 1000);
      if (time <= lastTimeRef.current) return;
      lastTimeRef.current = time;

      const inVal = flipped ? liveData.spread.spread_ab : liveData.spread.spread_ba;
      const outVal = flipped ? liveData.spread.spread_ba : liveData.spread.spread_ab;

      seriesInRef.current.update({ time, value: inVal });
      seriesOutRef.current.update({ time, value: outVal });
    } catch (_) {}
  }, [liveData, flipped]);

  if (error) {
    return <div className="chart-loading">Chart error: {error}</div>;
  }

  return (
    <div className="spread-chart">
      <div className="chart-legend">
        <span className="legend-red">Out</span>
        <span className="legend-green">In</span>
      </div>
      <div ref={containerRef} className="chart-container" />
    </div>
  );
}
