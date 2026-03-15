import type { Dispatch, FormEvent, SetStateAction } from 'react';
import type { Category } from '../../../types/category';

type ArchiveComposerForm = {
  title: string;
  content: string;
  memo: string;
  conversationUrl: string;
  source: string;
  categoryId: string;
  tags: string;
};

type ArchiveComposerDrawerProps = {
  isOpen: boolean;
  loading: boolean;
  categories: Category[];
  form: ArchiveComposerForm;
  setForm: Dispatch<SetStateAction<ArchiveComposerForm>>;
  onSubmit: (e: FormEvent<HTMLFormElement>) => Promise<void>;
  onCancel: () => void;
  onClose: () => void;
};

export default function ArchiveComposerDrawer({
  isOpen,
  loading,
  categories,
  form,
  setForm,
  onSubmit,
  onCancel,
  onClose,
}: ArchiveComposerDrawerProps) {
  return (
    <>
      <div className={`drawer-backdrop ${isOpen ? 'drawer-backdrop-open' : ''}`} onClick={() => !loading && onClose()} />

      <aside className={`drawer ${isOpen ? 'drawer-open' : ''}`}>
        <div className="drawer-head">
          <h3 style={{ margin: 0, fontSize: 22, fontWeight: 520 }}>남기기</h3>
          <button
            type="button"
            className="icon-button secondary"
            onClick={onClose}
            disabled={loading}
            aria-label="작성 패널 닫기"
          >
            ×
          </button>
        </div>

        <form className="grid" onSubmit={onSubmit}>
          <input
            placeholder="제목"
            value={form.title}
            onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
            required
          />
          <textarea
            placeholder="남기고 싶은 생각"
            value={form.content}
            onChange={(e) => setForm((prev) => ({ ...prev, content: e.target.value }))}
            rows={4}
            required
          />
          <textarea
            placeholder="메모"
            value={form.memo}
            onChange={(e) => setForm((prev) => ({ ...prev, memo: e.target.value }))}
            rows={3}
          />
          <input
            placeholder="대화 링크 URL"
            value={form.conversationUrl}
            onChange={(e) => setForm((prev) => ({ ...prev, conversationUrl: e.target.value }))}
            required
          />
          <select value={form.source} onChange={(e) => setForm((prev) => ({ ...prev, source: e.target.value }))}>
            <option value="chatgpt">ChatGPT</option>
            <option value="claude">Claude</option>
            <option value="gemini">Gemini</option>
            <option value="other">기타</option>
          </select>
          <select
            value={form.categoryId}
            onChange={(e) => setForm((prev) => ({ ...prev, categoryId: e.target.value }))}
            required
            disabled={categories.length === 0}
          >
            {categories.length === 0 ? <option value="">카테고리 없음</option> : null}
            {categories.map((category) => (
              <option key={category._id} value={category._id}>
                {category.name}
              </option>
            ))}
          </select>
          <input
            placeholder="태그 (쉼표로 구분)"
            value={form.tags}
            onChange={(e) => setForm((prev) => ({ ...prev, tags: e.target.value }))}
          />
          <div className="actions">
            <button type="submit" disabled={loading}>
              남기기
            </button>
            <button type="button" className="secondary" onClick={onCancel} disabled={loading}>
              닫기
            </button>
          </div>
        </form>
      </aside>
    </>
  );
}
