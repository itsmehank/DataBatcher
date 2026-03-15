import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

const THEME_KEY = "minervini-ui-theme";

const savedTheme = window.localStorage.getItem(THEME_KEY);
if (savedTheme === "ocean" || savedTheme === "slate" || savedTheme === "paper") {
  document.documentElement.dataset.theme = savedTheme;
} else {
  document.documentElement.dataset.theme = "paper";
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
