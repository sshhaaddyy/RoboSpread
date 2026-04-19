import { useEffect, useRef, useState } from "react";
import { createChart, LineSeries } from "lightweight-charts";

function spreadFromPrices(prices, longEx, shortEx) {
  const longP = prices?.[longEx];
  const shortP = prices?.[shortEx];
  if (!longP || !shortP) return null;
  return ((shortP - longP) / longP) * 100;
}

export default function SpreadChart({ history, liveData, longEx, shortEx }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesInRef = useRef(null);
  const seriesOutRef = useRef(null);
  const lastTimeRef = useRef(0);
  const readyRef = useRef(false);
  const [error, setError] = useState(null);

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

  useEffect(() => {
    if (!seriesInRef.current || !history || history.length === 0) return;
    if (!longEx || !shortEx) return;

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

      const inData = [];
      const outData = [];
      for (const h of clean) {
        const t = Math.floor(h.timestamp);
        const prices = h.prices || {};
        const outV = spreadFromPrices(prices, longEx, shortEx);
        const inV = spreadFromPrices(prices, shortEx, longEx);
        if (outV !== null) outData.push({ time: t, value: outV });
        if (inV !== null) inData.push({ time: t, value: inV });
      }

      if (inData.length === 0 && outData.length === 0) return;

      seriesInRef.current.setData(inData);
      seriesOutRef.current.setData(outData);
      const lastT =
        Math.max(
          inData.length ? inData[inData.length - 1].time : 0,
          outData.length ? outData[outData.length - 1].time : 0,
        );
      lastTimeRef.current = lastT;
      readyRef.current = true;

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
  }, [history, longEx, shortEx]);

  useEffect(() => {
    if (!seriesInRef.current || !liveData?.legs) return;
    if (!readyRef.current) return;
    if (!longEx || !shortEx) return;

    try {
      const time = Math.floor(Date.now() / 1000);
      if (time <= lastTimeRef.current) return;
      lastTimeRef.current = time;

      const prices = {
        [longEx]: liveData.legs[longEx]?.mark_price,
        [shortEx]: liveData.legs[shortEx]?.mark_price,
      };
      const outV = spreadFromPrices(prices, longEx, shortEx);
      const inV = spreadFromPrices(prices, shortEx, longEx);

      if (inV !== null) seriesInRef.current.update({ time, value: inV });
      if (outV !== null) seriesOutRef.current.update({ time, value: outV });
    } catch (_) {}
  }, [liveData, longEx, shortEx]);

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
