export type Region = "US" | "KR";
export type ListType = "focus" | "action" | "pass";
export type ThemeMode = "ocean" | "slate" | "paper";
export type UserRole = "viewer" | "editor";
export type TimeRangePreset = "1W" | "1M" | "3M" | "1Y" | "ALL";
export type AuthUser = { username: string; role: UserRole };

export type MinerviniRow = {
  ticker: string;
  name: string | null;
  market: string;
  sector: string | null;
  rs_rating: number | null;
  is_blue_dot: number | null;
  category_val: string;
  list_type: ListType | null;
};

export type ListViewItem = {
  symbol: string;
  name: string | null;
  market: string;
  list_type: ListType;
  sector: string | null;
  rs_rating: number | null;
  trigger_price: number | null;
  stop_price: number | null;
  status_tag: "A" | "B" | "C" | "D" | "E" | null;
  memo: string | null;
};

export type SymbolOption = {
  symbol: string;
  name: string | null;
};

export type CandlePoint = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

export type HistogramPoint = {
  time: string;
  value: number;
  color?: string;
};

export type LinePoint = {
  time: string;
  value: number;
};

export type ChartPayload = {
  symbol: string;
  timeframe: string;
  from: string;
  to: string;
  candles: CandlePoint[];
  volume: HistogramPoint[];
  indicators: Record<string, LinePoint[]>;
  meta?: {
    rs_1y_high?: {
      time: string;
      value: number;
    } | null;
  };
};
