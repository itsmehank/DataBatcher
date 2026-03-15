'use client';

import TemplateListSection from '../../features/templates/components/template-list-section';
import TemplateSkeleton from '../../features/templates/components/template-skeleton';
import TemplatesComposerDrawer from '../../features/templates/components/templates-composer-drawer';
import TemplatesHero from '../../features/templates/components/templates-hero';
import TemplatesStatusMessages from '../../features/templates/components/templates-status-messages';
import TemplatesToolbar from '../../features/templates/components/templates-toolbar';
import { useTemplatesData } from '../../features/templates/hooks/use-templates-data';
import { useTemplatesFilters } from '../../features/templates/hooks/use-templates-filters';

export default function TemplatesPage() {
  const {
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
    onRequestCreate,
    onCreateTemplate,
    onCopy,
    onCancelCreate,
    setIsDrawerOpen,
  } = useTemplatesData();

  const { query, setQuery, useCaseFilter, setUseCaseFilter, useCaseOptions, filteredTemplates, resetFilters } =
    useTemplatesFilters(templates);

  return (
    <div className="archive-page template-page">
      <TemplatesHero totalCount={templates.length} visibleCount={filteredTemplates.length} onRequestCreate={onRequestCreate} />

      <TemplatesStatusMessages
        needsLoginHint={needsLoginHint}
        feedback={feedback}
        errorMessage={errorMessage}
        pageState={pageState}
      />

      <TemplatesToolbar
        query={query}
        useCaseFilter={useCaseFilter}
        useCaseOptions={useCaseOptions}
        onQueryChange={setQuery}
        onUseCaseFilterChange={setUseCaseFilter}
        onResetFilters={resetFilters}
        onRequestCreate={onRequestCreate}
      />

      <section className="section">
        {pageState === 'loading' ? <TemplateSkeleton /> : null}

        {pageState === 'error' ? (
          <div className="panel" style={{ padding: 16 }}>
            <p className="muted">문장을 잠시 불러오지 못했습니다. {errorMessage || '잠시 후 다시 시도해 주세요.'}</p>
            <div className="card-actions" style={{ marginTop: 10 }}>
              <button type="button" className="secondary" style={{ maxWidth: 120 }} onClick={() => initializePage()}>
                다시 읽기
              </button>
            </div>
          </div>
        ) : null}

        {pageState === 'ready' ? (
          <TemplateListSection templates={filteredTemplates} onCopy={onCopy} onRequestCreate={onRequestCreate} />
        ) : null}
      </section>

      <button type="button" className="fab" onClick={onRequestCreate} aria-label="새 문장 추가">
        +
      </button>

      <TemplatesComposerDrawer
        isOpen={isDrawerOpen}
        loading={loading}
        form={form}
        setForm={setForm}
        onSubmit={onCreateTemplate}
        onCancel={onCancelCreate}
        onClose={() => setIsDrawerOpen(false)}
      />
    </div>
  );
}
