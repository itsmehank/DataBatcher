'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from './api';
import type { MeResponse } from '../types/auth';

const AUTH_CHANGED_EVENT = 'insight-auth-changed';

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

export function notifyAuthChanged() {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

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
    notifyAuthChanged();
  }, []);

  useEffect(() => {
    refreshAuth().catch(() => undefined);

    function onAuthChanged() {
      refreshAuth().catch(() => undefined);
    }

    window.addEventListener(AUTH_CHANGED_EVENT, onAuthChanged);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, onAuthChanged);
  }, [refreshAuth]);

  return {
    ...state,
    refreshAuth,
    logout,
  };
}
