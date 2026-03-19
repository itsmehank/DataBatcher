import type { ChartPayload, ListType, ListViewItem, MinerviniRow, Region } from "./types";

const qs = (params: Record<string, string | undefined>) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v) search.set(k, v);
  });
  return search.toString();
};

const withQuery = (path: string, params?: Record<string, string | undefined>) => {
  if (!params) return path;
  const query = qs(params);
  return query ? `${path}?${query}` : path;
};

async function parseErrorMessage(res: Response): Promise<string> {
  const text = await res.text();
  if (!text) return `Request failed: ${res.status}`;
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed.detail === "string" && parsed.detail) {
      return parsed.detail;
    }
  } catch {
    // Fallback to raw text.
  }
  return text;
}

async function requestJson<T>(
  path: string,
  options?: {
    method?: "GET" | "POST" | "PATCH";
    params?: Record<string, string | undefined>;
    body?: unknown;
    signal?: AbortSignal;
  }
): Promise<T> {
  const res = await fetch(withQuery(path, options?.params), {
    method: options?.method ?? "GET",
    headers: options?.body ? { "Content-Type": "application/json" } : undefined,
    body: options?.body ? JSON.stringify(options.body) : undefined,
    signal: options?.signal,
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(await parseErrorMessage(res));
  }
  return res.json() as Promise<T>;
}

export const api = {
  getDates: (region: Region, signal?: AbortSignal) =>
    requestJson<string[]>("/api/options/dates", { params: { region }, signal }),
  getMarkets: (region: Region, signal?: AbortSignal) =>
    requestJson<string[]>("/api/options/markets", { params: { region }, signal }),
  getCategories: (region: Region, market: string) =>
    requestJson<string[]>("/api/options/categories", { params: { region, market } }),
  getSymbols: (region: Region, market: string, category: string) =>
    requestJson<string[]>("/api/symbols", { params: { region, market, category } }),
  getMinervini: (region: Region, date: string, market: string) =>
    requestJson<MinerviniRow[]>("/api/minervini", { params: { region, date, market } }),
  updateMinerviniListType: (
    region: Region,
    date: string,
    market: string,
    symbol: string,
    listType: ListType | null
  ) =>
    requestJson<{ ok: boolean; action: string }>("/api/minervini/list-type", {
      method: "POST",
      body: { region, date, market, symbol, list_type: listType },
    }),
  getListViewDates: (region: Region) => requestJson<string[]>("/api/list-view/dates", { params: { region } }),
  getListViewItems: (region: Region, date: string, listCategory: ListType | "all") =>
    requestJson<ListViewItem[]>("/api/list-view/items", { params: { region, date, listCategory } }),
  updateListViewItem: (
    payload: {
      region: Region;
      date: string;
      market: string;
      symbol: string;
      trigger_price?: number | null;
      stop_price?: number | null;
      status_tag?: "A" | "B" | "C" | "D" | "E" | null;
      memo?: string | null;
    }
  ) =>
    requestJson<{ ok: boolean; action: string }>("/api/list-view/item", {
      method: "PATCH",
      body: payload,
    }),
  getDaily: (region: Region, symbol: string, from: string, to: string, signal?: AbortSignal) =>
    requestJson<ChartPayload>("/api/chart/daily", { params: { region, symbol, from, to }, signal }),
  getBenchmarkDaily: (region: Region, from: string, to: string, signal?: AbortSignal) =>
    requestJson<ChartPayload>("/api/chart/benchmark-daily", { params: { region, from, to }, signal }),
  getWeekly: (region: Region, symbol: string, from: string, to: string, signal?: AbortSignal) =>
    requestJson<ChartPayload>("/api/chart/weekly", { params: { region, symbol, from, to }, signal }),
};

export const authApi = {
  login: (username: string, password: string) =>
    requestJson<{ ok: boolean; username: string; role: string }>("/api/auth/login", {
      method: "POST",
      body: { username, password },
    }),
  logout: () => requestJson<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  me: () => requestJson<{ authenticated: boolean; username?: string; role?: string }>("/api/auth/me"),
};
