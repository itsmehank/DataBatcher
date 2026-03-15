type TemplatesToolbarProps = {
  query: string;
  useCaseFilter: string;
  useCaseOptions: string[];
  onQueryChange: (value: string) => void;
  onUseCaseFilterChange: (value: string) => void;
  onResetFilters: () => void;
  onRequestCreate: () => void;
};

export default function TemplatesToolbar({
  query,
  useCaseFilter,
  useCaseOptions,
  onQueryChange,
  onUseCaseFilterChange,
  onResetFilters,
  onRequestCreate,
}: TemplatesToolbarProps) {
  return (
    <section className="section" id="template-list">
      <div className="section-head">
        <div>
          <h2 className="section-title">모아둔 템플릿</h2>
        </div>
      </div>

      <div className="toolbar surface-card">
        <input
          placeholder="문장, 주제, 태그로 찾기"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          aria-label="템플릿 검색"
        />
        <select value={useCaseFilter} onChange={(e) => onUseCaseFilterChange(e.target.value)}>
          {useCaseOptions.map((useCase) => (
            <option key={useCase} value={useCase}>
              {useCase === 'all' ? '모든 사용 케이스' : useCase}
            </option>
          ))}
        </select>
        <button type="button" className="secondary" onClick={onResetFilters}>
          비우기
        </button>
        <button type="button" className="secondary" onClick={onRequestCreate}>
          남기기
        </button>
      </div>
    </section>
  );
}
