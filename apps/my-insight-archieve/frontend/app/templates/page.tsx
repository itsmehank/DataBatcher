'use client';

import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { api } from '../../lib/api';
import { formatDateShort } from '../../lib/date';
import { isUnauthorizedError } from '../../lib/errors';
import { useAuth } from '../../lib/use-auth';
import type { Template } from '../../types/template';

type TemplateFormState = {
  name: string;
  content: string;
  description: string;
  useCase: string;
  tags: string;
};

type TemplateRecord = Template & { createdAt?: string };

const INITIAL_TEMPLATE_FORM: TemplateFormState = {
  name: '',
  content: '',
  description: '',
  useCase: 'template',
  tags: '',
};

const USE_CASE_OPTIONS = ['prompt', 'template', 'snippet', 'other'] as const;

function SearchIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="23 4 23 10 17 10" />
      <polyline points="1 20 1 14 7 14" />
      <path d="M3.51 9a9 9 0 0 1 14.13-3.36L23 10M1 14l5.36 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

function TemplateRow({
  template,
  onCopy,
  onDelete,
}: {
  template: TemplateRecord;
  onCopy: (content: string) => Promise<void>;
  onDelete: (template: TemplateRecord) => Promise<void>;
}) {
  return (
    <article className="v2-template-row">
      <button
        type="button"
        className="v2-entry-delete"
        aria-label="템플릿 삭제"
        onClick={() => onDelete(template)}
      >
        ×
      </button>

      <div className="v2-entry-title-row">
        <div className="v2-entry-title">{template.name}</div>
        <span className="v2-entry-category">{template.useCase || 'other'}</span>
      </div>

      <div className="v2-template-description">{template.description || '설명이 없는 템플릿입니다.'}</div>
      <div className="v2-template-content">{template.content}</div>

      <div className="v2-entry-meta">
        <div className="v2-entry-tags">
          {template.tags.map((tag) => (
            <span key={`${template._id}-${tag}`} className="v2-entry-tag">
              #{tag}
            </span>
          ))}
        </div>
        <span className="v2-entry-date">{template.createdAt ? formatDateShort(template.createdAt) : ''}</span>
        <button type="button" className="v2-template-copy-btn" onClick={() => onCopy(template.content)}>
          복사
        </button>
      </div>
    </article>
  );
}

export default function TemplatesPage() {
  const { isAuthenticated, isLoading: isAuthLoading, refreshAuth } = useAuth();
  const [templates, setTemplates] = useState<TemplateRecord[]>([]);
  const [search, setSearch] = useState('');
  const [useCaseFilter, setUseCaseFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [authHint, setAuthHint] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerSubmitting, setDrawerSubmitting] = useState(false);
  const [drawerError, setDrawerError] = useState('');
  const [createForm, setCreateForm] = useState<TemplateFormState>(INITIAL_TEMPLATE_FORM);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const data = await api<TemplateRecord[]>('/templates');
      const sorted = [...data].sort((a, b) => {
        const left = a.createdAt ? new Date(a.createdAt).getTime() : 0;
        const right = b.createdAt ? new Date(b.createdAt).getTime() : 0;
        return right - left;
      });
      setTemplates(sorted);
    } catch (err) {
      setError((err as Error).message || '템플릿을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates().catch(() => undefined);
  }, [loadTemplates]);

  useEffect(() => {
    if (!drawerOpen) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDrawerOpen(false);
        setDrawerError('');
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [drawerOpen]);

  const filteredTemplates = useMemo(() => {
    let result = templates;

    if (useCaseFilter) {
      result = result.filter((t) => t.useCase === useCaseFilter);
    }

    if (search.trim()) {
      const query = search.trim().toLowerCase();
      result = result.filter((template) => {
        return (
          template.name.toLowerCase().includes(query) ||
          template.content.toLowerCase().includes(query) ||
          (template.description || '').toLowerCase().includes(query) ||
          (template.useCase || '').toLowerCase().includes(query) ||
          template.tags.some((tag) => tag.toLowerCase().includes(query))
        );
      });
    }

    return result;
  }, [search, useCaseFilter, templates]);

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    setDrawerError('');
    setCreateForm(INITIAL_TEMPLATE_FORM);
  }, []);

  const openDrawer = useCallback(() => {
    if (isAuthLoading) {
      setAuthHint('로그인 상태를 확인 중입니다. 잠시 후 다시 시도해 주세요.');
      return;
    }

    if (!isAuthenticated) {
      setAuthHint('로그인 후 템플릿을 만들 수 있어요.');
      return;
    }

    setAuthHint('');
    setDrawerError('');
    setDrawerOpen(true);
  }, [isAuthenticated, isAuthLoading]);

  const handleCopy = useCallback(async (content: string) => {
    await navigator.clipboard.writeText(content);
    setFeedback('템플릿 내용을 복사했습니다.');
  }, []);

  const handleCreate = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      if (!isAuthenticated) {
        setAuthHint('로그인 후 템플릿을 만들 수 있어요.');
        return;
      }

      setDrawerSubmitting(true);
      setDrawerError('');

      try {
        await api<TemplateRecord>('/templates', {
          method: 'POST',
          body: JSON.stringify({
            name: createForm.name,
            content: createForm.content,
            description: createForm.description,
            useCase: createForm.useCase,
            tags: createForm.tags
              .split(',')
              .map((tag) => tag.trim())
              .filter(Boolean),
          }),
        });

        await loadTemplates();
        setFeedback('새 템플릿을 보관했습니다.');
        closeDrawer();
      } catch (err) {
        const typedErr = err as Error;
        if (isUnauthorizedError(typedErr)) {
          setAuthHint('로그인이 만료되었습니다. 다시 로그인해 주세요.');
          setDrawerOpen(false);
          refreshAuth().catch(() => undefined);
          return;
        }
        setDrawerError(typedErr.message || '템플릿 저장에 실패했습니다.');
      } finally {
        setDrawerSubmitting(false);
      }
    },
    [closeDrawer, createForm, isAuthenticated, loadTemplates, refreshAuth],
  );

  const handleDelete = useCallback(
    async (template: TemplateRecord) => {
      if (!isAuthenticated) {
        setAuthHint('로그인 후 삭제할 수 있어요.');
        return;
      }

      if (!window.confirm(`'${template.name}' 템플릿을 삭제할까요?`)) {
        return;
      }

      setFeedback('');
      setError('');

      try {
        await api<{ success: boolean }>(`/templates/${template._id}`, { method: 'DELETE' });
        await loadTemplates();
        setFeedback('템플릿을 삭제했습니다.');
      } catch (err) {
        const typedErr = err as Error;
        if (isUnauthorizedError(typedErr)) {
          setAuthHint('로그인 후 삭제할 수 있어요.');
          refreshAuth().catch(() => undefined);
          return;
        }
        setError(typedErr.message || '템플릿 삭제에 실패했습니다.');
      }
    },
    [isAuthenticated, loadTemplates, refreshAuth],
  );

  return (
    <>
      <header className="v2-header">
        <div className="v2-header-top">
          <h1 className="v2-page-title">템플릿</h1>
          <span className="v2-page-count">{filteredTemplates.length}건</span>
        </div>

        <div className="v2-toolbar">
          <div className="v2-search-wrap">
            <span className="v2-search-icon">
              <SearchIcon />
            </span>
            <input
              type="text"
              className="v2-search-input"
              placeholder="제목, 내용, 태그 검색..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select
            className="v2-toolbar-select"
            value={useCaseFilter}
            onChange={(e) => setUseCaseFilter(e.target.value)}
          >
            <option value="">용도</option>
            {USE_CASE_OPTIONS.map((uc) => (
              <option key={uc} value={uc}>{uc}</option>
            ))}
          </select>

          {useCaseFilter ? (
            <button type="button" className="v2-filter-reset" onClick={() => setUseCaseFilter('')}>
              초기화
            </button>
          ) : null}
        </div>

        {authHint ? <div className="v2-error">{authHint}</div> : null}
        {feedback ? <div className="v2-admin-message">{feedback}</div> : null}
      </header>

      <div className="v2-entries">
        <div className="v2-section-label">저장된 템플릿</div>

        {loading ? <div className="v2-loading">템플릿을 불러오는 중입니다...</div> : null}
        {!loading && error ? (
          <div className="v2-error">
            불러오기에 실패했습니다. {error}
            <button type="button" className="v2-filter-reset" onClick={() => loadTemplates()} style={{ marginLeft: 8 }}>
              다시 읽기
            </button>
          </div>
        ) : null}
        {!loading && !error && filteredTemplates.length === 0 ? <div className="v2-empty">검색 결과가 없습니다.</div> : null}

        {!loading && !error
          ? filteredTemplates.map((template) => (
              <TemplateRow key={template._id} template={template} onCopy={handleCopy} onDelete={handleDelete} />
            ))
          : null}
      </div>

      <button type="button" className="v2-fab" onClick={openDrawer} aria-label="새 템플릿">
        +
      </button>

      <div
        className={`v2-drawer-overlay${drawerOpen ? ' open' : ''}`}
        onClick={closeDrawer}
        aria-hidden={drawerOpen ? 'false' : 'true'}
      />
      <aside className={`v2-drawer${drawerOpen ? ' open' : ''}`} aria-hidden={drawerOpen ? 'false' : 'true'}>
        <div className="v2-drawer-header">
          <h2>새 템플릿 만들기</h2>
        </div>

        <form className="v2-drawer-body" onSubmit={handleCreate}>
          <label className="v2-drawer-field">
            <span className="v2-drawer-label">이름</span>
            <input
              className="v2-drawer-input"
              value={createForm.name}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, name: e.target.value }))}
              required
            />
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">내용</span>
            <textarea
              className="v2-drawer-textarea"
              rows={5}
              value={createForm.content}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, content: e.target.value }))}
              required
            />
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">설명</span>
            <textarea
              className="v2-drawer-textarea"
              rows={2}
              value={createForm.description}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, description: e.target.value }))}
            />
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">활용 목적</span>
            <select
              className="v2-drawer-select"
              value={createForm.useCase}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, useCase: e.target.value }))}
            >
              {USE_CASE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">태그 (쉼표로 구분)</span>
            <input
              className="v2-drawer-input"
              value={createForm.tags}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, tags: e.target.value }))}
              placeholder="예: 글쓰기, 요약, 회의"
            />
          </label>

          {drawerError ? <div className="v2-error">{drawerError}</div> : null}

          <div className="v2-drawer-actions">
            <button type="button" className="v2-drawer-cancel-btn" onClick={closeDrawer}>
              취소
            </button>
            <button type="submit" className="v2-submit-btn" disabled={drawerSubmitting}>
              {drawerSubmitting ? '저장 중...' : '저장'}
            </button>
          </div>
        </form>
      </aside>
    </>
  );
}
