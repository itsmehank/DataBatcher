import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { authApi } from "../api";
import type { UserRole } from "../types";

type AuthState = {
  checked: boolean;
  authenticated: boolean;
  username: string | null;
  role: UserRole | null;
};

type AuthContextValue = AuthState & {
  isEditor: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const INITIAL_STATE: AuthState = {
  checked: false,
  authenticated: false,
  username: null,
  role: null,
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(INITIAL_STATE);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await authApi.me();
        if (!mounted) return;
        if (res.authenticated && res.username && res.role) {
          setState({
            checked: true,
            authenticated: true,
            username: res.username,
            role: res.role as UserRole,
          });
        } else {
          setState({ ...INITIAL_STATE, checked: true });
        }
      } catch {
        if (!mounted) return;
        setState({ ...INITIAL_STATE, checked: true });
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await authApi.login(username, password);
    setState({
      checked: true,
      authenticated: true,
      username: res.username,
      role: res.role as UserRole,
    });
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setState({ ...INITIAL_STATE, checked: true });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      isEditor: state.role === "editor",
      login,
      logout,
    }),
    [state, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
