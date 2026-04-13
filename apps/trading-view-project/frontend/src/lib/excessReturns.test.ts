import { describe, expect, it } from "vitest";

import type { ChartPayload } from "../types";
import { buildExcessReturnCards } from "./excessReturns";

const buildPayload = (): ChartPayload => ({
  symbol: "AAA",
  timeframe: "1D",
  from: "2025-10-10",
  to: "2026-04-10",
  candles: [
    { time: "2025-10-10", open: 100, high: 101, low: 99, close: 100 },
    { time: "2025-11-10", open: 105, high: 106, low: 104, close: 105 },
    { time: "2026-01-10", open: 115, high: 116, low: 114, close: 115 },
    { time: "2026-04-10", open: 130, high: 131, low: 129, close: 130 },
  ],
  volume: [],
  indicators: {
    benchmark_close: [
      { time: "2025-10-10", value: 100 },
      { time: "2025-11-10", value: 102 },
      { time: "2026-01-10", value: 108 },
      { time: "2026-04-10", value: 120 },
    ],
  },
});

describe("excess return cards", () => {
  it("builds 1m/3m/6m cards from price and benchmark series", () => {
    const cards = buildExcessReturnCards("US", buildPayload());
    expect(cards.map((card) => card.label)).toEqual(["1M", "3M", "6M"]);
    expect(cards[0].benchmarkLabel).toBe("S&P 500");
    expect(cards[0].excessReturn).toBeCloseTo(1.93, 2);
    expect(cards[1].excessReturn).toBeCloseTo(1.93, 2);
    expect(cards[2].excessReturn).toBeCloseTo(10, 2);
  });

  it("returns N/A cards when benchmark data is missing", () => {
    const payload = buildPayload();
    payload.indicators = {};
    const cards = buildExcessReturnCards("KR", payload);
    expect(cards.every((card) => card.excessReturn === null)).toBe(true);
    expect(cards[0].benchmarkLabel).toBe("KOSPI");
  });
});
