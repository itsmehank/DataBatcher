'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from './api';
import type { MeResponse } from '../types/auth';

type AuthState = {
  isLoading: boolean;
  isAuthenticated: boolean;
  username: string;
};

const INITIAL_STATE: AuthState = {
  isLoading: true,
  isAuthenticated: false,
  username: '',
};

export function useAuth() {
  const [state, setState] = useState<AuthState>(INITIAL_STATE);

  const refreshAuth = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true }));
    try {
      const me = await api<MeResponse>('/auth/me');
      setState({ isLoading: false, isAuthenticated: true, username: me.username });
    } catch {
      setState({ isLoading: false, isAuthenticated: false, username: '' });
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api('/auth/logout', { method: 'POST' });
    } catch {
      // Best-effort: cookie cleared server-side; proceed regardless
    }
    setState({ isLoading: false, isAuthenticated: false, username: '' });
  }, []);

  useEffect(() => {
    refreshAuth().catch(() => undefined);
  }, [refreshAuth]);

  return {
    ...state,
    refreshAuth,
    logout,
  };
}
