'use client';

import { useState } from 'react';
import { api } from '../../../lib/api';
import { useAuth } from '../../../lib/use-auth';

type EntryMemoProps = {
  entryId: string;
  initialMemo: string;
};

export default function EntryMemo({ entryId, initialMemo }: EntryMemoProps) {
  const { isAuthenticated } = useAuth();
  const [memo, setMemo] = useState(initialMemo);
  const [draft, setDraft] = useState(initialMemo);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  async function saveMemo(nextMemo: string) {
    setLoading(true);
    setFeedback('');
    setError('');

    try {
      const updated = await api<{ memo?: string }>(`/entries/${entryId}`, {
        method: 'PATCH',
        body: JSON.stringify({ memo: nextMemo }),
      });
      const resolved = updated.memo ?? nextMemo;
      setMemo(resolved);
      setDraft(resolved);
      setEditing(false);
      setFeedback(resolved ? '메모를 저장했습니다.' : '메모를 삭제했습니다.');
    } catch (err) {
      setError((err as Error).message || '메모 저장에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteMemo() {
    if (!window.confirm('메모를 삭제할까요?')) {
      return;
    }
    await saveMemo('');
  }

  return (
    <section className="v2-detail-memo">
      {editing ? (
        <textarea
          className="v2-detail-memo-editor"
          rows={4}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="이 기록에 대한 메모를 남겨보세요."
        />
      ) : memo ? (
        <p>{memo}</p>
      ) : (
        <p className="v2-detail-memo-empty">아직 메모가 없습니다.</p>
      )}

      {isAuthenticated ? (
        <div className="v2-detail-memo-actions bottom">
          {editing ? (
            <>
              <button
                type="button"
                className="v2-detail-mini-btn secondary"
                onClick={() => {
                  setEditing(false);
                  setDraft(memo);
                }}
              >
                취소
              </button>
              <button
                type="button"
                className="v2-detail-mini-btn"
                disabled={loading}
                onClick={() => saveMemo(draft)}
              >
                {loading ? '저장 중...' : '저장'}
              </button>
            </>
          ) : (
            <>
              <button type="button" className="v2-detail-mini-btn secondary" onClick={() => setEditing(true)}>
                {memo ? '수정' : '작성'}
              </button>
              {memo ? (
                <button
                  type="button"
                  className="v2-detail-mini-btn danger"
                  disabled={loading}
                  onClick={() => onDeleteMemo().catch(() => undefined)}
                >
                  삭제
                </button>
              ) : null}
            </>
          )}
        </div>
      ) : null}

      {feedback ? <p className="v2-comment-feedback">{feedback}</p> : null}
      {error ? <p className="v2-comment-error">{error}</p> : null}
    </section>
  );
}
