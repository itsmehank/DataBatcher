export default function TemplateSkeleton() {
  return (
    <div className="grid-cards">
      {Array.from({ length: 4 }).map((_, index) => (
        <article className="card skeleton-card" key={`template-skeleton-${index}`}>
          <div className="skeleton-line skeleton-line-sm" />
          <div className="skeleton-line skeleton-line-lg" />
          <div className="skeleton-line" />
          <div className="skeleton-line" />
        </article>
      ))}
    </div>
  );
}
