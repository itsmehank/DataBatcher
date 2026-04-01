import { useCallback, useEffect, useRef, useState } from "react";
import type { SetURLSearchParams } from "react-router-dom";

import { api } from "../api";
import { getInitialDashboardState } from "../lib/queryState";
import type { ListType, MinerviniRow, Region } from "../types";
import { useSymbolCharts } from "./useSymbolCharts";

export const REGIONS: Region[] = ["US", "KR"];

const toISO = (dt: Date) => dt.toISOString().slice(0, 10);

type Args = {
  searchParams: URLSearchParams;
  setSearchParams: SetURLSearchParams;
};

export function useDashboardData({ searchParams, setSearchParams }: Args) {
  const [initial] = useState(() => getInitialDashboardState(searchParams));

  const [region, setRegion] = useState<Region>(REGIONS.includes(initial.region) ? initial.region : "US");
  const [date, setDate] = useState(initial.date);
  const [market, setMarket] = useState(initial.market);
  const [listCategory, setListCategory] = useState<ListType | "all">(initial.listCategory);
  const [symbol, setSymbol] = useState("");

  const [dates, setDates] = useState<string[]>([]);
  const [markets, setMarkets] = useState<string[]>([]);

  const [rows, setRows] = useState<MinerviniRow[]>([]);
  const [savingKeys, setSavingKeys] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string>("");

  const lastListContextRef = useRef("");

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

  useEffect(() => {
    const nextParams: Record<string, string> = { region };
    if (date) nextParams.date = date;
    if (market) nextParams.market = market;
    if (listCategory) nextParams.listCategory = listCategory;
    setSearchParams(nextParams, { replace: true });
  }, [region, date, market, listCategory, setSearchParams]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setError("");
      try {
        const [loadedDates, loadedMarkets] = await Promise.all([api.getDates(region), api.getMarkets(region)]);
        if (!mounted) return;
        setDates(loadedDates);
        setMarkets(loadedMarkets);
        setDate((prev) => prev || loadedDates[0] || toISO(new Date()));
        setMarket((prev) => (prev && loadedMarkets.includes(prev) ? prev : loadedMarkets[0] || ""));
      } catch (e) {
        if (!mounted) return;
        setError(e instanceof Error ? e.message : "Failed to load options");
      }
    })();
    return () => {
      mounted = false;
    };
  }, [region]);

  useEffect(() => {
    if (!date || !market) {
      setRows([]);
      setSymbol("");
      lastListContextRef.current = "";
      return;
    }

    let mounted = true;
    const currentListContext = `${region}:${date}:${market}:${listCategory}`;

    (async () => {
      try {
        const loaded = await api.getMinervini(region, date, market, listCategory);
        if (!mounted) return;
        setRows(loaded);

        const topTicker = loaded[0]?.ticker ?? "";
        const isContextChanged = lastListContextRef.current !== currentListContext;

        if (!topTicker) {
          setSymbol("");
          lastListContextRef.current = currentListContext;
          return;
        }

        if (isContextChanged || !symbol || !loaded.some((r) => r.ticker === symbol)) {
          setSymbol(topTicker);
        }

        lastListContextRef.current = currentListContext;
      } catch (e) {
        if (!mounted) return;
        setError(e instanceof Error ? e.message : "Failed to load list");
      }
    })();

    return () => {
      mounted = false;
    };
  }, [region, date, market, listCategory, symbol]);

  const onChangeListType = useCallback(
    async (row: MinerviniRow, nextType: ListType | null) => {
      const rowKey = `${row.ticker}:${row.market}`;
      const previousType = row.list_type;
      setSavingKeys((prev) => ({ ...prev, [rowKey]: true }));
      setRows((prev) =>
        prev.map((r) => (r.ticker === row.ticker && r.market === row.market ? { ...r, list_type: nextType } : r))
      );

      try {
        await api.updateMinerviniListType(region, date, row.market, row.ticker, nextType);
      } catch (e) {
        setRows((prev) =>
          prev.map((r) => (r.ticker === row.ticker && r.market === row.market ? { ...r, list_type: previousType } : r))
        );
        setError(e instanceof Error ? e.message : "Failed to update list type");
      } finally {
        setSavingKeys((prev) => ({ ...prev, [rowKey]: false }));
      }
    },
    [region, date]
  );

  return {
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
  };
}
