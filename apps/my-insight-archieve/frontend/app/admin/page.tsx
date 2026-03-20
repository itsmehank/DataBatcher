'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { formatDateShort } from '../../lib/date';
import { isUnauthorizedError } from '../../lib/errors';
import { useAuth } from '../../lib/use-auth';

type BackupStatus = {
  lastBackup: string | null;
  backupDir: string;
};

type BackupResult = {
  success?: boolean;
  message?: string;
};

export default function AdminPage() {
  const { isAuthenticated, isLoading: isAuthLoading, refreshAuth } = useAuth();
  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [runningBackup, setRunningBackup] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const loadStatus = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      setStatus(null);
      return;
    }

    setLoading(true);
    setError('');

    try {
      const data = await api<BackupStatus>('/admin/backup/status');
      setStatus(data);
    } catch (err) {
      const typedErr = err as Error;
      if (isUnauthorizedError(typedErr)) {
        refreshAuth().catch(() => undefined);
      }
      setError(typedErr.message || '백업 상태를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, refreshAuth]);

  useEffect(() => {
    if (isAuthLoading) {
      return;
    }
    loadStatus().catch(() => undefined);
  }, [isAuthLoading, loadStatus]);

  useEffect(() => {
    if (!drawerOpen) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDrawerOpen(false);
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [drawerOpen]);

  const runBackup = useCallback(async () => {
    if (!isAuthenticated) {
      setMessage('관리자 로그인 후 사용할 수 있습니다.');
      return;
    }

    setRunningBackup(true);
    setError('');
    setMessage('');

    try {
      const result = await api<BackupResult>('/admin/backup/export', { method: 'POST' });
      await loadStatus();
      setMessage(result.message || '백업을 완료했습니다.');
    } catch (err) {
      const typedErr = err as Error;
      if (isUnauthorizedError(typedErr)) {
        setMessage('관리자 로그인 후 사용할 수 있습니다.');
        refreshAuth().catch(() => undefined);
      } else {
        setError(typedErr.message || '백업 실행에 실패했습니다.');
      }
    } finally {
      setRunningBackup(false);
    }
  }, [isAuthenticated, loadStatus, refreshAuth]);

  if (isAuthLoading) {
    return <div className="v2-loading">인증 상태를 확인 중입니다...</div>;
  }

  if (!isAuthenticated) {
    return (
      <section className="v2-admin-page">
        <header className="v2-header">
          <div className="v2-header-top">
            <h1 className="v2-page-title">어드민</h1>
          </div>
        </header>

        <div className="v2-admin-guard">
          관리자 로그인 후 사용할 수 있습니다. <Link href="/login">로그인하러 가기</Link>
        </div>
      </section>
    );
  }

  return (
    <>
      <header className="v2-header">
        <div className="v2-header-top">
          <h1 className="v2-page-title">어드민</h1>
          <span className="v2-page-count">백업 관리</span>
        </div>
      </header>

      <section className="v2-admin-page">
        <div className="v2-section-label">백업 상태</div>

        {loading ? <div className="v2-loading">백업 상태를 읽는 중입니다...</div> : null}
        {!loading && error ? <div className="v2-error">{error}</div> : null}

        {!loading && !error && status ? (
          <div className="v2-admin-status">
            <div className="v2-admin-item">
              <span className="v2-admin-key">최근 백업</span>
              <span className="v2-admin-value">
                {status.lastBackup ? `${formatDateShort(status.lastBackup)} ${new Date(status.lastBackup).toLocaleTimeString('ko-KR')}` : '기록 없음'}
              </span>
            </div>
            <div className="v2-admin-item">
              <span className="v2-admin-key">저장 경로</span>
              <span className="v2-admin-value v2-admin-dir">{status.backupDir}</span>
            </div>
          </div>
        ) : null}

        {message ? <div className="v2-admin-message">{message}</div> : null}
      </section>

      <button type="button" className="v2-fab" onClick={() => setDrawerOpen(true)} aria-label="백업 실행">
        +
      </button>

      <div
        className={`v2-drawer-overlay${drawerOpen ? ' open' : ''}`}
        onClick={() => setDrawerOpen(false)}
        aria-hidden={drawerOpen ? 'false' : 'true'}
      />
      <aside className={`v2-drawer${drawerOpen ? ' open' : ''}`} aria-hidden={drawerOpen ? 'false' : 'true'}>
        <div className="v2-drawer-header">
          <h2>백업 실행</h2>
        </div>

        <div className="v2-drawer-body">
          <p className="v2-admin-copy">최신 아카이브 데이터를 백업 파일로 저장합니다.</p>
          <p className="v2-admin-copy">기존 백업 파일은 최신 파일로 교체됩니다.</p>

          <div className="v2-drawer-actions">
            <button type="button" className="v2-drawer-cancel-btn" onClick={() => setDrawerOpen(false)}>
              닫기
            </button>
            <button
              type="button"
              className="v2-submit-btn"
              disabled={runningBackup}
              onClick={() => runBackup().catch(() => undefined)}
            >
              {runningBackup ? '백업 중...' : '백업 실행'}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
