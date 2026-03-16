import { useCallback, useEffect, useRef, useState } from "react";
import type { SetURLSearchParams } from "react-router-dom";

import { api } from "../api";
import { mergeChartPayload } from "../lib/chartPayload";
import { getInitialDashboardState } from "../lib/queryState";
import type { ChartPayload, ListType, MinerviniRow, Region } from "../types";

export const REGIONS: Region[] = ["US", "KR"];

const toISO = (dt: Date) => dt.toISOString().slice(0, 10);
const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const shiftIsoDate = (isoDate: string, deltaDays: number) => {
  const dt = new Date(`${isoDate}T00:00:00Z`);
  dt.setUTCDate(dt.getUTCDate() + deltaDays);
  return toISO(dt);
};

type Args = {
  searchParams: URLSearchParams;
  setSearchParams: SetURLSearchParams;
};

export function useDashboardData({ searchParams, setSearchParams }: Args) {
  const [initial] = useState(() => getInitialDashboardState(searchParams));

  const [region, setRegion] = useState<Region>(REGIONS.includes(initial.region) ? initial.region : "US");
  const [date, setDate] = useState(initial.date);
  const [market, setMarket] = useState(initial.market);
  const [category, setCategory] = useState(initial.category);
  const [symbol, setSymbol] = useState(initial.symbol);

  const [dates, setDates] = useState<string[]>([]);
  const [markets, setMarkets] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [symbols, setSymbols] = useState<string[]>([]);

  const [rows, setRows] = useState<MinerviniRow[]>([]);
  const [savingKeys, setSavingKeys] = useState<Record<string, boolean>>({});
  const [daily, setDaily] = useState<ChartPayload | null>(null);
  const [weekly, setWeekly] = useState<ChartPayload | null>(null);
  const [dailyHasMoreHistory, setDailyHasMoreHistory] = useState(true);
  const [weeklyHasMoreHistory, setWeeklyHasMoreHistory] = useState(true);
  const [dailyLoadingMoreHistory, setDailyLoadingMoreHistory] = useState(false);
  const [weeklyLoadingMoreHistory, setWeeklyLoadingMoreHistory] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  const contextRef = useRef<string>("");
  const initialChartRequestIdRef = useRef(0);
  const initialChartAbortRef = useRef<AbortController | null>(null);

  const dailyCursorFromRef = useRef<string | null>(null);
  const weeklyCursorFromRef = useRef<string | null>(null);

  const dailyLoadRequestIdRef = useRef(0);
  const weeklyLoadRequestIdRef = useRef(0);
  const dailyLoadAbortRef = useRef<AbortController | null>(null);
  const weeklyLoadAbortRef = useRef<AbortController | null>(null);
  const dailyInFlightRef = useRef(false);
  const weeklyInFlightRef = useRef(false);
  const lastListContextRef = useRef("");

  useEffect(() => {
    const nextParams: Record<string, string> = { region };
    if (date) nextParams.date = date;
    if (market) nextParams.market = market;
    if (category) nextParams.category = category;
    if (symbol) nextParams.symbol = symbol;
    setSearchParams(nextParams, { replace: true });
  }, [region, date, market, category, symbol, setSearchParams]);

  useEffect(() => {
    contextRef.current = `${region}:${symbol}`;
  }, [region, symbol]);

  useEffect(() => {
    return () => {
      initialChartAbortRef.current?.abort();
      dailyLoadAbortRef.current?.abort();
      weeklyLoadAbortRef.current?.abort();
    };
  }, []);

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
        const loaded = await api.getSymbols(region, market, category);
        if (!mounted) return;
        setSymbols(loaded);
      } catch (e) {
        if (!mounted) return;
        setError(e instanceof Error ? e.message : "Failed to load symbols");
      }
    })();
    return () => {
      mounted = false;
    };
  }, [region, market, category]);

  useEffect(() => {
    if (!date || !market) {
      setRows([]);
      setSymbol("");
      setDaily(null);
      setWeekly(null);
      setLoading(false);
      lastListContextRef.current = "";
      return;
    }

    let mounted = true;
    const currentListContext = `${region}:${date}:${market}`;

    (async () => {
      try {
        const loaded = await api.getMinervini(region, date, market);
        if (!mounted) return;
        setRows(loaded);

        const topTicker = loaded[0]?.ticker ?? "";
        const isContextChanged = lastListContextRef.current !== currentListContext;

        if (!topTicker) {
          setSymbol("");
          setDaily(null);
          setWeekly(null);
          setLoading(false);
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
  }, [region, date, market, symbol]);

  useEffect(() => {
    if (!symbol) {
      setDaily(null);
      setWeekly(null);
      setLoading(false);
      return;
    }

    let mounted = true;
    const requestId = ++initialChartRequestIdRef.current;
    const controller = new AbortController();
    const currentContext = `${region}:${symbol}`;
    contextRef.current = currentContext;

    initialChartAbortRef.current?.abort();
    initialChartAbortRef.current = controller;

    dailyLoadAbortRef.current?.abort();
    weeklyLoadAbortRef.current?.abort();
    dailyInFlightRef.current = false;
    weeklyInFlightRef.current = false;

    (async () => {
      setLoading(true);
      setError("");
      setDailyHasMoreHistory(true);
      setWeeklyHasMoreHistory(true);
      setDailyLoadingMoreHistory(false);
      setWeeklyLoadingMoreHistory(false);
      const to = toISO(new Date());
      const fromDaily = toISO(new Date(Date.now() - 1000 * 60 * 60 * 24 * 180));
      const fromWeekly = toISO(new Date(Date.now() - 1000 * 60 * 60 * 24 * 365 * 2));
      try {
        const [d, b, w] = await Promise.all([
          api.getDaily(region, symbol, fromDaily, to, controller.signal),
          api.getBenchmarkDaily(region, fromDaily, to, controller.signal),
          api.getWeekly(region, symbol, fromWeekly, to, controller.signal),
        ]);
        if (!mounted) return;
        if (requestId !== initialChartRequestIdRef.current) return;
        if (contextRef.current !== currentContext) return;

        dailyCursorFromRef.current = d.from;
        weeklyCursorFromRef.current = w.from;
        setDaily({
          ...d,
          indicators: {
            ...d.indicators,
            benchmark_close: b.indicators.benchmark_close ?? [],
          },
        });
        setWeekly(w);
      } catch (e) {
        if (isAbortError(e)) return;
        if (!mounted) return;
        if (requestId !== initialChartRequestIdRef.current) return;
        setError(e instanceof Error ? e.message : "Failed to load chart");
      } finally {
        if (mounted && requestId === initialChartRequestIdRef.current) {
          setLoading(false);
        }
      }
    })();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, [region, symbol]);

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

  const loadMoreDailyHistory = useCallback(async () => {
    if (!symbol || !daily || !dailyHasMoreHistory) return;
    if (dailyInFlightRef.current) return;

    const cursorFrom = dailyCursorFromRef.current;
    if (!cursorFrom) return;

    const currentContext = `${region}:${symbol}`;
    const requestId = ++dailyLoadRequestIdRef.current;
    dailyLoadAbortRef.current?.abort();
    const controller = new AbortController();
    dailyLoadAbortRef.current = controller;
    dailyInFlightRef.current = true;

    setDailyLoadingMoreHistory(true);

    const nextTo = shiftIsoDate(cursorFrom, -1);
    const nextFrom = shiftIsoDate(cursorFrom, -365);

    try {
      const [older, olderBenchmark] = await Promise.all([
        api.getDaily(region, symbol, nextFrom, nextTo, controller.signal),
        api.getBenchmarkDaily(region, nextFrom, nextTo, controller.signal),
      ]);
      if (requestId !== dailyLoadRequestIdRef.current) return;
      if (contextRef.current !== currentContext) return;

      if (older.candles.length === 0) {
        setDailyHasMoreHistory(false);
        return;
      }

      const oldestOlderTime = older.candles[0]?.time;
      if (!oldestOlderTime || oldestOlderTime >= cursorFrom) {
        setDailyHasMoreHistory(false);
      } else {
        dailyCursorFromRef.current = oldestOlderTime;
      }

      setDaily((prev) => {
        const olderWithBenchmark: ChartPayload = {
          ...older,
          indicators: {
            ...older.indicators,
            benchmark_close: olderBenchmark.indicators.benchmark_close ?? [],
          },
        };
        if (!prev) return olderWithBenchmark;
        return mergeChartPayload(prev, olderWithBenchmark);
      });
    } catch (e) {
      if (!isAbortError(e)) {
        setError(e instanceof Error ? e.message : "Failed to load more daily history");
      }
    } finally {
      if (requestId === dailyLoadRequestIdRef.current) {
        setDailyLoadingMoreHistory(false);
        dailyInFlightRef.current = false;
      }
    }
  }, [symbol, daily, dailyHasMoreHistory, region]);

  const loadMoreWeeklyHistory = useCallback(async () => {
    if (!symbol || !weekly || !weeklyHasMoreHistory) return;
    if (weeklyInFlightRef.current) return;

    const cursorFrom = weeklyCursorFromRef.current;
    if (!cursorFrom) return;

    const currentContext = `${region}:${symbol}`;
    const requestId = ++weeklyLoadRequestIdRef.current;
    weeklyLoadAbortRef.current?.abort();
    const controller = new AbortController();
    weeklyLoadAbortRef.current = controller;
    weeklyInFlightRef.current = true;

    setWeeklyLoadingMoreHistory(true);

    const nextTo = shiftIsoDate(cursorFrom, -1);
    const nextFrom = shiftIsoDate(cursorFrom, -730);

    try {
      const older = await api.getWeekly(region, symbol, nextFrom, nextTo, controller.signal);
      if (requestId !== weeklyLoadRequestIdRef.current) return;
      if (contextRef.current !== currentContext) return;

      if (older.candles.length === 0) {
        setWeeklyHasMoreHistory(false);
        return;
      }

      const oldestOlderTime = older.candles[0]?.time;
      if (!oldestOlderTime || oldestOlderTime >= cursorFrom) {
        setWeeklyHasMoreHistory(false);
      } else {
        weeklyCursorFromRef.current = oldestOlderTime;
      }

      setWeekly((prev) => {
        if (!prev) return older;
        return mergeChartPayload(prev, older);
      });
    } catch (e) {
      if (!isAbortError(e)) {
        setError(e instanceof Error ? e.message : "Failed to load more weekly history");
      }
    } finally {
      if (requestId === weeklyLoadRequestIdRef.current) {
        setWeeklyLoadingMoreHistory(false);
        weeklyInFlightRef.current = false;
      }
    }
  }, [symbol, weekly, weeklyHasMoreHistory, region]);

  return {
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
  };
}
