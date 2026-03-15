import type { ChartPayload } from "../types";

const mergeByTime = <T extends { time: string }>(left: T[], right: T[]) => {
  const merged = new Map<string, T>();
  [...left, ...right].forEach((item) => merged.set(item.time, item));
  return [...merged.values()].sort((a, b) => (a.time < b.time ? -1 : 1));
};

export const mergeChartPayload = (base: ChartPayload, incoming: ChartPayload): ChartPayload => {
  const keys = new Set([...Object.keys(base.indicators), ...Object.keys(incoming.indicators)]);
  const mergedIndicators: ChartPayload["indicators"] = {};

  keys.forEach((key) => {
    mergedIndicators[key] = mergeByTime(base.indicators[key] ?? [], incoming.indicators[key] ?? []);
  });

  const mergedCandles = mergeByTime(base.candles, incoming.candles);
  return {
    ...base,
    from: mergedCandles[0]?.time ?? base.from,
    to: mergedCandles[mergedCandles.length - 1]?.time ?? base.to,
    candles: mergedCandles,
    volume: mergeByTime(base.volume, incoming.volume),
    indicators: mergedIndicators,
    meta: base.meta ?? incoming.meta,
  };
};
