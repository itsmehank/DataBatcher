import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toJpeg } from "html-to-image";

import ChartPanel from "../components/ChartPanel";
import FilterBar from "../components/FilterBar";
import MinerviniTable from "../components/MinerviniTable";
import { REGIONS, useDashboardData } from "../hooks/useDashboardData";
import type { ThemeMode } from "../types";

const DAILY_SMA_KEYS = ["sma_50", "sma_100", "sma_150", "sma_200"] as const;
type DailySmaKey = (typeof DAILY_SMA_KEYS)[number];

type Props = {
  themeMode: ThemeMode;
};

export default function DashboardPage({ themeMode }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    region,
    setRegion,
    date,
    setDate,
    market,
    setMarket,
    category,
    setCategory,
    symbol,
    setSymbol,
    dates,
    markets,
    categories,
    symbols,
    rows,
    savingKeys,
    daily,
    weekly,
    dailyHasMoreHistory,
    weeklyHasMoreHistory,
    dailyLoadingMoreHistory,
    weeklyLoadingMoreHistory,
    loading,
    error,
    setError,
    onChangeListType,
    loadMoreDailyHistory,
    loadMoreWeeklyHistory,
  } = useDashboardData({ searchParams, setSearchParams });

  const [dailySmaVisibility, setDailySmaVisibility] = useState<Record<DailySmaKey, boolean>>({
    sma_50: true,
    sma_100: true,
    sma_150: true,
    sma_200: true,
  });
  const [showWeeklySma10, setShowWeeklySma10] = useState(true);
  const [showBenchmark, setShowBenchmark] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [captureRef, setCaptureRef] = useState<HTMLDivElement | null>(null);

  const titleBase = symbol || "-";
  const visibleDailySmaKeys = useMemo(
    () => DAILY_SMA_KEYS.filter((key) => dailySmaVisibility[key]),
    [dailySmaVisibility]
  );
  const dailyOverlayKeys = useMemo(
    () => [...visibleDailySmaKeys, ...(showBenchmark ? ["benchmark_close"] : [])],
    [visibleDailySmaKeys, showBenchmark]
  );
  const dailyLeftScaleKeys = useMemo(() => (showBenchmark ? ["benchmark_close"] : []), [showBenchmark]);
  const weeklyOverlayKeys = useMemo(
    () => [
      ...(showWeeklySma10 ? ["sma_10"] : []),
      "sma_20",
      "sma_50",
      "sma_100",
      "sma_200",
      "ema_21",
    ],
    [showWeeklySma10]
  );

  const onDownloadJpeg = useCallback(async () => {
    if (!captureRef || isExporting) return;

    const waitFrame = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const safeSymbol = symbol || "symbol";
    const fileName = `benchmark-lab-${region}-${safeSymbol}-${timestamp}.jpeg`;

    setIsExporting(true);
    setError("");

    try {
      await waitFrame();
      await waitFrame();

      const dataUrl = await toJpeg(captureRef, {
        quality: 0.95,
        pixelRatio: 2,
        cacheBust: true,
        backgroundColor: themeMode === "paper" ? "#ffffff" : "#0f172a",
        filter: (node) => {
          if (!(node instanceof HTMLElement)) return true;
          return !node.classList.contains("no-export");
        },
      });

      const link = document.createElement("a");
      link.download = fileName;
      link.href = dataUrl;
      link.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to export JPEG");
    } finally {
      setIsExporting(false);
    }
  }, [captureRef, isExporting, region, setError, symbol, themeMode]);

  return (
    <main className="app-root">
      <header className="topbar">
        <h1>Minervini Dashboard Benchmark Lab</h1>
        <div className="topbar-actions">
          {loading ? <span className="badge">Loading</span> : null}
          <button type="button" className="export-button" onClick={onDownloadJpeg} disabled={isExporting}>
            {isExporting ? "Preparing JPEG..." : "Download JPEG"}
          </button>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}

      <div ref={setCaptureRef}>
        <FilterBar
          region={region}
          date={date}
          market={market}
          category={category}
          symbol={symbol}
          regions={REGIONS}
          dates={dates.length ? dates : [date || "-"]}
          markets={markets.length ? markets : [market || "-"]}
          categories={categories.length ? categories : [category || "-"]}
          symbols={symbols.length ? symbols : [symbol || "-"]}
          onChange={(key, value) => {
            if (key === "region") setRegion(value as (typeof REGIONS)[number]);
            if (key === "date") setDate(value);
            if (key === "market") setMarket(value);
            if (key === "category") setCategory(value);
            if (key === "symbol") setSymbol(value);
          }}
        />

        <section className="sma-toggle-bar">
          <span>Daily SMA</span>
          {DAILY_SMA_KEYS.map((key) => (
            <label key={key}>
              <input
                type="checkbox"
                checked={dailySmaVisibility[key]}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setDailySmaVisibility((prev) => ({ ...prev, [key]: checked }));
                }}
              />
              {key.replace("sma_", "SMA ")}
            </label>
          ))}
          <label>
            <input type="checkbox" checked={showWeeklySma10} onChange={(e) => setShowWeeklySma10(e.target.checked)} />
            Weekly 10W SMA
          </label>
          <label>
            <input type="checkbox" checked={showBenchmark} onChange={(e) => setShowBenchmark(e.target.checked)} />
            Benchmark Index
          </label>
        </section>

        <div className="no-export">
          <MinerviniTable
            rows={rows}
            selectedSymbol={symbol}
            onSelectTicker={setSymbol}
            onChangeListType={onChangeListType}
            savingKeys={savingKeys}
          />
        </div>

        <div className="chart-grid two-col">
          <ChartPanel
            title={`${titleBase} Daily (Price + SMA + Benchmark + Volume)`}
            mode="candles"
            themeMode={themeMode}
            singleAxisHover
            showOhlcOnHover
            payload={daily}
            overlayKeys={dailyOverlayKeys}
            leftScaleKeys={dailyLeftScaleKeys}
            leftScaleMargins={showBenchmark ? { top: 0.05, bottom: 0.65 } : undefined}
            volumeOverlayKeys={["volume_sma_50"]}
            onNeedMoreHistory={loadMoreDailyHistory}
            canLoadMoreHistory={dailyHasMoreHistory}
            isLoadingMoreHistory={dailyLoadingMoreHistory}
          />
          <ChartPanel title={`${titleBase} Daily RS Line`} mode="line" themeMode={themeMode} payload={daily} lineKey="rs_line" />
        </div>

        <div className="chart-grid one-col">
          <ChartPanel
            title={`${titleBase} Weekly (Price + SMA/EMA + Volume)`}
            mode="candles"
            themeMode={themeMode}
            payload={weekly}
            overlayKeys={weeklyOverlayKeys}
            volumeOverlayKeys={["volume_sma_10"]}
            onNeedMoreHistory={loadMoreWeeklyHistory}
            canLoadMoreHistory={weeklyHasMoreHistory}
            isLoadingMoreHistory={weeklyLoadingMoreHistory}
          />
        </div>
      </div>
    </main>
  );
}
