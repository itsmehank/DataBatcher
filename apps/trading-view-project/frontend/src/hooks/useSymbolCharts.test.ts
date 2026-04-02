import { describe, expect, it } from "vitest";

import { createSymbolChartUiState } from "./useSymbolCharts";

describe("useSymbolCharts helpers", () => {
  it("creates a reset state that clears stale payloads and load-more flags", () => {
    expect(createSymbolChartUiState()).toEqual({
      daily: null,
      weekly: null,
      dailyHasMoreHistory: true,
      weeklyHasMoreHistory: true,
      dailyLoadingMoreHistory: false,
      weeklyLoadingMoreHistory: false,
      loading: false,
    });
  });
});
