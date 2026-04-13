import { describe, expect, it } from "vitest";

import type { ChartPayload } from "../types";
import { buildVisibleTimeRange } from "./chartRange";

const payload: ChartPayload = {
  symbol: "AAA",
  timeframe: "1D",
  from: "2025-01-01",
  to: "2026-04-10",
  candles: [
    { time: "2025-01-01", open: 10, high: 10, low: 10, close: 10 },
    { time: "2026-01-10", open: 12, high: 12, low: 12, close: 12 },
    { time: "2026-03-10", open: 13, high: 13, low: 13, close: 13 },
    { time: "2026-04-10", open: 15, high: 15, low: 15, close: 15 },
  ],
  volume: [],
  indicators: {},
};

describe("chart range helpers", () => {
  it("returns null for ALL", () => {
    expect(buildVisibleTimeRange(payload, "ALL")).toBeNull();
  });

  it("builds a 3M visible range anchored to the latest candle", () => {
    expect(buildVisibleTimeRange(payload, "3M")).toEqual({ from: "2026-01-10", to: "2026-04-10" });
  });

  it("clamps range to the earliest available candle", () => {
    expect(buildVisibleTimeRange(payload, "1Y")).toEqual({ from: "2025-04-10", to: "2026-04-10" });
  });
});
