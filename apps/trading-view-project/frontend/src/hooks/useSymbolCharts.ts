import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../api";
import { mergeChartPayload } from "../lib/chartPayload";
import type { ChartPayload, Region } from "../types";

const toISO = (dt: Date) => dt.toISOString().slice(0, 10);
const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const shiftIsoDate = (isoDate: string, deltaDays: number) => {
  const dt = new Date(`${isoDate}T00:00:00Z`);
  dt.setUTCDate(dt.getUTCDate() + deltaDays);
  return toISO(dt);
};

type Args = {
  region: Region;
  symbol: string;
  onError: (message: string) => void;
};

export function useSymbolCharts({ region, symbol, onError }: Args) {
  const [daily, setDaily] = useState<ChartPayload | null>(null);
  const [weekly, setWeekly] = useState<ChartPayload | null>(null);
  const [dailyHasMoreHistory, setDailyHasMoreHistory] = useState(true);
  const [weeklyHasMoreHistory, setWeeklyHasMoreHistory] = useState(true);
  const [dailyLoadingMoreHistory, setDailyLoadingMoreHistory] = useState(false);
  const [weeklyLoadingMoreHistory, setWeeklyLoadingMoreHistory] = useState(false);
  const [loading, setLoading] = useState(false);

  const contextRef = useRef("");
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
      onError("");
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
        onError(e instanceof Error ? e.message : "Failed to load chart");
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
  }, [onError, region, symbol]);

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
        onError(e instanceof Error ? e.message : "Failed to load more daily history");
      }
    } finally {
      if (requestId === dailyLoadRequestIdRef.current) {
        setDailyLoadingMoreHistory(false);
        dailyInFlightRef.current = false;
      }
    }
  }, [daily, dailyHasMoreHistory, onError, region, symbol]);

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
        onError(e instanceof Error ? e.message : "Failed to load more weekly history");
      }
    } finally {
      if (requestId === weeklyLoadRequestIdRef.current) {
        setWeeklyLoadingMoreHistory(false);
        weeklyInFlightRef.current = false;
      }
    }
  }, [onError, region, symbol, weekly, weeklyHasMoreHistory]);

  return {
    daily,
    weekly,
    dailyHasMoreHistory,
    weeklyHasMoreHistory,
    dailyLoadingMoreHistory,
    weeklyLoadingMoreHistory,
    loading,
    loadMoreDailyHistory,
    loadMoreWeeklyHistory,
  };
}
