'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, getToken } from './api';
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

function emitAuthChanged() {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function setAuthToken(token: string) {
  localStorage.setItem('accessToken', token);
  emitAuthChanged();
}

export function clearAuthToken() {
  localStorage.removeItem('accessToken');
  emitAuthChanged();
}

export function useAuth() {
  const [state, setState] = useState<AuthState>(INITIAL_STATE);

  const refreshAuth = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setState({ isLoading: false, isAuthenticated: false, username: '' });
      return;
    }

    setState((prev) => ({ ...prev, isLoading: true }));
    try {
      const me = await api<MeResponse>('/auth/me');
      setState({ isLoading: false, isAuthenticated: true, username: me.username });
    } catch {
      localStorage.removeItem('accessToken');
      setState({ isLoading: false, isAuthenticated: false, username: '' });
    }
  }, []);

  const logout = useCallback(() => {
    clearAuthToken();
    setState({ isLoading: false, isAuthenticated: false, username: '' });
  }, []);

  useEffect(() => {
    refreshAuth().catch(() => undefined);

    function onStorage(event: StorageEvent) {
      if (event.key === 'accessToken') {
        refreshAuth().catch(() => undefined);
      }
    }

    function onAuthChanged() {
      refreshAuth().catch(() => undefined);
    }

    window.addEventListener('storage', onStorage);
    window.addEventListener(AUTH_CHANGED_EVENT, onAuthChanged);

    return () => {
      window.removeEventListener('storage', onStorage);
      window.removeEventListener(AUTH_CHANGED_EVENT, onAuthChanged);
    };
  }, [refreshAuth]);

  return {
    ...state,
    refreshAuth,
    logout,
  };
}
