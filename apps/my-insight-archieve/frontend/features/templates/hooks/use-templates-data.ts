'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { api } from '../../../lib/api';
import { isUnauthorizedError } from '../../../lib/errors';
import type { Template } from '../../../types/template';

type TemplateForm = {
  name: string;
  content: string;
  description: string;
  useCase: string;
  tags: string;
};

type UseTemplatesDataResult = {
  templates: Template[];
  feedback: string;
  errorMessage: string;
  pageState: 'loading' | 'ready' | 'error';
  needsLoginHint: boolean;
  loading: boolean;
  isDrawerOpen: boolean;
  form: TemplateForm;
  setForm: Dispatch<SetStateAction<TemplateForm>>;
  initializePage: () => Promise<void>;
  loadTemplates: () => Promise<void>;
  onRequestCreate: () => void;
  onCreateTemplate: (e: FormEvent<HTMLFormElement>) => Promise<void>;
  onCopy: (content: string) => Promise<void>;
  onCancelCreate: () => void;
  setIsDrawerOpen: Dispatch<SetStateAction<boolean>>;
};

export function useTemplatesData(isAuthenticated: boolean): UseTemplatesDataResult {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [feedback, setFeedback] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [pageState, setPageState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [needsLoginHint, setNeedsLoginHint] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [form, setForm] = useState<TemplateForm>({
    name: '',
    content: '',
    description: '',
    useCase: '',
    tags: '',
  });

  const loadTemplates = useCallback(async () => {
    const data = await api<Template[]>('/templates');
    setTemplates(data);
  }, []);

  const initializePage = useCallback(async () => {
    setPageState('loading');
    setErrorMessage('');

    try {
      await loadTemplates();
      setPageState('ready');
    } catch (err) {
      setErrorMessage((err as Error).message);
      setPageState('error');
    }
  }, [loadTemplates]);

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
      setFeedback('새 문장 템플릿은 로그인 후 남길 수 있습니다.');
      return;
    }
    setNeedsLoginHint(false);
    setIsDrawerOpen(true);
  }

  async function onCreateTemplate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setFeedback('');
    setErrorMessage('');
    try {
      await api('/templates', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          tags: form.tags
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      });
      setForm({ name: '', content: '', description: '', useCase: '', tags: '' });
      await loadTemplates();
      setIsDrawerOpen(false);
      setNeedsLoginHint(false);
      setFeedback('새로운 시작 문장을 보관했습니다.');
    } catch (err) {
      const typedError = err as Error;
      if (isUnauthorizedError(typedError)) {
        setNeedsLoginHint(true);
        setIsDrawerOpen(false);
        setFeedback('로그인이 만료되었습니다. 다시 로그인 후 문장을 저장해 주세요.');
      } else {
        setErrorMessage(typedError.message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function onCopy(content: string) {
    await navigator.clipboard.writeText(content);
    setFeedback('문장을 복사해 바로 이어서 쓸 수 있어요.');
  }

  function onCancelCreate() {
    setForm({ name: '', content: '', description: '', useCase: '', tags: '' });
    setIsDrawerOpen(false);
  }

  return {
    templates,
    feedback,
    errorMessage,
    pageState,
    needsLoginHint,
    loading,
    isDrawerOpen,
    form,
    setForm,
    initializePage,
    loadTemplates,
    onRequestCreate,
    onCreateTemplate,
    onCopy,
    onCancelCreate,
    setIsDrawerOpen,
  };
}
