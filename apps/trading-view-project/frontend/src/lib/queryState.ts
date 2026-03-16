import type { ListType, Region } from "../types";

const parseRegion = (value: string | null): Region => (value === "KR" ? "KR" : "US");

export const getInitialDashboardState = (search: URLSearchParams) => ({
  region: parseRegion(search.get("region")),
  date: search.get("date") || "",
  market: search.get("market") || "",
  category: search.get("category") || "",
  symbol: search.get("symbol") || "",
});

const parseListCategory = (value: string | null): ListType | "all" => {
  if (value === "focus" || value === "action" || value === "pass") {
    return value;
  }
  return "all";
};

export const getInitialListViewState = (search: URLSearchParams) => ({
  region: parseRegion(search.get("region")),
  date: search.get("date") || "",
  listCategory: parseListCategory(search.get("listCategory")),
});
