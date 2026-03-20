import Link from 'next/link';
import { notFound } from 'next/navigation';
import { api } from '../../../lib/api';
import { formatDateLong } from '../../../lib/date';
import type { Category } from '../../../types/category';
import type { Entry } from '../../../types/entry';
import EntryComments from './entry-comments';
import EntryMemo from './entry-memo';

export default async function EntryDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let entry: Entry;
  try {
    entry = await api<Entry>(`/entries/${id}`);
  } catch {
    notFound();
  }

  const [categories, relatedRaw] = await Promise.all([
    api<Category[]>('/categories').catch(() => []),
    entry.categoryId
      ? api<Entry[]>(`/entries?categoryId=${entry.categoryId}`).catch(() => [])
      : Promise.resolve([]),
  ]);

  const currentCategory = categories.find((category) => category._id === entry.categoryId);
  const categoryName = currentCategory?.name || '미분류';
  const categoryColor = currentCategory?.color || 'var(--border)';
  const relatedEntries = relatedRaw.filter((item) => item._id !== entry._id).slice(0, 4);

  return (
    <section className="v2-detail-page">
      <div className="v2-detail-layout">
        <article className="v2-detail-main" style={{ borderLeftColor: categoryColor }}>
          <div className="v2-detail-meta">
            <span>{categoryName}</span>
            <span>{formatDateLong(entry.createdAt)}</span>
          </div>

          <h1 className="v2-detail-title">{entry.title}</h1>

          <div className="v2-detail-content">{entry.content}</div>

          <EntryMemo entryId={entry._id} initialMemo={entry.memo || ''} />

          {entry.tags.length > 0 ? (
            <div className="v2-detail-tags">
              {entry.tags.map((tag) => (
                <span key={`${entry._id}-${tag}`}>#{tag}</span>
              ))}
            </div>
          ) : null}

          {entry.conversationUrl ? (
            <a href={entry.conversationUrl} target="_blank" rel="noreferrer" className="v2-detail-action">
              원문 대화 열기
            </a>
          ) : null}

          <EntryComments entryId={entry._id} initialComments={entry.comments || []} />
        </article>

        <aside className="v2-detail-sidebar">
          <h2>관련 항목</h2>
          {relatedEntries.length > 0 ? (
            relatedEntries.map((item) => (
              <Link key={item._id} href={`/entries/${item._id}`} className="v2-detail-related-item">
                <strong>{item.title}</strong>
                <p>{item.content}</p>
              </Link>
            ))
          ) : (
            <p>같은 카테고리의 다른 항목이 아직 없습니다.</p>
          )}
        </aside>
      </div>
    </section>
  );
}
