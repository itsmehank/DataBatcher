import Link from 'next/link';

type TemplatesStatusMessagesProps = {
  needsLoginHint: boolean;
  feedback: string;
  errorMessage: string;
  pageState: 'loading' | 'ready' | 'error';
};

export default function TemplatesStatusMessages({
  needsLoginHint,
  feedback,
  errorMessage,
  pageState,
}: TemplatesStatusMessagesProps) {
  return (
    <>
      {needsLoginHint ? (
        <section className="section" style={{ marginBottom: 18 }}>
          <div className="panel">
            <p className="muted">로그인 후 남길 수 있습니다.</p>
            <div className="card-actions" style={{ marginTop: 12 }}>
              <Link href="/login" className="button-link">
                로그인
              </Link>
            </div>
          </div>
        </section>
      ) : null}

      {feedback ? <p className="muted">{feedback}</p> : null}
      {errorMessage && pageState !== 'error' ? <p className="muted">{errorMessage}</p> : null}
    </>
  );
}
