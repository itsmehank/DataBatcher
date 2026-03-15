'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '../../lib/api';

type BackupStatus = {
  running: boolean;
  lastStatus: { ok: boolean; message: string; timestamp: string };
  file: { exists: boolean; fileName?: string; size?: number; updatedAt?: string };
};

export default function AdminPage() {
  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [needsLogin, setNeedsLogin] = useState(false);

  async function loadStatus() {
    try {
      const result = await api<BackupStatus>('/admin/backup/status');
      setStatus(result);
      setNeedsLogin(false);
    } catch (err) {
      const text = (err as Error).message;
      if (text.includes('Unauthorized') || text.includes('401')) {
        setNeedsLogin(true);
        setStatus(null);
        return;
      }
      setMessage(text);
    }
  }

  useEffect(() => {
    loadStatus().catch(() => undefined);
  }, []);

  async function onRunBackup() {
    setLoading(true);
    setMessage('');
    try {
      await api('/admin/backup/export', { method: 'POST' });
      await loadStatus();
      setMessage('백업이 완료되었습니다. 기존 백업은 제거되고 최신 파일만 유지됩니다.');
    } catch (err) {
      const text = (err as Error).message;
      if (text.includes('Unauthorized') || text.includes('401')) {
        setNeedsLogin(true);
      } else {
        setMessage(text);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-center" style={{ minHeight: 'auto' }}>
      <section className="panel grid" style={{ width: 'min(840px, 100%)' }}>
        <div>
          <h1 className="section-title" style={{ fontSize: '36px' }}>
            기록 보관 관리
          </h1>
          <p className="section-subtitle">기록이 안전하게 남아 있도록 최신 백업을 1개 유지합니다.</p>
        </div>

        {needsLogin ? (
          <p className="muted">
            이 페이지는 관리자 로그인 후 사용할 수 있습니다. <Link href="/login">로그인하고 이어가기</Link>
          </p>
        ) : (
          <>
            <button type="button" onClick={onRunBackup} disabled={loading} style={{ maxWidth: 220 }}>
              지금 백업 만들기
            </button>
            {status ? (
              <div className="panel table-like">
                <div className="table-row">
                  <strong>최근 상태</strong>
                  <span className="muted">{status.lastStatus.message}</span>
                </div>
                <div className="table-row">
                  <strong>실행 시간</strong>
                  <span className="muted">{new Date(status.lastStatus.timestamp).toLocaleString('ko-KR')}</span>
                </div>
                <div className="table-row">
                  <strong>백업 파일</strong>
                  <span className="muted">{status.file.exists ? status.file.fileName : '없음'}</span>
                </div>
                <div className="table-row">
                  <strong>파일 크기</strong>
                  <span className="muted">{status.file.exists ? `${status.file.size} bytes` : '-'}</span>
                </div>
              </div>
            ) : null}
          </>
        )}

        {message ? <p className="muted">{message}</p> : null}
      </section>
    </div>
  );
}
