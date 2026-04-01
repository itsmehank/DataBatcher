import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import JSZip from "jszip";
import { useSearchParams } from "react-router-dom";
import { toJpeg } from "html-to-image";

import ChartPanel from "../components/ChartPanel";
import FilterBar from "../components/FilterBar";
import MinerviniTable from "../components/MinerviniTable";
import { REGIONS, useDashboardData } from "../hooks/useDashboardData";
import type { MinerviniRow, ThemeMode } from "../types";

const DAILY_SMA_KEYS = ["sma_50", "sma_100", "sma_150", "sma_200"] as const;
type DailySmaKey = (typeof DAILY_SMA_KEYS)[number];

type Props = {
  themeMode: ThemeMode;
};

type ExportProgress = {
  current: number;
  total: number;
  symbol: string;
};

type CaptureReadyWaiter = {
  symbol: string;
  resolve: () => void;
  reject: (error: Error) => void;
};

const waitFrame = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
const getRowKey = (row: MinerviniRow) => `${row.ticker}:${row.market}`;
const sanitizeFilePart = (value: string) => value.replace(/[<>:"/\\|?*\x00-\x1F]/g, "_").trim() || "item";

export default function DashboardPage({ themeMode }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    region,
    setRegion,
    date,
    setDate,
    market,
    setMarket,
    listCategory,
    setListCategory,
    symbol,
    setSymbol,
    dates,
    markets,
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
  const [checkedKeys, setCheckedKeys] = useState<Record<string, boolean>>({});
  const [exportProgress, setExportProgress] = useState<ExportProgress | null>(null);
  const [exportSummary, setExportSummary] = useState("");
  const [captureRef, setCaptureRef] = useState<HTMLDivElement | null>(null);
  const captureReadyRef = useRef<CaptureReadyWaiter | null>(null);

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

  const checkedCount = useMemo(
    () => rows.reduce((count, row) => count + (checkedKeys[getRowKey(row)] ? 1 : 0), 0),
    [checkedKeys, rows]
  );
  const areAllRowsChecked = rows.length > 0 && rows.every((row) => checkedKeys[getRowKey(row)]);
  const areSomeRowsChecked = rows.some((row) => checkedKeys[getRowKey(row)]) && !areAllRowsChecked;
  const batchButtonLabel = exportProgress
    ? `Capturing ${exportProgress.current}/${exportProgress.total}...`
    : checkedCount > 0
      ? `Download Checked (${checkedCount})`
      : "Download Checked";

  useEffect(() => {
    setCheckedKeys({});
    setExportSummary("");
  }, [region, date, market]);

  useEffect(() => {
    if (!captureReadyRef.current || loading) return;

    const pending = captureReadyRef.current;
    if (symbol !== pending.symbol) return;

    if (error) {
      captureReadyRef.current = null;
      pending.reject(new Error(error));
      return;
    }

    if (daily?.symbol !== pending.symbol || weekly?.symbol !== pending.symbol) {
      return;
    }

    captureReadyRef.current = null;
    void (async () => {
      await waitFrame();
      await waitFrame();
      pending.resolve();
    })();
  }, [daily, error, loading, symbol, weekly]);

  const capturePanelJpeg = useCallback(async () => {
    if (!captureRef) {
      throw new Error("Capture panel not ready");
    }

    await waitFrame();
    await waitFrame();

    return toJpeg(captureRef, {
      quality: 0.95,
      pixelRatio: 2,
      cacheBust: true,
      backgroundColor: themeMode === "paper" ? "#ffffff" : "#0f172a",
      filter: (node) => {
        if (!(node instanceof HTMLElement)) return true;
        return !node.classList.contains("no-export");
      },
    });
  }, [captureRef, themeMode]);

  const waitForSymbolCaptureReady = useCallback(
    async (targetSymbol: string) => {
      if (symbol === targetSymbol && !loading && daily?.symbol === targetSymbol && weekly?.symbol === targetSymbol && !error) {
        await waitFrame();
        await waitFrame();
        return;
      }

      await new Promise<void>((resolve, reject) => {
        captureReadyRef.current = { symbol: targetSymbol, resolve, reject };
        setSymbol(targetSymbol);
      });
    },
    [daily?.symbol, error, loading, setSymbol, symbol, weekly?.symbol]
  );

  const onToggleRowChecked = useCallback((row: MinerviniRow) => {
    const rowKey = getRowKey(row);
    setCheckedKeys((prev) => ({ ...prev, [rowKey]: !prev[rowKey] }));
  }, []);

  const onToggleAllChecked = useCallback(() => {
    setCheckedKeys((prev) => {
      const next = { ...prev };
      if (areAllRowsChecked) {
        rows.forEach((row) => {
          delete next[getRowKey(row)];
        });
        return next;
      }

      rows.forEach((row) => {
        next[getRowKey(row)] = true;
      });
      return next;
    });
  }, [areAllRowsChecked, rows]);

  const onDownloadJpeg = useCallback(async () => {
    if (!captureRef || isExporting) return;

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const safeSymbol = symbol || "symbol";
    const fileName = `benchmark-lab-${region}-${safeSymbol}-${timestamp}.jpeg`;

    setIsExporting(true);
    setError("");
    setExportSummary("");

    try {
      const dataUrl = await capturePanelJpeg();

      const link = document.createElement("a");
      link.download = fileName;
      link.href = dataUrl;
      link.click();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to export JPEG");
    } finally {
      setIsExporting(false);
    }
  }, [capturePanelJpeg, captureRef, isExporting, region, setError, symbol]);

  const onDownloadChecked = useCallback(async () => {
    if (isExporting) return;

    const targets = rows.filter((row) => checkedKeys[getRowKey(row)]);
    if (targets.length === 0) return;

    const originalSymbol = symbol;
    const zip = new JSZip();
    const failures: string[] = [];
    const indexWidth = Math.max(3, String(targets.length).length);
    const zipDate = (date || new Date().toISOString().slice(0, 10)).replace(/-/g, "");
    const zipMarket = sanitizeFilePart(market || "ALL");

    setIsExporting(true);
    setExportProgress({ current: 0, total: targets.length, symbol: "" });
    setError("");
    setExportSummary("");

    try {
      for (const [index, row] of targets.entries()) {
        const targetSymbol = row.ticker;
        setExportProgress({ current: index + 1, total: targets.length, symbol: targetSymbol });

        try {
          await waitForSymbolCaptureReady(targetSymbol);

          const dataUrl = await capturePanelJpeg();
          const imageBlob = await (await fetch(dataUrl)).blob();
          const fileName = `${String(index + 1).padStart(indexWidth, "0")}_${sanitizeFilePart(targetSymbol)}.jpg`;
          zip.file(fileName, imageBlob);
        } catch (e) {
          failures.push(targetSymbol);
          if (e instanceof Error) {
            console.error(`Failed to export ${targetSymbol}:`, e);
          }
        }
      }

      const successCount = targets.length - failures.length;
      if (successCount === 0) {
        throw new Error("Failed to export all selected symbols");
      }

      const zipBlob = await zip.generateAsync({ type: "blob" });
      const link = document.createElement("a");
      link.download = `${region}-${zipDate}-${zipMarket}.zip`;
      link.href = URL.createObjectURL(zipBlob);
      link.click();
      URL.revokeObjectURL(link.href);

      setExportSummary(`Success ${successCount} / Failure ${failures.length}`);
      if (failures.length > 0) {
        setError(`Failed symbols: ${failures.join(", ")}`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to export checked charts");
    } finally {
      captureReadyRef.current = null;
      setExportProgress(null);
      setIsExporting(false);
      if (originalSymbol) {
        setSymbol(originalSymbol);
      }
    }
  }, [capturePanelJpeg, checkedKeys, date, isExporting, market, region, rows, setError, setSymbol, symbol, waitForSymbolCaptureReady]);

  return (
    <main className="app-root">
      <header className="topbar">
        <h1>Minervini Dashboard Benchmark Lab</h1>
        <div className="topbar-actions">
          {loading ? <span className="badge">Loading</span> : null}
          {exportSummary ? <span className="badge">{exportSummary}</span> : null}
          <button type="button" className="export-button" onClick={onDownloadJpeg} disabled={isExporting}>
            {isExporting ? "Preparing JPEG..." : "Download JPEG"}
          </button>
          <button type="button" className="export-button" onClick={onDownloadChecked} disabled={isExporting || checkedCount === 0}>
            {batchButtonLabel}
          </button>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}

      <div ref={setCaptureRef}>
        <FilterBar
          region={region}
          date={date}
          market={market}
          listCategory={listCategory}
          disabled={isExporting}
          regions={REGIONS}
          dates={dates.length ? dates : [date || "-"]}
          markets={markets.length ? markets : [market || "-"]}
          onChange={(key, value) => {
            if (key === "region") setRegion(value as (typeof REGIONS)[number]);
            if (key === "date") setDate(value);
            if (key === "market") setMarket(value);
            if (key === "listCategory") setListCategory(value as "all" | "focus" | "action" | "pass");
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
            checkedKeys={checkedKeys}
            areAllRowsChecked={areAllRowsChecked}
            areSomeRowsChecked={areSomeRowsChecked}
            onSelectTicker={setSymbol}
            onToggleRowChecked={onToggleRowChecked}
            onToggleAllChecked={onToggleAllChecked}
            onChangeListType={onChangeListType}
            savingKeys={savingKeys}
            disableSelection={isExporting}
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
            showOhlcOnHover
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
