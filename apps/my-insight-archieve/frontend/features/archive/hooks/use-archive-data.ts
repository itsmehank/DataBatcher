'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { api } from '../../../lib/api';
import { isUnauthorizedError } from '../../../lib/errors';
import type { Category } from '../../../types/category';
import type { Entry } from '../../../types/entry';

type EntryForm = {
  title: string;
  content: string;
  memo: string;
  conversationUrl: string;
  source: string;
  categoryId: string;
  tags: string;
};

type UseArchiveDataResult = {
  categories: Category[];
  entries: Entry[];
  pageState: 'loading' | 'ready' | 'error';
  loading: boolean;
  needsLoginHint: boolean;
  isDrawerOpen: boolean;
  feedback: string;
  errorMessage: string;
  form: EntryForm;
  setForm: Dispatch<SetStateAction<EntryForm>>;
  categoryNameMap: Record<string, string>;
  initializePage: () => Promise<void>;
  loadData: () => Promise<void>;
  onRequestCreate: () => void;
  onCreateEntry: (e: FormEvent<HTMLFormElement>) => Promise<void>;
  onCancelCreate: () => void;
  setIsDrawerOpen: Dispatch<SetStateAction<boolean>>;
  setErrorMessage: Dispatch<SetStateAction<string>>;
  setFeedback: Dispatch<SetStateAction<string>>;
  setNeedsLoginHint: Dispatch<SetStateAction<boolean>>;
};

export function useArchiveData(isAuthenticated: boolean): UseArchiveDataResult {
  const [categories, setCategories] = useState<Category[]>([]);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [feedback, setFeedback] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [pageState, setPageState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [needsLoginHint, setNeedsLoginHint] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const [form, setForm] = useState<EntryForm>({
    title: '',
    content: '',
    memo: '',
    conversationUrl: '',
    source: 'chatgpt',
    categoryId: '',
    tags: '',
  });

  const categoryNameMap = useMemo(
    () =>
      categories.reduce<Record<string, string>>((acc, category) => {
        acc[category._id] = category.name;
        return acc;
      }, {}),
    [categories],
  );

  const loadData = useCallback(async () => {
    const [categoriesRes, entriesRes] = await Promise.all([api<Category[]>('/categories'), api<Entry[]>('/entries')]);
    setCategories(categoriesRes);
    setEntries(entriesRes);
    if (!form.categoryId && categoriesRes[0]) {
      setForm((prev) => ({ ...prev, categoryId: categoriesRes[0]._id }));
    }
  }, [form.categoryId]);

  const initializePage = useCallback(async () => {
    setPageState('loading');
    setErrorMessage('');

    try {
      await loadData();
      setPageState('ready');
    } catch (err) {
      setErrorMessage((err as Error).message);
      setPageState('error');
    }
  }, [loadData]);

  useEffect(() => {
    initializePage().catch(() => undefined);
  }, [initializePage]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setIsDrawerOpen(false);
      }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  function onRequestCreate() {
    if (!isAuthenticated) {
      setNeedsLoginHint(true);
      setFeedback('기록 남기기는 관리자 로그인 후 사용할 수 있습니다.');
      return;
    }
    setNeedsLoginHint(false);
    setIsDrawerOpen(true);
  }

  async function onCreateEntry(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setFeedback('');
    setErrorMessage('');

    try {
      await api('/entries', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          tags: form.tags
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      });
      setForm((prev) => ({ ...prev, title: '', content: '', memo: '', tags: '' }));
      await loadData();
      setIsDrawerOpen(false);
      setNeedsLoginHint(false);
      setFeedback('새 기록을 조용히 남겨두었습니다.');
    } catch (err) {
      const typedError = err as Error;
      if (isUnauthorizedError(typedError)) {
        setNeedsLoginHint(true);
        setIsDrawerOpen(false);
        setFeedback('로그인이 만료되었습니다. 다시 로그인 후 기록을 저장해 주세요.');
      } else {
        setErrorMessage(typedError.message);
      }
    } finally {
      setLoading(false);
    }
  }

  function onCancelCreate() {
    setForm((prev) => ({
      ...prev,
      title: '',
      content: '',
      memo: '',
      conversationUrl: '',
      source: 'chatgpt',
      tags: '',
    }));
    setIsDrawerOpen(false);
  }

  return {
    categories,
    entries,
    pageState,
    loading,
    needsLoginHint,
    isDrawerOpen,
    feedback,
    errorMessage,
    form,
    setForm,
    categoryNameMap,
    initializePage,
    loadData,
    onRequestCreate,
    onCreateEntry,
    onCancelCreate,
    setIsDrawerOpen,
    setErrorMessage,
    setFeedback,
    setNeedsLoginHint,
  };
}
