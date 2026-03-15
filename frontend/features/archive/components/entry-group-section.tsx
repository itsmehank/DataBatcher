import EntryCard from './entry-card';
import type { Entry } from '../../../types/entry';

type EntryGroupSectionProps = {
  title: string;
  entries: Entry[];
  username: string;
  deleteModeEntryId: string;
  deletingEntryId: string;
  categoryNameMap: Record<string, string>;
  onStartCardLongPress: (entryId: string, canDelete: boolean) => void;
  onCancelCardLongPress: () => void;
  onDeleteEntry: (entryId: string) => void;
};

export default function EntryGroupSection({
  title,
  entries,
  username,
  deleteModeEntryId,
  deletingEntryId,
  categoryNameMap,
  onStartCardLongPress,
  onCancelCardLongPress,
  onDeleteEntry,
}: EntryGroupSectionProps) {
  return (
    <>
      <div className="entry-group-head">
        <span>{title}</span>
        <span>{entries.length}</span>
      </div>
      <div className="grid-cards">
        {entries.map((entry) => {
          const canDelete = entry.createdBy === username;
          return (
            <EntryCard
              key={entry._id}
              entry={entry}
              categoryName={categoryNameMap[entry.categoryId || ''] || '미분류'}
              canDelete={canDelete}
              isDeleteMode={deleteModeEntryId === entry._id}
              isDeleting={deletingEntryId === entry._id}
              onPointerDown={() => onStartCardLongPress(entry._id, canDelete)}
              onPointerUp={onCancelCardLongPress}
              onPointerLeave={onCancelCardLongPress}
              onPointerCancel={onCancelCardLongPress}
              onDelete={() => onDeleteEntry(entry._id)}
            />
          );
        })}
      </div>
    </>
  );
}
