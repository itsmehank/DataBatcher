import type { Dispatch, FormEvent, SetStateAction } from 'react';

type TemplateForm = {
  name: string;
  content: string;
  description: string;
  useCase: string;
  tags: string;
};

type TemplatesComposerDrawerProps = {
  isOpen: boolean;
  loading: boolean;
  form: TemplateForm;
  setForm: Dispatch<SetStateAction<TemplateForm>>;
  onSubmit: (e: FormEvent<HTMLFormElement>) => Promise<void>;
  onCancel: () => void;
  onClose: () => void;
};

export default function TemplatesComposerDrawer({
  isOpen,
  loading,
  form,
  setForm,
  onSubmit,
  onCancel,
  onClose,
}: TemplatesComposerDrawerProps) {
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
            aria-label="템플릿 작성 패널 닫기"
          >
            ×
          </button>
        </div>

        <form className="grid" onSubmit={onSubmit}>
          <input
            placeholder="문장 제목"
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            required
          />
          <textarea
            placeholder="시작 문장 (Markdown 가능)"
            value={form.content}
            onChange={(e) => setForm((prev) => ({ ...prev, content: e.target.value }))}
            rows={8}
            required
          />
          <input
            placeholder="이 문장을 꺼내 쓰는 상황"
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
          />
          <input
            placeholder="사용 케이스"
            value={form.useCase}
            onChange={(e) => setForm((prev) => ({ ...prev, useCase: e.target.value }))}
          />
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
