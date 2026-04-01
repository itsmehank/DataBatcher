import { describe, expect, it } from "vitest";

import type { ChartPayload } from "../types";
import { buildDailyExportCsv, buildRsExportCsv, buildWeeklyExportCsv } from "./dashboardExport";

const payload: ChartPayload = {
  symbol: "AAA",
  timeframe: "1D",
  from: "2026-01-01",
  to: "2026-03-31",
  candles: Array.from({ length: 95 }, (_, index) => ({
    time: `2026-03-${String(index + 1).padStart(2, "0")}`,
    open: index + 1,
    high: index + 2,
    low: index,
    close: index + 1.5,
  })),
  volume: Array.from({ length: 95 }, (_, index) => ({
    time: `2026-03-${String(index + 1).padStart(2, "0")}`,
    value: 1000 + index,
  })),
  indicators: {
    rs_line: Array.from({ length: 95 }, (_, index) => ({
      time: `2026-03-${String(index + 1).padStart(2, "0")}`,
      value: 1 + index / 100,
    })),
  },
};

describe("dashboard export helpers", () => {
  it("builds daily csv with latest 90 rows", () => {
    const csv = buildDailyExportCsv(payload);
    const lines = csv.split("\n");
    expect(lines).toHaveLength(91);
    expect(lines[0]).toBe("time,open,high,low,close,volume");
    expect(lines[1]).toContain("2026-03-06");
    expect(lines.at(-1)).toContain("2026-03-95");
  });

  it("builds weekly csv with latest 52 rows", () => {
    const csv = buildWeeklyExportCsv(payload);
    const lines = csv.split("\n");
    expect(lines).toHaveLength(53);
    expect(lines[0]).toBe("time,open,high,low,close,volume");
    expect(lines[1]).toContain("2026-03-44");
  });

  it("builds rs csv with latest 90 rows", () => {
    const csv = buildRsExportCsv(payload);
    const lines = csv.split("\n");
    expect(lines).toHaveLength(91);
    expect(lines[0]).toBe("time,rs_line");
    expect(lines[1]).toContain("2026-03-06");
  });
});
