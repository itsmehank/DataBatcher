import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const from = (location.state as { from?: string } | null)?.from || "/dashboard";

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="app-root" style={{ display: "flex", justifyContent: "center", paddingTop: "4rem" }}>
      <section className="panel" style={{ width: "100%", maxWidth: "380px" }}>
        <div className="panel-header">
          <h2>Sign In</h2>
        </div>
        <form onSubmit={onSubmit} style={{ padding: "1.25rem 1rem" }}>
          {error ? <div className="error-box">{error}</div> : null}
          <label className="filter-item" style={{ marginBottom: "0.75rem" }}>
            <span>Username</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              disabled={submitting}
              style={{
                background: "var(--control-bg)",
                color: "var(--text)",
                border: "1px solid var(--line)",
                borderRadius: "0.45rem",
                minHeight: "2.2rem",
                padding: "0 0.55rem",
                width: "100%",
              }}
            />
          </label>
          <label className="filter-item" style={{ marginBottom: "1rem" }}>
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              disabled={submitting}
              style={{
                background: "var(--control-bg)",
                color: "var(--text)",
                border: "1px solid var(--line)",
                borderRadius: "0.45rem",
                minHeight: "2.2rem",
                padding: "0 0.55rem",
                width: "100%",
              }}
            />
          </label>
          <button
            type="submit"
            disabled={submitting}
            style={{
              width: "100%",
              padding: "0.5rem",
              border: "none",
              borderRadius: "0.45rem",
              background: "var(--accent)",
              color: "var(--accent-text)",
              fontSize: "0.88rem",
              fontWeight: 600,
              cursor: submitting ? "wait" : "pointer",
              opacity: submitting ? 0.65 : 1,
            }}
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </section>
    </main>
  );
}
