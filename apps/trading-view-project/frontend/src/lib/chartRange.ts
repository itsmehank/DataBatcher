import type { ChartPayload, TimeRangePreset } from "../types";

const toUtcDate = (isoDate: string) => new Date(`${isoDate}T00:00:00Z`);
const toIsoDate = (date: Date) => date.toISOString().slice(0, 10);

const subtractPreset = (endDate: string, preset: Exclude<TimeRangePreset, "ALL">) => {
  const target = toUtcDate(endDate);
  if (preset === "1W") {
    target.setUTCDate(target.getUTCDate() - 7);
    return toIsoDate(target);
  }
  if (preset === "1M") {
    target.setUTCMonth(target.getUTCMonth() - 1);
    return toIsoDate(target);
  }
  if (preset === "3M") {
    target.setUTCMonth(target.getUTCMonth() - 3);
    return toIsoDate(target);
  }
  target.setUTCFullYear(target.getUTCFullYear() - 1);
  return toIsoDate(target);
};

export const buildVisibleTimeRange = (payload: ChartPayload, preset: TimeRangePreset | null) => {
  if (!preset || preset === "ALL" || payload.candles.length === 0) {
    return null;
  }

  const earliest = payload.candles[0]?.time ?? payload.from;
  const latest = payload.candles[payload.candles.length - 1]?.time ?? payload.to;
  const targetFrom = subtractPreset(latest, preset);
  const from = earliest > targetFrom ? earliest : targetFrom;

  return { from, to: latest };
};
