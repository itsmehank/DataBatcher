import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api";
import ChartPanel from "../components/ChartPanel";
import { REGIONS } from "../hooks/useDashboardData";
import { useSymbolCharts } from "../hooks/useSymbolCharts";
import { getInitialChartViewState } from "../lib/queryState";
import type { Region, SymbolOption, ThemeMode } from "../types";

type Props = {
  themeMode: ThemeMode;
};

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="filter-item">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function ChartViewPage({ themeMode }: Props) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [initial] = useState(() => getInitialChartViewState(searchParams));

  const [region, setRegion] = useState<Region>(REGIONS.includes(initial.region) ? initial.region : "US");
  const [market, setMarket] = useState(initial.market);
  const [category, setCategory] = useState(initial.category);
  const [symbol, setSymbol] = useState(initial.symbol);
  const [markets, setMarkets] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [symbolOptions, setSymbolOptions] = useState<SymbolOption[]>([]);
  const [error, setError] = useState("");

  const {
    daily,
    weekly,
    dailyHasMoreHistory,
    weeklyHasMoreHistory,
    dailyLoadingMoreHistory,
    weeklyLoadingMoreHistory,
    loading,
    loadMoreDailyHistory,
    loadMoreWeeklyHistory,
  } = useSymbolCharts({ region, symbol, onError: setError });

  const symbolName = useMemo(
    () => symbolOptions.find((item) => item.symbol === symbol)?.name ?? "-",
    [symbol, symbolOptions]
  );

  useEffect(() => {
    const nextParams: Record<string, string> = { region };
    if (market) nextParams.market = market;
    if (category) nextParams.category = category;
    if (symbol) nextParams.symbol = symbol;
    setSearchParams(nextParams, { replace: true });
  }, [region, market, category, symbol, setSearchParams]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setError("");
      try {
        const loaded = await api.getMarkets(region);
        if (!mounted) return;
        setMarkets(loaded);
        setMarket((prev) => (prev && loaded.includes(prev) ? prev : loaded[0] || ""));
      } catch (e) {
        if (!mounted) return;
        setError(e instanceof Error ? e.message : "Failed to load markets");
      }
    })();
    return () => {
      mounted = false;
    };
  }, [region]);

  useEffect(() => {
    if (!market) return;
    let mounted = true;
    (async () => {
      try {
        const loaded = await api.getCategories(region, market);
        if (!mounted) return;
        setCategories(loaded);
        setCategory((prev) => (prev && loaded.includes(prev) ? prev : loaded[0] || ""));
      } catch (e) {
        if (!mounted) return;
        setError(e instanceof Error ? e.message : "Failed to load categories");
      }
    })();
    return () => {
      mounted = false;
    };
  }, [region, market]);

  useEffect(() => {
    if (!market || !category) return;
    let mounted = true;
    (async () => {
      try {
        const loaded = await api.getSymbolOptions(region, market, category);
        if (!mounted) return;
        setSymbolOptions(loaded);
        setSymbol((prev) => (prev && loaded.some((item) => item.symbol === prev) ? prev : loaded[0]?.symbol || ""));
      } catch (e) {
        if (!mounted) return;
        setError(e instanceof Error ? e.message : "Failed to load symbol options");
      }
    })();
    return () => {
      mounted = false;
    };
  }, [region, market, category]);

  return (
    <main className="app-root">
      <header className="topbar">
        <h1>Chart View</h1>
        {loading ? <span className="badge">Loading</span> : null}
      </header>

      {error ? <div className="error-box">{error}</div> : null}

      <section className="filter-bar chart-view-filters">
        <SelectField label="Region" value={region} options={REGIONS} onChange={(value) => setRegion(value as Region)} />
        <SelectField label="Market" value={market} options={markets.length ? markets : [market || "-"]} onChange={setMarket} />
        <SelectField
          label="Category"
          value={category}
          options={categories.length ? categories : [category || "-"]}
          onChange={setCategory}
        />
        <SelectField
          label="Ticker"
          value={symbol}
          options={symbolOptions.length ? symbolOptions.map((item) => item.symbol) : [symbol || "-"]}
          onChange={setSymbol}
        />
        <label className="filter-item">
          <span>Name</span>
          <div className="filter-static-value">{symbolName}</div>
        </label>
      </section>

      <div className="chart-grid two-col">
        <ChartPanel
          title={`${symbol || "-"} Daily (Price + SMA + Benchmark + Volume)`}
          mode="candles"
          themeMode={themeMode}
          singleAxisHover
          showOhlcOnHover
          payload={daily}
          overlayKeys={["sma_50", "sma_100", "sma_150", "sma_200", "benchmark_close"]}
          leftScaleKeys={["benchmark_close"]}
          leftScaleMargins={{ top: 0.05, bottom: 0.65 }}
          volumeOverlayKeys={["volume_sma_50"]}
          onNeedMoreHistory={loadMoreDailyHistory}
          canLoadMoreHistory={dailyHasMoreHistory}
          isLoadingMoreHistory={dailyLoadingMoreHistory}
        />
        <ChartPanel title={`${symbol || "-"} Daily RS Line`} mode="line" themeMode={themeMode} payload={daily} lineKey="rs_line" />
      </div>

      <div className="chart-grid one-col">
        <ChartPanel
          title={`${symbol || "-"} Weekly (Price + SMA/EMA + Volume)`}
          mode="candles"
          themeMode={themeMode}
          showOhlcOnHover
          payload={weekly}
          overlayKeys={["sma_10", "sma_20", "sma_50", "sma_100", "sma_200", "ema_21"]}
          volumeOverlayKeys={["volume_sma_10"]}
          onNeedMoreHistory={loadMoreWeeklyHistory}
          canLoadMoreHistory={weeklyHasMoreHistory}
          isLoadingMoreHistory={weeklyLoadingMoreHistory}
        />
      </div>
    </main>
  );
}
