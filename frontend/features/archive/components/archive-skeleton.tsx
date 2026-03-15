export default function ArchiveSkeleton() {
  return (
    <div className="grid-cards">
      {Array.from({ length: 6 }).map((_, index) => (
        <article className="card skeleton-card" key={`skeleton-${index}`}>
          <div className="skeleton-line skeleton-line-sm" />
          <div className="skeleton-line skeleton-line-lg" />
          <div className="skeleton-line" />
          <div className="skeleton-line" />
          <div className="skeleton-line skeleton-line-sm" />
        </article>
      ))}
    </div>
  );
}
