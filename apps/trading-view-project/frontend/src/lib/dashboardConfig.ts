type EnvLike = Record<string, string | boolean | undefined>;

export type ExportConfig = {
  dailyDays: number;
  weeklyWeeks: number;
  rsDays: number;
};

const DEFAULT_EXPORT_CONFIG: ExportConfig = {
  dailyDays: 90,
  weeklyWeeks: 52,
  rsDays: 90,
};

const parsePositiveInt = (value: string | boolean | undefined, fallback: number) => {
  if (typeof value !== "string") return fallback;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return parsed;
};

export const resolveExportConfig = (env: EnvLike): ExportConfig => ({
  dailyDays: parsePositiveInt(env.VITE_EXPORT_DAILY_DAYS, DEFAULT_EXPORT_CONFIG.dailyDays),
  weeklyWeeks: parsePositiveInt(env.VITE_EXPORT_WEEKLY_WEEKS, DEFAULT_EXPORT_CONFIG.weeklyWeeks),
  rsDays: parsePositiveInt(env.VITE_EXPORT_RS_DAYS, DEFAULT_EXPORT_CONFIG.rsDays),
});

export const EXPORT_CONFIG = resolveExportConfig(import.meta.env as EnvLike);
