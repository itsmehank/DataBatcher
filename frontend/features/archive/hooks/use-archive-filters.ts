'use client';

import { useMemo, useState } from 'react';
import type { Entry } from '../../../types/entry';

export type SortOption = 'newest' | 'oldest' | 'title';

export function useArchiveFilters(entries: Entry[]) {
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [sortBy, setSortBy] = useState<SortOption>('newest');

  const sourceOptions = useMemo(() => {
    const unique = new Set(entries.map((entry) => entry.source));
    return ['all', ...Array.from(unique)];
  }, [entries]);

  const sortedEntries = useMemo(() => {
    const sorted = [...entries];
    if (sortBy === 'title') {
      sorted.sort((a, b) => a.title.localeCompare(b.title, 'ko'));
      return sorted;
    }

    sorted.sort((a, b) => {
      const aTime = new Date(a.createdAt || 0).getTime();
      const bTime = new Date(b.createdAt || 0).getTime();
      return sortBy === 'newest' ? bTime - aTime : aTime - bTime;
    });
    return sorted;
  }, [entries, sortBy]);

  const filteredEntries = useMemo(() => {
    return sortedEntries.filter((entry) => {
      const fullText = `${entry.title} ${entry.content} ${entry.memo} ${entry.tags.join(' ')}`.toLowerCase();
      const queryMatch = fullText.includes(searchQuery.trim().toLowerCase());
      const categoryMatch = categoryFilter === 'all' || entry.categoryId === categoryFilter;
      const sourceMatch = sourceFilter === 'all' || entry.source === sourceFilter;
      return queryMatch && categoryMatch && sourceMatch;
    });
  }, [sortedEntries, searchQuery, categoryFilter, sourceFilter]);

  const groupedEntries = useMemo(() => {
    const now = Date.now();
    const oneWeek = 1000 * 60 * 60 * 24 * 7;
    const thisWeek = filteredEntries.filter((entry) => {
      if (!entry.createdAt) {
        return false;
      }
      return now - new Date(entry.createdAt).getTime() <= oneWeek;
    });
    const earlier = filteredEntries.filter((entry) => {
      if (!entry.createdAt) {
        return true;
      }
      return now - new Date(entry.createdAt).getTime() > oneWeek;
    });
    return { thisWeek, earlier };
  }, [filteredEntries]);

  const weeklySavedCount = useMemo(() => {
    const now = Date.now();
    const oneWeek = 1000 * 60 * 60 * 24 * 7;
    return entries.filter((entry) => {
      if (!entry.createdAt) {
        return false;
      }
      return now - new Date(entry.createdAt).getTime() <= oneWeek;
    }).length;
  }, [entries]);

  function resetFilters() {
    setSearchQuery('');
    setCategoryFilter('all');
    setSourceFilter('all');
  }

  return {
    searchQuery,
    setSearchQuery,
    categoryFilter,
    setCategoryFilter,
    sourceFilter,
    setSourceFilter,
    sortBy,
    setSortBy,
    sourceOptions,
    filteredEntries,
    groupedEntries,
    weeklySavedCount,
    resetFilters,
  };
}
