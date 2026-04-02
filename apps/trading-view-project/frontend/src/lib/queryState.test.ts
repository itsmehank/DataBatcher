import { describe, expect, it } from "vitest";

import { getInitialChartViewState, getInitialDashboardState, getInitialListViewState } from "./queryState";

describe("query state helpers", () => {
  it("parses dashboard query values with defaults", () => {
    const params = new URLSearchParams("region=KR&date=2026-03-01&market=KOSPI&listCategory=focus");
    expect(getInitialDashboardState(params)).toEqual({
      region: "KR",
      date: "2026-03-01",
      market: "KOSPI",
      listCategory: "focus",
      symbol: "",
    });
  });

  it("falls back for invalid query values", () => {
    const params = new URLSearchParams("region=JP&listCategory=invalid");
    expect(getInitialListViewState(params)).toEqual({
      region: "US",
      date: "",
      listCategory: "all",
    });
  });

  it("parses chart view query values with defaults", () => {
    const params = new URLSearchParams("region=KR&market=KOSPI&category=A&symbol=005930");
    expect(getInitialChartViewState(params)).toEqual({
      region: "KR",
      market: "KOSPI",
      category: "A",
      symbol: "005930",
    });
  });

  it("parses dashboard symbol query when present", () => {
    const params = new URLSearchParams("region=US&date=2026-03-01&market=NASDAQ&listCategory=focus&symbol=AAPL");
    expect(getInitialDashboardState(params)).toEqual({
      region: "US",
      date: "2026-03-01",
      market: "NASDAQ",
      listCategory: "focus",
      symbol: "AAPL",
    });
  });
});
