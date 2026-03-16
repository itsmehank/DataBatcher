import { useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import ListViewPage from "./pages/ListViewPage";
import type { ThemeMode } from "./types";

const THEME_KEY = "minervini-ui-theme";
const DEFAULT_THEME: ThemeMode = "paper";

const THEME_OPTIONS: { key: ThemeMode; label: string }[] = [
  { key: "ocean", label: "Ocean" },
  { key: "slate", label: "Slate" },
  { key: "paper", label: "Paper" },
];

export default function App() {
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return DEFAULT_THEME;
    const saved = window.localStorage.getItem(THEME_KEY);
    if (saved === "ocean" || saved === "slate" || saved === "paper") {
      return saved;
    }
    return DEFAULT_THEME;
  });

  useEffect(() => {
    document.documentElement.dataset.theme = themeMode;
    window.localStorage.setItem(THEME_KEY, themeMode);
  }, [themeMode]);

  return (
    <>
      <nav className="main-nav">
        <div className="nav-links">
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/list-view">List View</NavLink>
        </div>
        <div className="theme-switcher" role="group" aria-label="Theme mode">
          {THEME_OPTIONS.map((option) => (
            <button
              key={option.key}
              type="button"
              className={option.key === themeMode ? "active" : ""}
              onClick={() => setThemeMode(option.key)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </nav>
      <Routes>
        <Route path="/dashboard" element={<DashboardPage themeMode={themeMode} />} />
        <Route path="/list-view" element={<ListViewPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </>
  );
}
