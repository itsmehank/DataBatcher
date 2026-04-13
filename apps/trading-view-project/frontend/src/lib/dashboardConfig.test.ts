import { describe, expect, it } from "vitest";

import { resolveExportConfig } from "./dashboardConfig";

describe("dashboard export config", () => {
  it("uses defaults when env values are missing", () => {
    expect(resolveExportConfig({})).toEqual({ dailyDays: 90, weeklyWeeks: 52, rsDays: 90 });
  });

  it("parses positive integer env values", () => {
    expect(
      resolveExportConfig({
        VITE_EXPORT_DAILY_DAYS: "120",
        VITE_EXPORT_WEEKLY_WEEKS: "78",
        VITE_EXPORT_RS_DAYS: "45",
      }),
    ).toEqual({ dailyDays: 120, weeklyWeeks: 78, rsDays: 45 });
  });

  it("falls back for invalid env values", () => {
    expect(
      resolveExportConfig({
        VITE_EXPORT_DAILY_DAYS: "-1",
        VITE_EXPORT_WEEKLY_WEEKS: "abc",
        VITE_EXPORT_RS_DAYS: "0",
      }),
    ).toEqual({ dailyDays: 90, weeklyWeeks: 52, rsDays: 90 });
  });
});
