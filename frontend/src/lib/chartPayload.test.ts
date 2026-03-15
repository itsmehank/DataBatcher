import { describe, expect, it } from "vitest";

import { mergeChartPayload } from "./chartPayload";

describe("mergeChartPayload", () => {
  it("merges candles and indicators by time order", () => {
    const base = {
      symbol: "AAA",
      timeframe: "1D",
      from: "2026-01-02",
      to: "2026-01-03",
      candles: [
        { time: "2026-01-02", open: 1, high: 2, low: 1, close: 2 },
        { time: "2026-01-03", open: 2, high: 3, low: 1, close: 2 },
      ],
      volume: [{ time: "2026-01-03", value: 10 }],
      indicators: {
        sma_50: [{ time: "2026-01-03", value: 2 }],
      },
      meta: { rs_1y_high: { time: "2026-01-03", value: 2 } },
    };

    const incoming = {
      symbol: "AAA",
      timeframe: "1D",
      from: "2026-01-01",
      to: "2026-01-02",
      candles: [{ time: "2026-01-01", open: 1, high: 1, low: 1, close: 1 }],
      volume: [{ time: "2026-01-01", value: 8 }],
      indicators: {
        sma_50: [{ time: "2026-01-01", value: 1 }],
      },
    };

    const merged = mergeChartPayload(base, incoming);
    expect(merged.from).toBe("2026-01-01");
    expect(merged.to).toBe("2026-01-03");
    expect(merged.candles).toHaveLength(3);
    expect(merged.volume).toHaveLength(2);
    expect(merged.indicators.sma_50).toHaveLength(2);
    expect(merged.meta).toEqual(base.meta);
  });
});
