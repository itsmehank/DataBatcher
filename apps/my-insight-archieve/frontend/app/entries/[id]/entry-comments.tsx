'use client';

import { FormEvent, useMemo, useState } from 'react';
import { formatDateTime } from '../../../lib/date';
import { api } from '../../../lib/api';
import { useAuth } from '../../../lib/use-auth';
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
      setFeedback('댓글을 남겼습니다.');
    } catch (error) {
      setErrorMessage((error as Error).message || '댓글 작성에 실패했습니다.');
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

  function onCancelEdit() {
    setEditingCommentId('');
    setEditingDraft('');
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
      onCancelEdit();
      setFeedback('댓글을 수정했습니다.');
    } catch (error) {
      setErrorMessage((error as Error).message || '댓글 수정에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteComment(commentId: string) {
    if (!window.confirm('댓글을 삭제할까요?')) {
      return;
    }

    setLoading(true);
    setFeedback('');
    setErrorMessage('');

    try {
      const updated = await api<{ comments: EntryComment[] }>(`/entries/${entryId}/comments/${commentId}`, {
        method: 'DELETE',
      });
      setComments(updated.comments);
      onCancelEdit();
      setFeedback('댓글을 삭제했습니다.');
    } catch (error) {
      setErrorMessage((error as Error).message || '댓글 삭제에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="v2-comment-section">
      <h2 className="v2-comment-title">댓글</h2>

      <div className="v2-comment-list">
        {orderedComments.length === 0 ? <p className="v2-comment-empty">아직 댓글이 없습니다.</p> : null}

        {orderedComments.map((comment) => {
          const isMine = comment.author === username;
          const isEditing = editingCommentId === comment.id;

          return (
            <article key={comment.id} className="v2-comment-item">
              <div className="v2-comment-meta">
                <span>{comment.author}</span>
                <span>{formatDateTime(comment.createdAt)}</span>
              </div>

              {isEditing ? (
                <>
                  <textarea
                    className="v2-comment-editor"
                    value={editingDraft}
                    onChange={(event) => setEditingDraft(event.target.value)}
                    rows={4}
                  />

                  <div className="v2-comment-actions">
                    <button type="button" className="v2-comment-mini-btn" onClick={() => onUpdateComment(comment.id)} disabled={loading}>
                      저장
                    </button>
                    <button type="button" className="v2-comment-mini-btn secondary" onClick={onCancelEdit} disabled={loading}>
                      취소
                    </button>
                  </div>
                </>
              ) : (
                <p className="v2-comment-content">{comment.content}</p>
              )}

              {!isEditing && isMine ? (
                <div className="v2-comment-actions">
                  <button type="button" className="v2-comment-mini-btn secondary" onClick={() => onStartEdit(comment)}>
                    수정
                  </button>
                  <button type="button" className="v2-comment-mini-btn danger" onClick={() => onDeleteComment(comment.id).catch(() => undefined)}>
                    삭제
                  </button>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      {isAuthenticated ? (
        <form className="v2-comment-form" onSubmit={onCreateComment}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={4}
            placeholder="기록에 대한 생각을 남겨보세요."
            required
          />

          <div className="v2-comment-submit-row">
            <button type="submit" className="v2-comment-submit-btn" disabled={loading}>
              {loading ? '저장 중...' : '댓글 남기기'}
            </button>
          </div>
        </form>
      ) : (
        <p className="v2-comment-empty">댓글 작성은 로그인 후 가능합니다.</p>
      )}

      {feedback ? <p className="v2-comment-feedback">{feedback}</p> : null}
      {errorMessage ? <p className="v2-comment-error">{errorMessage}</p> : null}
    </section>
  );
}
