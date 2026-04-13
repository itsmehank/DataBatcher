import type { ListType, MinerviniRow, Region } from "../types";

export type DashboardQueryState = {
  region: Region;
  date: string;
  market: string;
  listCategory: ListType | "all";
  symbol: string;
};

export const buildDashboardSearchParams = ({ region, date, market, listCategory, symbol }: DashboardQueryState) => {
  const nextParams: Record<string, string> = { region };
  if (date) nextParams.date = date;
  if (market) nextParams.market = market;
  if (listCategory) nextParams.listCategory = listCategory;
  if (symbol) nextParams.symbol = symbol;
  return nextParams;
};

export const pickDashboardSymbol = (rows: MinerviniRow[], currentSymbol: string) => {
  if (currentSymbol && rows.some((row) => row.ticker === currentSymbol)) {
    return currentSymbol;
  }
  return rows[0]?.ticker ?? "";
};

export const getSelectedDashboardRow = (rows: MinerviniRow[], currentSymbol: string) =>
  rows.find((row) => row.ticker === currentSymbol) ?? null;

export const getDashboardTickerNeighbors = (rows: MinerviniRow[], currentSymbol: string) => {
  const currentIndex = rows.findIndex((row) => row.ticker === currentSymbol);
  if (currentIndex < 0) {
    return {
      previousTicker: null,
      nextTicker: rows[0]?.ticker ?? null,
    };
  }

  return {
    previousTicker: currentIndex > 0 ? rows[currentIndex - 1].ticker : null,
    nextTicker: currentIndex < rows.length - 1 ? rows[currentIndex + 1].ticker : null,
  };
};

export const applyDashboardListTypeChange = (
  rows: MinerviniRow[],
  targetRow: MinerviniRow,
  nextType: ListType | null,
  listCategory: ListType | "all"
) => {
  const nextRows = rows.map((row) =>
    row.ticker === targetRow.ticker && row.market === targetRow.market ? { ...row, list_type: nextType } : row
  );

  if (listCategory === "all") {
    return nextRows;
  }

  return nextRows.filter((row) => row.list_type === listCategory);
};
