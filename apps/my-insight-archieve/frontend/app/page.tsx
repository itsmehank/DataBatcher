'use client';

import { api } from '../lib/api';
import { isUnauthorizedError } from '../lib/errors';
import { useAuth } from '../lib/use-auth';
import ArchiveComposerDrawer from '../features/archive/components/archive-composer-drawer';
import ArchiveHero from '../features/archive/components/archive-hero';
import ArchiveSkeleton from '../features/archive/components/archive-skeleton';
import ArchiveStatusMessages from '../features/archive/components/archive-status-messages';
import ArchiveToolbar from '../features/archive/components/archive-toolbar';
import EntryGroupSection from '../features/archive/components/entry-group-section';
import { useArchiveData } from '../features/archive/hooks/use-archive-data';
import { useArchiveFilters } from '../features/archive/hooks/use-archive-filters';
import { useCardDeleteMode } from '../features/archive/hooks/use-card-delete-mode';

export default function HomePage() {
  const { isAuthenticated, username } = useAuth();

  const {
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
  } = useArchiveData(isAuthenticated);

  const {
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
  } = useArchiveFilters(entries);

  const {
    deleteModeEntryId,
    deletingEntryId,
    softHint,
    startCardLongPress,
    cancelCardLongPress,
    startDeleting,
    finishDeleting,
    clearDeleteMode,
  } = useCardDeleteMode();

  async function onDeleteEntry(entryId: string) {
    if (!isAuthenticated) {
      setNeedsLoginHint(true);
      setFeedback('삭제는 로그인 후 사용할 수 있습니다.');
      return;
    }

    const confirmed = window.confirm('이 기록을 삭제할까요?');
    if (!confirmed) {
      return;
    }

    startDeleting(entryId);
    setErrorMessage('');
    setFeedback('');
    try {
      await api(`/entries/${entryId}`, { method: 'DELETE' });
      await loadData();
      clearDeleteMode();
      setFeedback('기록을 삭제했습니다.');
    } catch (error) {
      const typedError = error as Error;
      if (isUnauthorizedError(typedError)) {
        setNeedsLoginHint(true);
        setFeedback('로그인 후 다시 시도해 주세요.');
      } else {
        setErrorMessage(typedError.message);
      }
    } finally {
      finishDeleting();
    }
  }

  return (
    <div className="archive-page">
      <ArchiveHero weeklySavedCount={weeklySavedCount} totalEntries={entries.length} onRequestCreate={onRequestCreate} />

      <ArchiveStatusMessages
        needsLoginHint={needsLoginHint}
        feedback={feedback}
        errorMessage={errorMessage}
        pageState={pageState}
      />

      <ArchiveToolbar
        categories={categories}
        searchQuery={searchQuery}
        categoryFilter={categoryFilter}
        sourceFilter={sourceFilter}
        sortBy={sortBy}
        sourceOptions={sourceOptions}
        onSearchQueryChange={setSearchQuery}
        onCategoryFilterChange={setCategoryFilter}
        onSourceFilterChange={setSourceFilter}
        onSortByChange={setSortBy}
        onResetFilters={resetFilters}
      />

      <section className="section">
        {pageState === 'loading' ? <ArchiveSkeleton /> : null}

        {pageState === 'error' ? (
          <div className="panel" style={{ padding: 16 }}>
            <p className="muted">기록을 불러오지 못했습니다. {errorMessage || '잠시 후 다시 시도해 주세요.'}</p>
            <div className="card-actions" style={{ marginTop: 10 }}>
              <button type="button" className="secondary" style={{ maxWidth: 120 }} onClick={() => initializePage()}>
                다시 읽기
              </button>
            </div>
          </div>
        ) : null}

        {pageState === 'ready' ? (
          <>
            <EntryGroupSection
              title="이번주 글들"
              entries={groupedEntries.thisWeek}
              username={username}
              deleteModeEntryId={deleteModeEntryId}
              deletingEntryId={deletingEntryId}
              categoryNameMap={categoryNameMap}
              onStartCardLongPress={startCardLongPress}
              onCancelCardLongPress={cancelCardLongPress}
              onDeleteEntry={(entryId) => onDeleteEntry(entryId).catch(() => undefined)}
            />

            <EntryGroupSection
              title="이전 글들"
              entries={groupedEntries.earlier}
              username={username}
              deleteModeEntryId={deleteModeEntryId}
              deletingEntryId={deletingEntryId}
              categoryNameMap={categoryNameMap}
              onStartCardLongPress={startCardLongPress}
              onCancelCardLongPress={cancelCardLongPress}
              onDeleteEntry={(entryId) => onDeleteEntry(entryId).catch(() => undefined)}
            />

            {filteredEntries.length === 0 ? (
              <article className="panel">
                <h3 className="card-title" style={{ fontSize: 22 }}>
                  아직 없습니다.
                </h3>
              </article>
            ) : null}
          </>
        ) : null}
      </section>

      {softHint ? <div className="archive-soft-hint">{softHint}</div> : null}

      <button type="button" className="fab" onClick={onRequestCreate} aria-label="새 기록 남기기">
        +
      </button>

      <ArchiveComposerDrawer
        isOpen={isDrawerOpen}
        loading={loading}
        categories={categories}
        form={form}
        setForm={setForm}
        onSubmit={onCreateEntry}
        onCancel={onCancelCreate}
        onClose={() => setIsDrawerOpen(false)}
      />
    </div>
  );
}
