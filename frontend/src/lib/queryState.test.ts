import { describe, expect, it } from "vitest";

import { getInitialDashboardState, getInitialListViewState } from "./queryState";

describe("query state helpers", () => {
  it("parses dashboard query values with defaults", () => {
    const params = new URLSearchParams("region=KR&date=2026-03-01&market=KOSPI&category=A&symbol=005930");
    expect(getInitialDashboardState(params)).toEqual({
      region: "KR",
      date: "2026-03-01",
      market: "KOSPI",
      category: "A",
      symbol: "005930",
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
});
