import type { Category } from '../../../types/category';

type ArchiveToolbarProps = {
  categories: Category[];
  searchQuery: string;
  categoryFilter: string;
  sourceFilter: string;
  sortBy: 'newest' | 'oldest' | 'title';
  sourceOptions: string[];
  onSearchQueryChange: (value: string) => void;
  onCategoryFilterChange: (value: string) => void;
  onSourceFilterChange: (value: string) => void;
  onSortByChange: (value: 'newest' | 'oldest' | 'title') => void;
  onResetFilters: () => void;
};

export default function ArchiveToolbar({
  categories,
  searchQuery,
  categoryFilter,
  sourceFilter,
  sortBy,
  sourceOptions,
  onSearchQueryChange,
  onCategoryFilterChange,
  onSourceFilterChange,
  onSortByChange,
  onResetFilters,
}: ArchiveToolbarProps) {
  return (
    <section className="section" id="archive-list">
      <div className="section-head">
        <div>
          <h2 className="section-title">모아둔 기록</h2>
        </div>
      </div>

      <div className="toolbar surface-card" role="region" aria-label="아카이브 탐색 도구">
        <input
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
          placeholder="제목, 내용, 태그 검색"
          aria-label="검색"
        />
        <select value={categoryFilter} onChange={(e) => onCategoryFilterChange(e.target.value)}>
          <option value="all">모든 기록 묶음</option>
          {categories.map((category) => (
            <option key={category._id} value={category._id}>
              {category.name}
            </option>
          ))}
        </select>
        <select value={sourceFilter} onChange={(e) => onSourceFilterChange(e.target.value)}>
          {sourceOptions.map((source) => (
            <option key={source} value={source}>
              {source === 'all' ? '모든 대화 출처' : source}
            </option>
          ))}
        </select>
        <select value={sortBy} onChange={(e) => onSortByChange(e.target.value as 'newest' | 'oldest' | 'title')}>
          <option value="newest">최근에 남긴 순</option>
          <option value="oldest">오래된 기록 순</option>
          <option value="title">제목 가나다순</option>
        </select>
        <button type="button" className="secondary" onClick={onResetFilters}>
          비우기
        </button>
      </div>
    </section>
  );
}
