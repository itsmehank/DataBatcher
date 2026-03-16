import Link from 'next/link';
import { notFound } from 'next/navigation';
import { api } from '../../../lib/api';
import EntryComments from './entry-comments';
import { formatDateLong } from '../../../lib/date';
import type { Category } from '../../../types/category';
import type { Entry } from '../../../types/entry';

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
    entry.categoryId ? api<Entry[]>(`/entries?categoryId=${entry.categoryId}`).catch(() => []) : Promise.resolve([]),
  ]);

  const categoryName = categories.find((category) => category._id === entry.categoryId)?.name || '미분류';
  const relatedEntries = relatedRaw.filter((item) => item._id !== entry._id).slice(0, 4);

  return (
    <div>
      <section className="section">
        <div className="section-head">
          <div>
            <h1 className="section-title" style={{ fontSize: '42px' }}>
              인사이트 상세
            </h1>
            <p className="section-subtitle">저장한 항목을 읽고, 원문 대화로 바로 돌아갈 수 있습니다.</p>
          </div>
          <Link href="/" className="button-link secondary-link">
            아카이브로 돌아가기
          </Link>
        </div>
      </section>

      <section className="section detail-layout">
        <article className="panel detail-main">
          <div className="meta-row" style={{ marginBottom: 14 }}>
            <span>{categoryName}</span>
              <span>{formatDateLong(entry.createdAt)}</span>
          </div>

          <h2 className="detail-title">{entry.title}</h2>

          <p className="detail-content">{entry.content}</p>

          {entry.memo ? (
            <div className="detail-block">
              <h3 className="detail-block-title">기록 메모</h3>
              <p className="muted">{entry.memo}</p>
            </div>
          ) : null}

          <EntryComments entryId={entry._id} initialComments={entry.comments || []} />

          {entry.tags.length > 0 ? (
            <div className="detail-block">
              <h3 className="detail-block-title">태그</h3>
              <div className="tag-row" style={{ marginTop: 10 }}>
                {entry.tags.map((tag) => (
                  <span className="chip" key={`${entry._id}-${tag}`}>
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <div className="card-actions" style={{ marginTop: 20 }}>
            <a href={entry.conversationUrl} target="_blank" rel="noreferrer" className="button-link">
              원문 대화 열기
            </a>
          </div>
        </article>

        <aside className="panel detail-side">
          <h3 className="detail-block-title">관련 항목</h3>
          {relatedEntries.length > 0 ? (
            <div className="detail-related-list">
              {relatedEntries.map((item) => (
                <Link key={item._id} href={`/entries/${item._id}`} className="detail-related-item">
                  <strong className="clamp-2">{item.title}</strong>
                  <span className="muted clamp-2">{item.content}</span>
                </Link>
              ))}
            </div>
          ) : (
            <p className="muted">같은 카테고리의 다른 항목이 아직 없습니다.</p>
          )}
        </aside>
      </section>
    </div>
  );
}
