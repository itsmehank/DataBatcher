import type { ChartPayload, Region } from "../types";

type PricePoint = {
  time: string;
  value: number;
};

export type ExcessReturnCard = {
  label: "1M" | "3M" | "6M";
  benchmarkLabel: string;
  excessReturn: number | null;
  symbolReturn: number | null;
  benchmarkReturn: number | null;
};

const PERIOD_MONTHS = [
  { label: "1M" as const, months: 1 },
  { label: "3M" as const, months: 3 },
  { label: "6M" as const, months: 6 },
];

const toUtcDate = (isoDate: string) => new Date(`${isoDate}T00:00:00Z`);

const benchmarkLabelByRegion = (region: Region) => (region === "KR" ? "KOSPI" : "S&P 500");

const toPriceSeries = (payload: ChartPayload): PricePoint[] =>
  payload.candles.map((candle) => ({ time: candle.time, value: candle.close }));

const toBenchmarkSeries = (payload: ChartPayload): PricePoint[] =>
  (payload.indicators.benchmark_close ?? []).map((point) => ({ time: point.time, value: point.value }));

const findPointOnOrBefore = (series: PricePoint[], targetDate: Date) => {
  for (let index = series.length - 1; index >= 0; index -= 1) {
    if (toUtcDate(series[index].time) <= targetDate) {
      return series[index];
    }
  }
  return null;
};

const toReturnPct = (start: number, end: number) => {
  if (!Number.isFinite(start) || !Number.isFinite(end) || start <= 0) return null;
  return ((end / start) - 1) * 100;
};

const roundPct = (value: number | null) => (value === null ? null : Math.round(value * 100) / 100);

export const buildExcessReturnCards = (region: Region, payload: ChartPayload | null): ExcessReturnCard[] => {
  const benchmarkLabel = benchmarkLabelByRegion(region);
  const unavailable = PERIOD_MONTHS.map(({ label }) => ({
    label,
    benchmarkLabel,
    excessReturn: null,
    symbolReturn: null,
    benchmarkReturn: null,
  }));

  if (!payload || payload.candles.length === 0) return unavailable;

  const symbolSeries = toPriceSeries(payload);
  const benchmarkSeries = toBenchmarkSeries(payload);
  if (benchmarkSeries.length === 0) return unavailable;

  const symbolEnd = symbolSeries.at(-1) ?? null;
  const benchmarkEnd = benchmarkSeries.at(-1) ?? null;
  if (!symbolEnd || !benchmarkEnd) return unavailable;

  const endDate = toUtcDate(symbolEnd.time);
  const benchmarkEndPoint = findPointOnOrBefore(benchmarkSeries, endDate);
  if (!benchmarkEndPoint) return unavailable;

  return PERIOD_MONTHS.map(({ label, months }) => {
    const targetDate = new Date(endDate);
    targetDate.setUTCMonth(targetDate.getUTCMonth() - months);

    const symbolStart = findPointOnOrBefore(symbolSeries, targetDate);
    const benchmarkStart = findPointOnOrBefore(benchmarkSeries, targetDate);
    if (!symbolStart || !benchmarkStart) {
      return { label, benchmarkLabel, excessReturn: null, symbolReturn: null, benchmarkReturn: null };
    }

    const symbolReturn = roundPct(toReturnPct(symbolStart.value, symbolEnd.value));
    const benchmarkReturn = roundPct(toReturnPct(benchmarkStart.value, benchmarkEndPoint.value));
    const excessReturn =
      symbolReturn === null || benchmarkReturn === null ? null : roundPct(symbolReturn - benchmarkReturn);

    return { label, benchmarkLabel, excessReturn, symbolReturn, benchmarkReturn };
  });
};
