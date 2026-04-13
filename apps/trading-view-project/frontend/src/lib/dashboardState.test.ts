import { describe, expect, it } from "vitest";

import type { MinerviniRow } from "../types";
import {
  applyDashboardListTypeChange,
  buildDashboardSearchParams,
  getDashboardTickerNeighbors,
  getSelectedDashboardRow,
  pickDashboardSymbol,
} from "./dashboardState";

const rows: MinerviniRow[] = [
  {
    ticker: "AAPL",
    name: "Apple",
    market: "NASDAQ",
    sector: "Tech",
    rs_rating: 98,
    is_blue_dot: 1,
    category_val: "A",
    list_type: "focus",
  },
  {
    ticker: "MSFT",
    name: "Microsoft",
    market: "NASDAQ",
    sector: "Tech",
    rs_rating: 96,
    is_blue_dot: 0,
    category_val: "A",
    list_type: "focus",
  },
];

describe("dashboard state helpers", () => {
  it("builds dashboard search params including symbol", () => {
    expect(
      buildDashboardSearchParams({
        region: "US",
        date: "2026-03-01",
        market: "NASDAQ",
        listCategory: "focus",
        symbol: "AAPL",
      })
    ).toEqual({
      region: "US",
      date: "2026-03-01",
      market: "NASDAQ",
      listCategory: "focus",
      symbol: "AAPL",
    });
  });

  it("drops a row immediately when its next list type no longer matches the active filter", () => {
    expect(applyDashboardListTypeChange(rows, rows[0], "action", "focus")).toEqual([rows[1]]);
  });

  it("falls back to the first row when the selected symbol disappears", () => {
    expect(pickDashboardSymbol([rows[1]], "AAPL")).toBe("MSFT");
    expect(pickDashboardSymbol([], "AAPL")).toBe("");
  });

  it("finds the selected row from the current symbol", () => {
    expect(getSelectedDashboardRow(rows, "AAPL")).toEqual(rows[0]);
    expect(getSelectedDashboardRow(rows, "NVDA")).toBeNull();
  });

  it("returns previous and next ticker neighbors", () => {
    expect(getDashboardTickerNeighbors(rows, "AAPL")).toEqual({ previousTicker: null, nextTicker: "MSFT" });
    expect(getDashboardTickerNeighbors(rows, "MSFT")).toEqual({ previousTicker: "AAPL", nextTicker: null });
    expect(getDashboardTickerNeighbors(rows, "NVDA")).toEqual({ previousTicker: null, nextTicker: "AAPL" });
  });
});
