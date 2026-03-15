type ArchiveHeroProps = {
  weeklySavedCount: number;
  totalEntries: number;
  onRequestCreate: () => void;
};

export default function ArchiveHero({ weeklySavedCount, totalEntries, onRequestCreate }: ArchiveHeroProps) {
  return (
    <section className="hero section">
      <div>
        <h1>남겨 둔 문장들</h1>
        <div className="hero-actions">
          <button type="button" onClick={onRequestCreate}>
            남기기
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => document.getElementById('archive-list')?.scrollIntoView({ behavior: 'smooth' })}
          >
            둘러보기
          </button>
        </div>
      </div>

      <aside className="surface-card hero-preview">
        <div className="tag-row" style={{ marginTop: 12 }}>
          <span className="chip chip-strong">이번 주 {weeklySavedCount}개 기록</span>
          <span className="chip">지금까지 {totalEntries}개의 기록</span>
        </div>
      </aside>
    </section>
  );
}
