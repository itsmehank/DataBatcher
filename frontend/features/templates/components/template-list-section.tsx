import Link from 'next/link';
import type { Template } from '../../../types/template';

type TemplateListSectionProps = {
  templates: Template[];
  onCopy: (content: string) => Promise<void>;
  onRequestCreate: () => void;
};

export default function TemplateListSection({ templates, onCopy, onRequestCreate }: TemplateListSectionProps) {
  const hasNoTemplates = templates.length === 0;

  return (
    <>
      <div className="grid-cards">
        {templates.map((template) => (
          <article key={template._id} className="card">
            <div className="meta-row">
              <span>{template.useCase || '일반 템플릿'}</span>
            </div>
            <h3 className="card-title clamp-2">{template.name}</h3>
            {template.description ? (
              <p className="muted clamp-2" style={{ marginTop: 8 }}>
                {template.description}
              </p>
            ) : null}
            <p className="card-body clamp-3">{template.content}</p>
            {template.tags.length > 0 ? (
              <div className="tag-row">
                {template.tags.slice(0, 3).map((tag) => (
                  <span className="chip" key={`${template._id}-${tag}`}>
                    #{tag}
                  </span>
                ))}
              </div>
            ) : null}
            <div className="card-actions">
              <button type="button" className="card-link card-link-button" onClick={() => onCopy(template.content)}>
                복사
              </button>
            </div>
          </article>
        ))}
      </div>

      {hasNoTemplates ? (
        <article className="panel empty-state-card" style={{ marginTop: 20 }}>
          <div>
            <h3 className="card-title" style={{ fontSize: 22 }}>
              아직 없습니다.
            </h3>
          </div>
          <div className="empty-state-actions">
            <button type="button" onClick={onRequestCreate}>
              남기기
            </button>
            <Link href="/login" className="button-link secondary-link">
              로그인
            </Link>
          </div>
        </article>
      ) : null}
    </>
  );
}
