import { useEffect, useState, useRef } from "react";
import {
  ColorType,
  LineStyle,
  createChart,
  type CandlestickData,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type HistogramData,
  type LineData,
  type MouseEventParams,
  type SeriesType,
  type Time,
} from "lightweight-charts";
import { buildVisibleTimeRange } from "../lib/chartRange";
import type { ChartPayload, ThemeMode, TimeRangePreset } from "../types";

type Mode = "candles" | "line";

type Props = {
  title: string;
  mode: Mode;
  themeMode: ThemeMode;
  height?: number;
  singleAxisHover?: boolean;
  showOhlcOnHover?: boolean;
  payload: ChartPayload | null;
  lineKey?: string;
  overlayKeys?: string[];
  leftScaleKeys?: string[];
  leftScaleMargins?: { top: number; bottom: number };
  volumeOverlayKeys?: string[];
  onNeedMoreHistory?: () => void;
  canLoadMoreHistory?: boolean;
  isLoadingMoreHistory?: boolean;
  rangePreset?: TimeRangePreset | null;
};

const lineColors: Record<string, string> = {
  sma_10: "#f43f5e",
  sma_20: "#f59e0b",
  sma_50: "#84cc16",
  sma_100: "#06b6d4",
  sma_150: "#8b5cf6",
  sma_200: "#3b82f6",
  ema_21: "#f97316",
  rs_line: "#0ea5e9",
  benchmark_close: "#f59e0b",
  volume_sma_50: "#fbbf24",
  volume_sma_10: "#38bdf8",
};

const getChartPalette = (themeMode: ThemeMode) => {
  if (themeMode === "paper") {
    return {
      background: "#ffffff",
      textColor: "#3f362a",
      grid: "rgba(120, 103, 82, 0.18)",
    };
  }

  return {
    background: "#0f172a",
    textColor: "#cbd5e1",
    grid: "rgba(148, 163, 184, 0.15)",
  };
};

const isNumber = (value: unknown): value is number => typeof value === "number";

const isCandleSeriesData = (value: unknown): value is { open: number; high: number; low: number; close: number } => {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return (
    isNumber(candidate.open) &&
    isNumber(candidate.high) &&
    isNumber(candidate.low) &&
    isNumber(candidate.close)
  );
};

const isLineSeriesData = (value: unknown): value is { value: number } => {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Record<string, unknown>;
  return isNumber(candidate.value);
};

export default function ChartPanel({
  title,
  mode,
  themeMode,
  height = 360,
  singleAxisHover = false,
  showOhlcOnHover = false,
  payload,
  lineKey,
  overlayKeys = [],
  leftScaleKeys = [],
  leftScaleMargins,
  volumeOverlayKeys = [],
  onNeedMoreHistory,
  canLoadMoreHistory = false,
  isLoadingMoreHistory = false,
  rangePreset = null,
}: Props) {
  type CandlestickSeries = ISeriesApi<"Candlestick", Time>;
  type LineSeries = ISeriesApi<"Line", Time>;
  type AnySeries = ISeriesApi<SeriesType, Time>;
  type CreatedEntry = { kind: "series"; series: AnySeries } | { kind: "priceLine"; series: LineSeries; priceLine: IPriceLine };

  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  const lastHistoryRequestAtRef = useRef(0);
  const lastVisibleFromRef = useRef<number | null>(null);
  const fittedContextKeyRef = useRef<string>("");
  const rangePresetKeyRef = useRef<string>("");
  const isChartDisposedRef = useRef(false);
  const candleSeriesRef = useRef<CandlestickSeries | null>(null);
  const benchmarkSeriesRef = useRef<LineSeries | null>(null);
  const [rsHighInfo, setRsHighInfo] = useState<{ time: string; value: number } | null>(null);
  const [rsHighX, setRsHighX] = useState<number | null>(null);
  const [rsHighInView, setRsHighInView] = useState(false);
  const [axisHover, setAxisHover] = useState<{ y: number; side: "left" | "right"; label: string } | null>(null);
  const [ohlcHover, setOhlcHover] = useState<{ open: string; high: string; low: string; close: string } | null>(null);

  const clearAxisHover = () => setAxisHover(null);
  const formatAxisValue = (value: number) => {
    const abs = Math.abs(value);
    if (abs >= 1000) return value.toFixed(2);
    if (abs >= 1) return value.toFixed(3);
    return value.toFixed(6);
  };
  const formatOhlcValue = (value: number) => {
    const abs = Math.abs(value);
    if (abs >= 1000) return value.toFixed(2);
    if (abs >= 1) return value.toFixed(4);
    return value.toFixed(6);
  };

  useEffect(() => {
    if (!containerRef.current) return;

    isChartDisposedRef.current = false;
    const palette = getChartPalette(themeMode);

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: palette.background },
        textColor: palette.textColor,
      },
      grid: {
        vertLines: { color: palette.grid },
        horzLines: { color: palette.grid },
      },
      width: containerRef.current.clientWidth,
      height,
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
    });

    chartRef.current = chart;

    const resize = () => {
      if (!containerRef.current || isChartDisposedRef.current) return;
      try {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      } catch {
        // chart can already be disposed during route transition cleanup
      }
    };

    window.addEventListener("resize", resize);
    cleanupRef.current = () => {
      window.removeEventListener("resize", resize);
      if (isChartDisposedRef.current) {
        chartRef.current = null;
        return;
      }
      isChartDisposedRef.current = true;
      try {
        chart.remove();
      } catch {
        // already disposed
      }
      chartRef.current = null;
    };

    return cleanupRef.current;
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || isChartDisposedRef.current) return;
    try {
      chart.applyOptions({ height });
    } catch {
      // ignore late height updates during unmount
    }
  }, [height]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || isChartDisposedRef.current) return;

    const useSingleAxisHover = singleAxisHover && mode === "candles";
    try {
      chart.applyOptions({
        crosshair: {
          horzLine: {
            visible: !useSingleAxisHover,
            labelVisible: !useSingleAxisHover,
          },
        },
      });
    } catch {
      // ignore update failures during transitions
    }

    if (!useSingleAxisHover) {
      clearAxisHover();
    }
  }, [singleAxisHover, mode]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || isChartDisposedRef.current) return;

    const palette = getChartPalette(themeMode);
    try {
      chart.applyOptions({
        layout: {
          background: { type: ColorType.Solid, color: palette.background },
          textColor: palette.textColor,
        },
        grid: {
          vertLines: { color: palette.grid },
          horzLines: { color: palette.grid },
        },
      });
    } catch {
      // ignore late theme updates during unmount
    }
  }, [themeMode]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !payload || isChartDisposedRef.current) return;

    const createdSeries: CreatedEntry[] = [];

    if (mode === "candles") {
      candleSeriesRef.current = null;
      benchmarkSeriesRef.current = null;
      const hasLeftScaleOverlay = overlayKeys.some((key) => leftScaleKeys.includes(key));
      try {
        chart.applyOptions({
          leftPriceScale: {
            visible: hasLeftScaleOverlay,
            borderVisible: false,
            scaleMargins: hasLeftScaleOverlay && leftScaleMargins ? leftScaleMargins : undefined,
          },
          rightPriceScale: { borderVisible: false },
        });
      } catch {
        // ignore chart update failures during transitions
      }

      const candles = chart.addCandlestickSeries({
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderUpColor: "#22c55e",
        borderDownColor: "#ef4444",
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      });
      candles.setData(payload.candles as CandlestickData<Time>[]);
      createdSeries.push({ kind: "series", series: candles });
      candleSeriesRef.current = candles;

      const volume = chart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });
      volume.priceScale().applyOptions({ scaleMargins: { top: 0.6, bottom: 0 } });
      volume.setData(payload.volume as HistogramData<Time>[]);
      createdSeries.push({ kind: "series", series: volume });

      volumeOverlayKeys.forEach((key) => {
        const data = payload.indicators[key];
        if (!data || data.length === 0) return;
        const line = chart.addLineSeries({
          color: lineColors[key] ?? "#f8fafc",
          lineWidth: 1,
          priceScaleId: "",
          priceFormat: { type: "volume" },
        });
        line.setData(data as LineData<Time>[]);
        createdSeries.push({ kind: "series", series: line });
      });

      overlayKeys.forEach((key) => {
        const data = payload.indicators[key];
        if (!data || data.length === 0) return;
        const line = chart.addLineSeries({
          color: lineColors[key] ?? "#e2e8f0",
          lineWidth: 1,
          priceScaleId: leftScaleKeys.includes(key) ? "left" : "right",
        });
        line.setData(data as LineData<Time>[]);
        createdSeries.push({ kind: "series", series: line });
        if (key === "benchmark_close") {
          benchmarkSeriesRef.current = line;
        }
      });
    } else if (mode === "line" && lineKey) {
      candleSeriesRef.current = null;
      benchmarkSeriesRef.current = null;
      const data = payload.indicators[lineKey] ?? [];
      const line = chart.addLineSeries({
        color: lineColors[lineKey] ?? "#0ea5e9",
        lineWidth: 2,
        priceFormat:
          lineKey === "rs_line"
            ? {
                type: "price",
                precision: 6,
                minMove: 0.000001,
              }
            : undefined,
      });
      line.setData(data as LineData<Time>[]);

      if (lineKey === "rs_line") {
        const high = payload.meta?.rs_1y_high ?? null;
        setRsHighInfo(high);

        if (high) {
          const highLine = line.createPriceLine({
            price: high.value,
            color: "#fbbf24",
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: "1Y High",
          });
          createdSeries.push({ kind: "priceLine", series: line, priceLine: highLine });
        }
      } else {
        setRsHighInfo(null);
      }

      createdSeries.push({ kind: "series", series: line });
    } else {
      setRsHighInfo(null);
    }

    const fitKey = `${payload.symbol}:${payload.timeframe}`;
    const rangeKey = `${fitKey}:${rangePreset ?? "ALL"}`;
    if (rangePreset === "ALL" || rangePreset === null) {
      if (rangePresetKeyRef.current !== rangeKey) {
        try {
          chart.timeScale().fitContent();
        } catch {
          // chart may be disposed while route changes
        }
        rangePresetKeyRef.current = rangeKey;
        fittedContextKeyRef.current = fitKey;
        lastVisibleFromRef.current = null;
      }
    } else if (rangePresetKeyRef.current !== rangeKey) {
      const visibleRange = buildVisibleTimeRange(payload, rangePreset);
      if (visibleRange) {
        try {
          chart.timeScale().setVisibleRange(visibleRange);
        } catch {
          // chart may be disposed while route changes
        }
      }
      rangePresetKeyRef.current = rangeKey;
      fittedContextKeyRef.current = fitKey;
      lastVisibleFromRef.current = null;
    }

    return () => {
      createdSeries.forEach((series) => {
        if (!chart || isChartDisposedRef.current || !series) return;
        if (series.kind === "priceLine") {
          try {
            series.series.removePriceLine(series.priceLine);
          } catch {
            // already removed/disposed
          }
          return;
        }
        try {
          chart.removeSeries(series.series);
        } catch {
          // already removed/disposed
        }
      });
      candleSeriesRef.current = null;
      benchmarkSeriesRef.current = null;
      clearAxisHover();
      setOhlcHover(null);
    };
  }, [mode, payload, lineKey, overlayKeys, leftScaleKeys, leftScaleMargins, volumeOverlayKeys, rangePreset]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || isChartDisposedRef.current) return;
    if (!(showOhlcOnHover && mode === "candles")) {
      setOhlcHover(null);
      return;
    }

    const onMove = (param: MouseEventParams<Time>) => {
      if (isChartDisposedRef.current) return;
      const point = param?.point;
      if (!point || !containerRef.current) {
        setOhlcHover(null);
        return;
      }

      const candleSeries = candleSeriesRef.current;
      if (!candleSeries) {
        setOhlcHover(null);
        return;
      }

      const candleData = param.seriesData?.get?.(candleSeries);
      const open = isCandleSeriesData(candleData) ? candleData.open : null;
      const high = isCandleSeriesData(candleData) ? candleData.high : null;
      const low = isCandleSeriesData(candleData) ? candleData.low : null;
      const close = isCandleSeriesData(candleData) ? candleData.close : null;

      if (open === null || high === null || low === null || close === null) {
        setOhlcHover(null);
        return;
      }

      setOhlcHover({
        open: formatOhlcValue(open),
        high: formatOhlcValue(high),
        low: formatOhlcValue(low),
        close: formatOhlcValue(close),
      });
    };

    chart.subscribeCrosshairMove(onMove);
    return () => {
      if (!isChartDisposedRef.current) {
        try {
          chart.unsubscribeCrosshairMove(onMove);
        } catch {
          // already disposed
        }
      }
      setOhlcHover(null);
    };
  }, [showOhlcOnHover, mode, payload]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || isChartDisposedRef.current) return;
    if (!(singleAxisHover && mode === "candles")) return;

    const onMove = (param: MouseEventParams<Time>) => {
      if (isChartDisposedRef.current) return;
      const point = param?.point;
      if (!point || !containerRef.current) {
        clearAxisHover();
        return;
      }

      const candidates: Array<{ side: "left" | "right"; value: number; coord: number; distance: number }> = [];
      const benchmarkSeries = benchmarkSeriesRef.current;
      const candleSeries = candleSeriesRef.current;

      if (benchmarkSeries) {
        const benchmarkData = param.seriesData?.get?.(benchmarkSeries);
        const benchmarkValue = isLineSeriesData(benchmarkData) ? benchmarkData.value : null;
        if (benchmarkValue !== null) {
          const y = benchmarkSeries.priceToCoordinate(benchmarkValue);
          if (typeof y === "number") {
            candidates.push({
              side: "left",
              value: benchmarkValue,
              coord: y,
              distance: Math.abs(y - point.y),
            });
          }
        }
      }

      if (candleSeries) {
        const candleData = param.seriesData?.get?.(candleSeries);
        const candleValue = isCandleSeriesData(candleData) ? candleData.close : null;
        if (candleValue !== null) {
          const y = candleSeries.priceToCoordinate(candleValue);
          if (typeof y === "number") {
            candidates.push({
              side: "right",
              value: candleValue,
              coord: y,
              distance: Math.abs(y - point.y),
            });
          }
        }
      }

      if (candidates.length === 0) {
        clearAxisHover();
        return;
      }

      candidates.sort((a, b) => a.distance - b.distance);
      const active = candidates[0];
      setAxisHover({
        y: active.coord,
        side: active.side,
        label: formatAxisValue(active.value),
      });
    };

    chart.subscribeCrosshairMove(onMove);
    return () => {
      if (!isChartDisposedRef.current) {
        try {
          chart.unsubscribeCrosshairMove(onMove);
        } catch {
          // already disposed
        }
      }
      clearAxisHover();
    };
  }, [singleAxisHover, mode, payload]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !rsHighInfo || mode !== "line" || lineKey !== "rs_line" || isChartDisposedRef.current) {
      setRsHighX(null);
      setRsHighInView(false);
      return;
    }

    const updateMarker = () => {
      if (isChartDisposedRef.current) return;
      let x: number | null;
      try {
        x = chart.timeScale().timeToCoordinate(rsHighInfo.time as Time);
      } catch {
        return;
      }
      if (typeof x !== "number" || !containerRef.current) {
        setRsHighX(null);
        setRsHighInView(false);
        return;
      }
      const width = containerRef.current.clientWidth;
      setRsHighX(x);
      setRsHighInView(x >= 0 && x <= width);
    };

    updateMarker();
    try {
      chart.timeScale().subscribeVisibleTimeRangeChange(updateMarker);
      chart.timeScale().subscribeVisibleLogicalRangeChange(updateMarker);
    } catch {
      return;
    }
    window.addEventListener("resize", updateMarker);
    return () => {
      if (!isChartDisposedRef.current) {
        try {
          chart.timeScale().unsubscribeVisibleTimeRangeChange(updateMarker);
          chart.timeScale().unsubscribeVisibleLogicalRangeChange(updateMarker);
        } catch {
          // already disposed
        }
      }
      window.removeEventListener("resize", updateMarker);
    };
  }, [rsHighInfo, mode, lineKey]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !payload || !onNeedMoreHistory || isChartDisposedRef.current) return;

    const handleRange = (range: { from: number; to: number } | null) => {
      if (!range || !canLoadMoreHistory || isLoadingMoreHistory) return;

      const prevFrom = lastVisibleFromRef.current;
      lastVisibleFromRef.current = range.from;
      if (prevFrom === null) return;

      const movedLeft = range.from < prevFrom - 0.5;
      if (!movedLeft) return;
      if (range.from > 15) return;

      const now = Date.now();
      if (now - lastHistoryRequestAtRef.current < 400) return;
      lastHistoryRequestAtRef.current = now;
      onNeedMoreHistory();
    };

    try {
      chart.timeScale().subscribeVisibleLogicalRangeChange(handleRange);
    } catch {
      return;
    }
    return () => {
      if (!isChartDisposedRef.current) {
        try {
          chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleRange);
        } catch {
          // already disposed
        }
      }
    };
  }, [payload, onNeedMoreHistory, canLoadMoreHistory, isLoadingMoreHistory]);

  return (
    <section className="panel chart-panel">
      <div className="panel-header">
        <h2>{title}</h2>
        <div className="panel-meta">
          {showOhlcOnHover && mode === "candles" ? (
            <span className="ohlc-readout">
              O {ohlcHover?.open ?? "-"} H {ohlcHover?.high ?? "-"} L {ohlcHover?.low ?? "-"} C {ohlcHover?.close ?? "-"}
            </span>
          ) : null}
          {mode === "line" && lineKey === "rs_line" && rsHighInfo ? (
            <span className="rs-high-badge">
              1Y High {rsHighInfo.value.toFixed(6)} @ {rsHighInfo.time}
              {!rsHighInView ? " (off-screen)" : ""}
            </span>
          ) : null}
          {isLoadingMoreHistory ? <span>Loading more history...</span> : null}
        </div>
      </div>
      <div ref={containerRef} className="chart-host">
        {singleAxisHover && mode === "candles" && axisHover ? (
          <>
            <div className="axis-hover-line" style={{ top: `${axisHover.y}px` }} />
            <div className={`axis-hover-label ${axisHover.side}`} style={{ top: `${axisHover.y}px` }}>
              {axisHover.label}
            </div>
          </>
        ) : null}
        {mode === "line" && lineKey === "rs_line" && rsHighInfo && rsHighX !== null && rsHighInView ? (
          <>
            <div className="rs-high-vertical" style={{ left: `${rsHighX}px` }} />
            <div className="rs-high-date" style={{ left: `${rsHighX}px` }}>
              {rsHighInfo.time}
            </div>
          </>
        ) : null}
      </div>
    </section>
  );
}
