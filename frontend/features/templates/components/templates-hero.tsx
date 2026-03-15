type TemplatesHeroProps = {
  totalCount: number;
  visibleCount: number;
  onRequestCreate: () => void;
};

export default function TemplatesHero({ totalCount, visibleCount, onRequestCreate }: TemplatesHeroProps) {
  return (
    <section className="hero section">
      <div>
        <h1>템플릿 저장소</h1>
        <div className="hero-actions">
          <button type="button" onClick={onRequestCreate}>
            남기기
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => document.getElementById('template-list')?.scrollIntoView({ behavior: 'smooth' })}
          >
            둘러보기
          </button>
        </div>
      </div>

      <aside className="surface-card hero-preview">
        <div className="tag-row" style={{ marginTop: 12 }}>
          <span className="chip chip-strong">전체 {totalCount}개</span>
          <span className="chip">보이는 {visibleCount}개</span>
        </div>
      </aside>
    </section>
  );
}
