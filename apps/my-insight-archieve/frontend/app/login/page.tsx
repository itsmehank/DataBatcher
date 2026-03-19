'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/use-auth';
import type { LoginResponse } from '../../types/auth';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, username: authenticatedUser, logout, refreshAuth } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (isAuthenticated) {
      const timer = window.setTimeout(() => {
        router.replace('/');
        router.refresh();
      }, 500);
      return () => window.clearTimeout(timer);
    }
  }, [isAuthenticated, router]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMessage('');
    try {
      const result = await api<LoginResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      await refreshAuth();
      setMessage(`로그인 완료: ${result.admin.username}`);
      router.replace('/');
      router.refresh();
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  async function onLogout() {
    await logout();
    setMessage('로그아웃되었습니다.');
  }

  if (isLoading) {
    return (
      <div className="page-center">
        <section className="panel grid center-card">
          <p className="muted">인증 상태를 확인 중입니다.</p>
        </section>
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="page-center">
        <section className="panel grid center-card">
          <div>
            <h1 className="section-title" style={{ fontSize: '32px' }}>
              이미 로그인 상태입니다
            </h1>
            <p className="section-subtitle">{authenticatedUser} 계정으로 접속 중입니다.</p>
          </div>
          <div className="actions">
            <button type="button" onClick={() => router.replace('/')}>
              아카이브로 이동
            </button>
            <button type="button" className="secondary" onClick={() => onLogout().catch(() => undefined)} style={{ maxWidth: 140 }}>
              로그아웃
            </button>
          </div>
          {message ? <p className="muted">{message}</p> : null}
        </section>
      </div>
    );
  }

  return (
    <div className="page-center">
      <section className="panel grid center-card">
        <div>
          <h1 className="section-title" style={{ fontSize: '38px' }}>
            기록장을 위한 로그인
          </h1>
          <p className="section-subtitle">조용한 기록 공간을 안전하게 유지하기 위해 인증이 필요합니다.</p>
        </div>
        <form className="grid" onSubmit={onSubmit}>
          <input
            type="text"
            placeholder="아이디"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            aria-label="아이디"
          />
          <input
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <div className="actions">
            <button type="submit">로그인하고 이어쓰기</button>
            <button type="button" className="secondary" onClick={() => onLogout().catch(() => undefined)} style={{ maxWidth: 140 }}>
              로그아웃
            </button>
          </div>
        </form>
        {message ? <p className="muted">{message}</p> : null}
      </section>
    </div>
  );
}
