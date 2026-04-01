import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth/AuthContext";
import ChartPanel from "../components/ChartPanel";
import { useSymbolCharts } from "../hooks/useSymbolCharts";
import { getInitialListViewState } from "../lib/queryState";
import type { ListType, ListViewItem, Region, ThemeMode } from "../types";

const REGIONS: Region[] = ["US", "KR"];

type Props = {
  themeMode: ThemeMode;
};

export default function ListViewPage({ themeMode }: Props) {
  const { isEditor } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [initial] = useState(() => getInitialListViewState(searchParams));

  const [region, setRegion] = useState<Region>(REGIONS.includes(initial.region) ? initial.region : "US");
  const [date, setDate] = useState(initial.date);
  const [listCategory, setListCategory] = useState<ListType | "all">(
    ["focus", "action", "pass", "all"].includes(initial.listCategory) ? initial.listCategory : "all"
  );

  const [dates, setDates] = useState<string[]>([]);
  const [items, setItems] = useState<ListViewItem[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [savingKeys, setSavingKeys] = useState<Record<string, boolean>>({});
  const [isBootstrapped, setIsBootstrapped] = useState(false);
  const [datesLoading, setDatesLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const datesRequestIdRef = useRef(0);
  const itemsRequestIdRef = useRef(0);

  const {
    daily,
    weekly,
    dailyHasMoreHistory,
    weeklyHasMoreHistory,
    dailyLoadingMoreHistory,
    weeklyLoadingMoreHistory,
    loading: chartLoading,
    loadMoreDailyHistory,
    loadMoreWeeklyHistory,
  } = useSymbolCharts({ region, symbol: selectedSymbol, onError: setError });

  useEffect(() => {
    if (!isBootstrapped) return;

    const nextParams: Record<string, string> = { region, listCategory };
    if (date) nextParams.date = date;

    const currentRegion = searchParams.get("region") || "";
    const currentListCategory = searchParams.get("listCategory") || "";
    const currentDate = searchParams.get("date") || "";

    if (currentRegion === region && currentListCategory === listCategory && currentDate === (date || "")) {
      return;
    }

    setSearchParams(nextParams, { replace: true });
  }, [isBootstrapped, region, date, listCategory, setSearchParams]);

  useEffect(() => {
    setIsBootstrapped(false);
    setItems([]);
    setLoading(false);

    let mounted = true;
    const requestId = ++datesRequestIdRef.current;
    (async () => {
      setDatesLoading(true);
      setError("");
      try {
        const loaded = await api.getListViewDates(region);
        if (!mounted) return;
        if (requestId !== datesRequestIdRef.current) return;

        setDates(loaded);
        const resolvedDate = ((prev: string) => {
          if (prev && loaded.includes(prev)) return prev;
          return loaded[0] || "";
        })(date);

        setDate(resolvedDate);
        setIsBootstrapped(true);
      } catch (e) {
        if (!mounted) return;
        if (requestId !== datesRequestIdRef.current) return;

        setError(e instanceof Error ? e.message : "Failed to load dates");
        setDates([]);
        setDate("");
        setIsBootstrapped(true);
      } finally {
        if (mounted && requestId === datesRequestIdRef.current) {
          setDatesLoading(false);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, [region]);

  useEffect(() => {
    if (!isBootstrapped) return;

    if (!date) {
      setItems([]);
      setSelectedSymbol("");
      setLoading(false);
      return;
    }

    let mounted = true;
    const requestId = ++itemsRequestIdRef.current;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const loaded = await api.getListViewItems(region, date, listCategory);
        if (!mounted) return;
        if (requestId !== itemsRequestIdRef.current) return;

        setItems(loaded);
        setSelectedSymbol((prev) => (prev && loaded.some((item) => item.symbol === prev) ? prev : ""));
      } catch (e) {
        if (!mounted) return;
        if (requestId !== itemsRequestIdRef.current) return;

        setError(e instanceof Error ? e.message : "Failed to load items");
      } finally {
        if (mounted && requestId === itemsRequestIdRef.current) {
          setLoading(false);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, [isBootstrapped, region, date, listCategory]);

  const updateItemField = <K extends keyof ListViewItem>(key: K, rowKey: string, value: ListViewItem[K]) => {
    setItems((prev) => prev.map((item) => (item.symbol + ":" + item.market === rowKey ? { ...item, [key]: value } : item)));
  };

  const onSaveRow = async (item: ListViewItem) => {
    const rowKey = `${item.symbol}:${item.market}`;
    setSavingKeys((prev) => ({ ...prev, [rowKey]: true }));
    try {
      await api.updateListViewItem({
        region,
        date,
        market: item.market,
        symbol: item.symbol,
        trigger_price: item.trigger_price,
        stop_price: item.stop_price,
        status_tag: item.status_tag,
        memo: item.memo,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update item");
      try {
        const refreshed = await api.getListViewItems(region, date, listCategory);
        setItems(refreshed);
      } catch {
        // ignore refresh failure
      }
    } finally {
      setSavingKeys((prev) => ({ ...prev, [rowKey]: false }));
    }
  };

  return (
    <main className="app-root">
      <header className="topbar">
        <h1>List View</h1>
        {loading || chartLoading ? <span className="badge">Loading</span> : null}
      </header>

      {error ? <div className="error-box">{error}</div> : null}

      <section className="filter-bar list-view-filters">
        <label className="filter-item">
          <span>Region</span>
          <select value={region} onChange={(e) => setRegion(e.target.value as Region)}>
            {REGIONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-item">
          <span>Date</span>
          <select value={date} onChange={(e) => setDate(e.target.value)}>
            {!date ? <option value="">{datesLoading ? "Loading..." : "-"}</option> : null}
            {(dates.length ? dates : [date || "-"]).map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-item">
          <span>List Category</span>
          <select value={listCategory} onChange={(e) => setListCategory(e.target.value as ListType | "all")}>
            <option value="all">all</option>
            <option value="focus">focus</option>
            <option value="action">action</option>
            <option value="pass">pass</option>
          </select>
        </label>
      </section>

      <section className="panel table-panel">
        <div className="panel-header">
          <h2>Selected Symbols</h2>
          <span>{items.length} rows</span>
        </div>
        <div className="table-wrap">
          {!isBootstrapped ? (
            <div style={{ padding: "0.75rem" }}>Loading list view...</div>
          ) : datesLoading && !date ? (
            <div style={{ padding: "0.75rem" }}>Loading available dates...</div>
          ) : !datesLoading && dates.length === 0 ? (
            <div style={{ padding: "0.75rem" }}>No available dates for this region.</div>
          ) : (
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Name</th>
                <th>Market</th>
                <th>List Type</th>
                <th>Sector</th>
                <th>RS Rating</th>
                <th>Trigger Price</th>
                <th>Stop Price</th>
                <th>Status Tag</th>
                <th>Memo</th>
                <th>Save</th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && !loading ? (
                <tr>
                  <td colSpan={11}>No items for the selected filters.</td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr
                    key={`${item.symbol}-${item.market}-${item.list_type}`}
                    className={item.symbol === selectedSymbol ? "active" : ""}
                  >
                    <td>
                      <button type="button" className="link-button" onClick={() => setSelectedSymbol(item.symbol)}>
                        {item.symbol}
                      </button>
                    </td>
                    <td>{item.name ?? "-"}</td>
                    <td>{item.market}</td>
                    <td>{item.list_type}</td>
                    <td>{item.sector ?? "-"}</td>
                    <td>{item.rs_rating ?? "-"}</td>
                    <td>
                      <input
                        type="number"
                        step="0.0001"
                        value={item.trigger_price ?? ""}
                        disabled={!isEditor}
                        onChange={(e) =>
                          updateItemField(
                            "trigger_price",
                            `${item.symbol}:${item.market}`,
                            e.target.value === "" ? null : Number(e.target.value)
                          )
                        }
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        step="0.0001"
                        value={item.stop_price ?? ""}
                        disabled={!isEditor}
                        onChange={(e) =>
                          updateItemField(
                            "stop_price",
                            `${item.symbol}:${item.market}`,
                            e.target.value === "" ? null : Number(e.target.value)
                          )
                        }
                      />
                    </td>
                    <td>
                      <select
                        value={item.status_tag ?? ""}
                        disabled={!isEditor}
                        onChange={(e) =>
                          updateItemField(
                            "status_tag",
                            `${item.symbol}:${item.market}`,
                            (e.target.value || null) as ListViewItem["status_tag"]
                          )
                        }
                      >
                        <option value="">(none)</option>
                        <option value="A">A</option>
                        <option value="B">B</option>
                        <option value="C">C</option>
                        <option value="D">D</option>
                        <option value="E">E</option>
                      </select>
                    </td>
                    <td>
                      <input
                        type="text"
                        value={item.memo ?? ""}
                        disabled={!isEditor}
                        onChange={(e) => updateItemField("memo", `${item.symbol}:${item.market}`, e.target.value)}
                      />
                    </td>
                    <td>
                      <button
                        className="link-button"
                        onClick={() => onSaveRow(item)}
                        disabled={!isEditor || savingKeys[`${item.symbol}:${item.market}`]}
                      >
                        {savingKeys[`${item.symbol}:${item.market}`] ? "Saving..." : "Save"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          )}
        </div>
      </section>

      <div className="chart-grid two-col">
        <ChartPanel
          title={`${selectedSymbol || "-"} Daily (Price + SMA + Benchmark + Volume)`}
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
        <ChartPanel title={`${selectedSymbol || "-"} Daily RS Line`} mode="line" themeMode={themeMode} payload={daily} lineKey="rs_line" />
      </div>

      <div className="chart-grid one-col">
        <ChartPanel
          title={`${selectedSymbol || "-"} Weekly (Price + SMA/EMA + Volume)`}
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
