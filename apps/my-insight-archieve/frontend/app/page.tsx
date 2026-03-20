'use client';

import Link from 'next/link';
import { useState, useMemo, useEffect, useCallback, type FormEvent } from 'react';
import { api } from '../lib/api';
import { formatDateShort } from '../lib/date';
import { isUnauthorizedError } from '../lib/errors';
import { useAuth } from '../lib/use-auth';
import type { Entry } from '../types/entry';
import type { Category } from '../types/category';

type DateGroup = {
  label: string;
  items: Entry[];
};

type CreateFormState = {
  title: string;
  content: string;
  memo: string;
  conversationUrl: string;
  source: string;
  categoryId: string;
  tags: string;
};

const INITIAL_CREATE_FORM: CreateFormState = {
  title: '',
  content: '',
  memo: '',
  conversationUrl: '',
  source: 'chatgpt',
  categoryId: '',
  tags: '',
};

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

function FilterIcon() {
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
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="8" y1="12" x2="16" y2="12" />
      <line x1="11" y1="18" x2="13" y2="18" />
    </svg>
  );
}

function getWeekStart(base: Date): Date {
  const day = base.getDay();
  const diffToMonday = day === 0 ? -6 : 1 - day;
  const start = new Date(base);
  start.setHours(0, 0, 0, 0);
  start.setDate(base.getDate() + diffToMonday);
  return start;
}

function getDateGroup(iso?: string): string {
  if (!iso) {
    return '이전 글들';
  }

  const now = new Date();
  const entryDate = new Date(iso);
  if (Number.isNaN(entryDate.getTime())) {
    return '이전 글들';
  }

  const weekStart = getWeekStart(now);
  return entryDate >= weekStart ? '이번 주' : '이전 글들';
}

function groupEntries(entries: Entry[]): DateGroup[] {
  const grouped = entries.reduce<Record<string, Entry[]>>((acc, entry) => {
    const label = getDateGroup(entry.createdAt);
    if (!acc[label]) {
      acc[label] = [];
    }
    acc[label].push(entry);
    return acc;
  }, {});

  return ['이번 주', '이전 글들']
    .filter((label) => grouped[label] && grouped[label].length > 0)
    .map((label) => ({ label, items: grouped[label] }));
}

function EntryRow({
  entry,
  categoryName,
  categoryColor,
  onDelete,
}: {
  entry: Entry;
  categoryName: string;
  categoryColor: string;
  onDelete: (entry: Entry) => void;
}) {
  return (
    <article className="v2-entry" style={{ borderLeftColor: categoryColor }}>
      <button
        type="button"
        className="v2-entry-delete"
        aria-label="기록 삭제"
        onClick={() => onDelete(entry)}
      >
        ×
      </button>

      <div className="v2-entry-title-row">
        <Link href={`/entries/${entry._id}`} className="v2-entry-link">
          <div className="v2-entry-title">{entry.title}</div>
        </Link>
        <span className="v2-entry-category">{categoryName}</span>
      </div>

      <div className="v2-entry-content">{entry.content}</div>

      <div className="v2-entry-meta">
        <div className="v2-entry-tags">
          {entry.tags.map((tag) => (
            <span key={`${entry._id}-${tag}`} className="v2-entry-tag">
              #{tag}
            </span>
          ))}
        </div>
        {entry.conversationUrl ? (
          <a href={entry.conversationUrl} target="_blank" rel="noreferrer" className="v2-entry-original">
            원문
          </a>
        ) : null}
        <span className="v2-entry-date">{formatDateShort(entry.createdAt)}</span>
        <span className="v2-entry-source">{entry.source || 'other'}</span>
      </div>
    </article>
  );
}

export default function HomePage() {
  const { isAuthenticated, isLoading: isAuthLoading, refreshAuth } = useAuth();
  const [entries, setEntries] = useState<Entry[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'title'>('newest');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');
  const [authHint, setAuthHint] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerError, setDrawerError] = useState('');
  const [drawerSubmitting, setDrawerSubmitting] = useState(false);
  const [createForm, setCreateForm] = useState<CreateFormState>(INITIAL_CREATE_FORM);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const [entriesRes, categoriesRes] = await Promise.all([
        api<Entry[]>('/entries'),
        api<Category[]>('/categories'),
      ]);

      const sortedEntries = [...entriesRes].sort((a, b) => {
        const left = a.createdAt ? new Date(a.createdAt).getTime() : 0;
        const right = b.createdAt ? new Date(b.createdAt).getTime() : 0;
        return right - left;
      });

      setEntries(sortedEntries);
      setCategories(categoriesRes);
    } catch (err) {
      setError((err as Error).message || '데이터를 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData().catch(() => undefined);
  }, [loadData]);

  useEffect(() => {
    const syncCategoryFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      const categoryFromUrl = params.get('category') || '';
      setCategoryFilter((prev) => (prev === categoryFromUrl ? prev : categoryFromUrl));
    };

    const onCategoryChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ categoryId?: string }>).detail;
      setCategoryFilter(detail?.categoryId || '');
    };

    syncCategoryFromUrl();
    window.addEventListener('popstate', syncCategoryFromUrl);
    window.addEventListener('insight:set-category-filter', onCategoryChanged as EventListener);
    return () => {
      window.removeEventListener('popstate', syncCategoryFromUrl);
      window.removeEventListener('insight:set-category-filter', onCategoryChanged as EventListener);
    };
  }, []);

  useEffect(() => {
    if (!drawerOpen) {
      return;
    }

    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDrawerOpen(false);
        setDrawerError('');
        setCreateForm(INITIAL_CREATE_FORM);
      }
    };

    window.addEventListener('keydown', handleEsc);
    return () => {
      window.removeEventListener('keydown', handleEsc);
    };
  }, [drawerOpen]);

  const categoryNameMap = useMemo(() => {
    return categories.reduce<Record<string, string>>((acc, category) => {
      acc[category._id] = category.name;
      return acc;
    }, {});
  }, [categories]);

  const categoryColorMap = useMemo(() => {
    return categories.reduce<Record<string, string>>((acc, category) => {
      acc[category._id] = category.color;
      return acc;
    }, {});
  }, [categories]);

  const sourceOptions = useMemo(() => {
    const sources = new Set(entries.map((e) => e.source).filter(Boolean));
    return Array.from(sources).sort();
  }, [entries]);

  const filtered = useMemo(() => {
    let result = entries;

    if (categoryFilter) {
      result = result.filter((e) => e.categoryId === categoryFilter);
    }

    if (sourceFilter) {
      result = result.filter((e) => e.source === sourceFilter);
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter((entry) => {
        const catName = (entry.categoryId && categoryNameMap[entry.categoryId]) || '';
        return (
          entry.title.toLowerCase().includes(q) ||
          entry.content.toLowerCase().includes(q) ||
          entry.tags.some((tag) => tag.toLowerCase().includes(q)) ||
          catName.toLowerCase().includes(q)
        );
      });
    }

    if (sortBy === 'oldest') {
      result = [...result].sort((a, b) => new Date(a.createdAt ?? 0).getTime() - new Date(b.createdAt ?? 0).getTime());
    } else if (sortBy === 'title') {
      result = [...result].sort((a, b) => a.title.localeCompare(b.title, 'ko'));
    }

    return result;
  }, [entries, search, categoryFilter, sourceFilter, sortBy, categoryNameMap]);

  const hasActiveFilter = categoryFilter !== '' || sourceFilter !== '' || sortBy !== 'newest';

  const groups = useMemo(() => groupEntries(filtered), [filtered]);

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    setDrawerError('');
    setCreateForm(INITIAL_CREATE_FORM);
  }, []);

  const openDrawer = useCallback(() => {
    if (isAuthLoading) {
      setAuthHint('로그인 상태를 확인 중입니다. 잠시 후 다시 시도해 주세요.');
      return;
    }

    if (!isAuthenticated) {
      setAuthHint('로그인 후 새 기록을 작성할 수 있어요.');
      return;
    }

    setAuthHint('');
    setDrawerError('');
    setDrawerOpen(true);
  }, [isAuthLoading, isAuthenticated]);

  const handleCreateSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      if (!isAuthenticated) {
        setAuthHint('로그인 후 새 기록을 작성할 수 있어요.');
        return;
      }

      setDrawerSubmitting(true);
      setDrawerError('');

      try {
        await api<Entry>('/entries', {
          method: 'POST',
          body: JSON.stringify({
            title: createForm.title,
            content: createForm.content,
            memo: createForm.memo,
            conversationUrl: createForm.conversationUrl,
            source: createForm.source,
            categoryId: createForm.categoryId || undefined,
            tags: createForm.tags
              .split(',')
              .map((tag) => tag.trim())
              .filter(Boolean),
          }),
        });
        await loadData();
        closeDrawer();
        setFeedback('새 기록을 저장했습니다.');
        setTimeout(() => setFeedback(''), 3000);
      } catch (err) {
        const typedErr = err as Error;
        if (isUnauthorizedError(typedErr)) {
          setAuthHint('로그인 후 새 기록을 작성할 수 있어요.');
          setDrawerOpen(false);
          setCreateForm(INITIAL_CREATE_FORM);
          refreshAuth().catch(() => undefined);
          return;
        }
        setDrawerError(typedErr.message || '기록 생성에 실패했습니다.');
      } finally {
        setDrawerSubmitting(false);
      }
    },
    [closeDrawer, createForm, isAuthenticated, loadData, refreshAuth],
  );

  const handleDelete = useCallback(
    async (entry: Entry) => {
      if (!isAuthenticated) {
        setAuthHint('로그인 후 삭제할 수 있어요.');
        return;
      }

      if (!window.confirm('이 기록을 삭제할까요?')) {
        return;
      }

      try {
        await api<{ success: boolean }>(`/entries/${entry._id}`, { method: 'DELETE' });
        await loadData();
        setFeedback('기록을 삭제했습니다.');
        setTimeout(() => setFeedback(''), 3000);
      } catch (err) {
        const typedErr = err as Error;
        if (isUnauthorizedError(typedErr)) {
          setAuthHint('로그인 후 삭제할 수 있어요.');
          refreshAuth().catch(() => undefined);
          return;
        }
        setError(typedErr.message || '기록 삭제에 실패했습니다.');
      }
    },
    [isAuthenticated, loadData, refreshAuth],
  );

  const updateCategoryFilter = useCallback(
    (value: string) => {
      setCategoryFilter(value);
      const next = new URLSearchParams(window.location.search);
      if (value) {
        next.set('category', value);
      } else {
        next.delete('category');
      }
      const query = next.toString();
      window.history.replaceState({}, '', query ? `/?${query}` : '/');
      window.dispatchEvent(new CustomEvent('insight:set-category-filter', { detail: { categoryId: value } }));
    },
    [],
  );

  return (
    <>
      <header className="v2-header">
        <div className="v2-header-top">
          <h1 className="v2-page-title">기록</h1>
          <span className="v2-page-count">{filtered.length}건의 인사이트</span>
        </div>

        <div className="v2-toolbar">
          <div className="v2-search-wrap">
            <span className="v2-search-icon">
              <SearchIcon />
            </span>
            <input
              type="text"
              className="v2-search-input"
              placeholder="검색..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select
            className="v2-toolbar-select"
            value={categoryFilter}
            onChange={(e) => updateCategoryFilter(e.target.value)}
          >
            <option value="">카테고리</option>
            {categories.map((c) => (
              <option key={c._id} value={c._id}>{c.name}</option>
            ))}
          </select>

          <select
            className="v2-toolbar-select"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
          >
            <option value="">출처</option>
            {sourceOptions.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <select
            className="v2-toolbar-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'newest' | 'oldest' | 'title')}
          >
            <option value="newest">최신순</option>
            <option value="oldest">오래된순</option>
            <option value="title">제목순</option>
          </select>

          {hasActiveFilter ? (
            <button
              type="button"
              className="v2-filter-reset"
              onClick={() => {
                updateCategoryFilter('');
                setSourceFilter('');
                setSortBy('newest');
              }}
            >
              초기화
            </button>
          ) : null}
        </div>

        {feedback ? <div className="v2-feedback">{feedback}</div> : null}
        {authHint ? (
          <div className="v2-auth-hint">
            {authHint} <Link href="/login" className="v2-auth-hint-link">로그인하기</Link>
          </div>
        ) : null}
      </header>

      <div className="v2-entries">
        {loading ? <div className="v2-loading">기록을 불러오는 중입니다...</div> : null}

        {!loading && error ? <div className="v2-error">불러오기에 실패했습니다. {error}</div> : null}

        {!loading && !error && groups.length === 0 ? <div className="v2-empty">검색 결과가 없습니다.</div> : null}

        {!loading && !error
          ? groups.map((group) => (
              <section key={group.label}>
                <div className="v2-section-label">{group.label}</div>
                {group.items.map((entry) => (
                  <EntryRow
                    key={entry._id}
                    entry={entry}
                    categoryName={(entry.categoryId && categoryNameMap[entry.categoryId]) || '미분류'}
                    categoryColor={(entry.categoryId && categoryColorMap[entry.categoryId]) || 'transparent'}
                    onDelete={handleDelete}
                  />
                ))}
              </section>
            ))
          : null}
      </div>

      <button type="button" className="v2-fab" onClick={openDrawer} aria-label="새 기록">
        +
      </button>

      <div
        className={`v2-drawer-overlay${drawerOpen ? ' open' : ''}`}
        onClick={closeDrawer}
        aria-hidden={drawerOpen ? 'false' : 'true'}
      />
      <aside className={`v2-drawer${drawerOpen ? ' open' : ''}`} aria-hidden={drawerOpen ? 'false' : 'true'}>
        <div className="v2-drawer-header">
          <h2>새 기록 작성</h2>
        </div>

        <form className="v2-drawer-body" onSubmit={handleCreateSubmit}>
          <label className="v2-drawer-field">
            <span className="v2-drawer-label">제목</span>
            <input
              className="v2-drawer-input"
              value={createForm.title}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, title: e.target.value }))}
              required
            />
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">내용</span>
            <textarea
              className="v2-drawer-textarea"
              rows={4}
              value={createForm.content}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, content: e.target.value }))}
              required
            />
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">메모</span>
            <textarea
              className="v2-drawer-textarea"
              rows={2}
              value={createForm.memo}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, memo: e.target.value }))}
            />
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">대화 URL</span>
            <input
              className="v2-drawer-input"
              value={createForm.conversationUrl}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, conversationUrl: e.target.value }))}
            />
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">출처</span>
            <select
              className="v2-drawer-select"
              value={createForm.source}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, source: e.target.value }))}
            >
              <option value="chatgpt">chatgpt</option>
              <option value="claude">claude</option>
              <option value="gemini">gemini</option>
              <option value="other">other</option>
            </select>
          </label>

          <label className="v2-drawer-field">
            <span className="v2-drawer-label">카테고리</span>
            <select
              className="v2-drawer-select"
              value={createForm.categoryId}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, categoryId: e.target.value }))}
              required
            >
              <option value="">카테고리를 선택하세요</option>
              {categories.map((category) => (
                <option key={category._id} value={category._id}>
                  {category.name}
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
              placeholder="예: 요약, 프롬프트, 아이디어"
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
