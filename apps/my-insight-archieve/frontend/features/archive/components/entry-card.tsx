import Link from 'next/link';
import { formatDateShort } from '../../../lib/date';
import type { Entry } from '../../../types/entry';

type EntryCardProps = {
  entry: Entry;
  categoryName: string;
  isDeleteMode: boolean;
  isDeleting: boolean;
  canDelete: boolean;
  onPointerDown: () => void;
  onPointerUp: () => void;
  onPointerLeave: () => void;
  onPointerCancel: () => void;
  onDelete: () => void;
};

export default function EntryCard({
  entry,
  categoryName,
  isDeleteMode,
  isDeleting,
  canDelete,
  onPointerDown,
  onPointerUp,
  onPointerLeave,
  onPointerCancel,
  onDelete,
}: EntryCardProps) {
  return (
    <article
      className={`card ${isDeleteMode ? 'card-delete-mode' : ''}`}
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerLeave}
      onPointerCancel={onPointerCancel}
    >
      {isDeleteMode && canDelete ? (
        <button
          type="button"
          className="card-delete-button"
          onClick={(event) => {
            event.stopPropagation();
            onDelete();
          }}
          disabled={isDeleting}
        >
          ×
        </button>
      ) : null}

      <div className="meta-row">
        <span>{categoryName}</span>
        <span>{formatDateShort(entry.createdAt)}</span>
      </div>

      <h3 className="card-title clamp-2">{entry.title}</h3>
      <p className="muted" style={{ marginTop: 8 }}>
        출처: {entry.source}
      </p>
      <p className="card-body clamp-3">{entry.content}</p>

      {entry.tags.length > 0 ? (
        <div className="tag-row">
          {entry.tags.slice(0, 3).map((tag) => (
            <span className="chip" key={`${entry._id}-${tag}`}>
              #{tag}
            </span>
          ))}
        </div>
      ) : null}

      <div className="card-actions">
        <Link href={`/entries/${entry._id}`} className="card-link">
          읽기
        </Link>
        <a href={entry.conversationUrl} target="_blank" rel="noreferrer" className="card-link">
          원문
        </a>
      </div>
    </article>
  );
}
