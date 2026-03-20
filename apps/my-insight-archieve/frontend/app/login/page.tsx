'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';
import { api } from '../../lib/api';
import { notifyAuthChanged, useAuth } from '../../lib/use-auth';
import type { LoginResponse } from '../../types/auth';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, username, logout, refreshAuth } = useAuth();
  const [id, setId] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    setMessage('');

    try {
      const result = await api<LoginResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username: id, password }),
      });
      await refreshAuth();
      notifyAuthChanged();
      setMessage(`${result.admin.username}님, 로그인되었습니다.`);
      router.replace('/');
      router.refresh();
    } catch (err) {
      setError((err as Error).message || '로그인에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    setMessage('로그아웃되었습니다.');
    setError('');
  };

  if (isLoading) {
    return <div className="v2-loading">인증 상태를 확인 중입니다...</div>;
  }

  if (isAuthenticated) {
    return (
      <section className="v2-login-page">
        <div className="v2-login-card">
          <h1 className="v2-page-title">이미 로그인 상태입니다</h1>
          <p className="v2-login-subtitle">{username} 계정으로 접속 중입니다.</p>

          <div className="v2-login-actions">
            <Link href="/" className="v2-login-link-btn">
              아카이브로 이동
            </Link>
            <button type="button" className="v2-drawer-cancel-btn" onClick={() => handleLogout().catch(() => undefined)}>
              로그아웃
            </button>
          </div>

          {message ? <p className="v2-admin-message">{message}</p> : null}
        </div>
      </section>
    );
  }

  return (
    <section className="v2-login-page">
      <div className="v2-login-card">
        <h1 className="v2-page-title">관리자 로그인</h1>
        <p className="v2-login-subtitle">기록을 안전하게 관리하려면 인증이 필요합니다.</p>

        <form className="v2-login-form" onSubmit={handleSubmit}>
          <label className="v2-drawer-field">
            <span className="v2-drawer-label">아이디</span>
            <input
              className="v2-drawer-input"
              value={id}
              onChange={(e) => setId(e.target.value)}
              required
              autoComplete="username"
            />
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">비밀번호</span>
            <input
              type="password"
              className="v2-drawer-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>

          {error ? <div className="v2-error">{error}</div> : null}
          {message ? <div className="v2-admin-message">{message}</div> : null}

          <button type="submit" className="v2-submit-btn" disabled={submitting}>
            {submitting ? '로그인 중...' : '로그인'}
          </button>
        </form>
      </div>
    </section>
  );
}
