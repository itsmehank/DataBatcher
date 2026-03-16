'use client';

import { useMemo, useState } from 'react';
import type { Template } from '../../../types/template';

export function useTemplatesFilters(templates: Template[]) {
  const [query, setQuery] = useState('');
  const [useCaseFilter, setUseCaseFilter] = useState('all');

  const useCaseOptions = useMemo(() => {
    const unique = new Set(templates.map((template) => template.useCase).filter(Boolean));
    return ['all', ...Array.from(unique)];
  }, [templates]);

  const filteredTemplates = useMemo(() => {
    return templates.filter((template) => {
      const text = `${template.name} ${template.description} ${template.useCase} ${template.content} ${template.tags.join(' ')}`.toLowerCase();
      const queryMatch = text.includes(query.trim().toLowerCase());
      const useCaseMatch = useCaseFilter === 'all' || template.useCase === useCaseFilter;
      return queryMatch && useCaseMatch;
    });
  }, [templates, query, useCaseFilter]);

  function resetFilters() {
    setQuery('');
    setUseCaseFilter('all');
  }

  return {
    query,
    setQuery,
    useCaseFilter,
    setUseCaseFilter,
    useCaseOptions,
    filteredTemplates,
    resetFilters,
  };
}
