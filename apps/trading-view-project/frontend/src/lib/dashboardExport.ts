import type { ChartPayload } from "../types";
import { EXPORT_CONFIG } from "./dashboardConfig";

const sliceLast = <T,>(items: T[], count: number) => (items.length <= count ? items : items.slice(-count));

const toCsv = (headers: string[], rows: Array<Array<string | number>>) => {
  const escapeCell = (value: string | number) => {
    const text = String(value);
    if (!/[",\n]/.test(text)) return text;
    return `"${text.replace(/"/g, '""')}"`;
  };

  return [headers.join(","), ...rows.map((row) => row.map(escapeCell).join(","))].join("\n");
};

export function buildDailyExportCsv(payload: ChartPayload, days = EXPORT_CONFIG.dailyDays): string {
  const volumeByTime = new Map(sliceLast(payload.volume, days).map((item) => [item.time, item.value]));
  const rows = sliceLast(payload.candles, days).map((item) => [
    item.time,
    item.open,
    item.high,
    item.low,
    item.close,
    volumeByTime.get(item.time) ?? "",
  ]);
  return toCsv(["time", "open", "high", "low", "close", "volume"], rows);
}

export function buildWeeklyExportCsv(payload: ChartPayload, weeks = EXPORT_CONFIG.weeklyWeeks): string {
  const volumeByTime = new Map(sliceLast(payload.volume, weeks).map((item) => [item.time, item.value]));
  const rows = sliceLast(payload.candles, weeks).map((item) => [
    item.time,
    item.open,
    item.high,
    item.low,
    item.close,
    volumeByTime.get(item.time) ?? "",
  ]);
  return toCsv(["time", "open", "high", "low", "close", "volume"], rows);
}

export function buildRsExportCsv(payload: ChartPayload, days = EXPORT_CONFIG.rsDays): string {
  const rows = sliceLast(payload.indicators.rs_line ?? [], days).map((item) => [item.time, item.value]);
  return toCsv(["time", "rs_line"], rows);
}
