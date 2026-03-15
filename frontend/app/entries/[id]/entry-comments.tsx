'use client';

import { FormEvent, useMemo, useState } from 'react';
import { api } from '../../../lib/api';
import { useAuth } from '../../../lib/use-auth';
import { formatDateTime } from '../../../lib/date';
import type { EntryComment } from '../../../types/entry';

type EntryCommentsProps = {
  entryId: string;
  initialComments: EntryComment[];
};

export default function EntryComments({ entryId, initialComments }: EntryCommentsProps) {
  const { isAuthenticated, username } = useAuth();
  const [comments, setComments] = useState<EntryComment[]>(initialComments);
  const [draft, setDraft] = useState('');
  const [editingCommentId, setEditingCommentId] = useState('');
  const [editingDraft, setEditingDraft] = useState('');
  const [feedback, setFeedback] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const orderedComments = useMemo(
    () => [...comments].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()),
    [comments],
  );

  async function onCreateComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) {
      return;
    }

    setLoading(true);
    setFeedback('');
    setErrorMessage('');
    try {
      const updated = await api<{ comments: EntryComment[] }>(`/entries/${entryId}/comments`, {
        method: 'POST',
        body: JSON.stringify({ content: draft }),
      });
      setComments(updated.comments);
      setDraft('');
      setFeedback('메모를 남겼습니다.');
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function onStartEdit(comment: EntryComment) {
    setEditingCommentId(comment.id);
    setEditingDraft(comment.content);
    setFeedback('');
    setErrorMessage('');
  }

  async function onUpdateComment(commentId: string) {
    if (!editingDraft.trim()) {
      return;
    }

    setLoading(true);
    setFeedback('');
    setErrorMessage('');
    try {
      const updated = await api<{ comments: EntryComment[] }>(`/entries/${entryId}/comments/${commentId}`, {
        method: 'PATCH',
        body: JSON.stringify({ content: editingDraft }),
      });
      setComments(updated.comments);
      setEditingCommentId('');
      setEditingDraft('');
      setFeedback('메모를 수정했습니다.');
    } catch (error) {
      setErrorMessage((error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="detail-block">
      <h3 className="detail-block-title">메모</h3>

      <div className="entry-comments-list">
        {orderedComments.length === 0 ? <p className="muted">아직 메모가 없습니다.</p> : null}

        {orderedComments.map((comment) => {
          const isMine = comment.author === username;
          const isEditing = editingCommentId === comment.id;
          return (
            <article key={comment.id} className="entry-comment-item">
              <div className="entry-comment-meta">
                <span>{comment.author}</span>
                <span>{formatDateTime(comment.createdAt)}</span>
              </div>

              {isEditing ? (
                <>
                  <textarea
                    className="entry-comment-editor"
                    value={editingDraft}
                    onChange={(event) => setEditingDraft(event.target.value)}
                    rows={3}
                  />
                  <div className="entry-comment-actions">
                    <button type="button" className="secondary" onClick={() => onUpdateComment(comment.id)} disabled={loading}>
                      저장
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => {
                        setEditingCommentId('');
                        setEditingDraft('');
                      }}
                      disabled={loading}
                    >
                      취소
                    </button>
                  </div>
                </>
              ) : (
                <p className="entry-comment-content">{comment.content}</p>
              )}

              {!isEditing && isMine ? (
                <div className="entry-comment-actions">
                  <button type="button" className="secondary" onClick={() => onStartEdit(comment)}>
                    수정
                  </button>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      {isAuthenticated ? (
        <form className="entry-comment-form" onSubmit={onCreateComment}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={3}
            placeholder="메모 남기기"
            required
          />
          <div className="entry-comment-actions">
            <button type="submit" disabled={loading}>
              추가
            </button>
          </div>
        </form>
      ) : (
        <p className="muted" style={{ marginTop: 8 }}>
          메모 추가는 로그인 후 가능합니다.
        </p>
      )}

      {feedback ? <p className="muted">{feedback}</p> : null}
      {errorMessage ? <p className="muted">{errorMessage}</p> : null}
    </div>
  );
}
