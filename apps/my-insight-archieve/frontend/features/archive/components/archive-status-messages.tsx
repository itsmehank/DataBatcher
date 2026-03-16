import Link from 'next/link';

type ArchiveStatusMessagesProps = {
  needsLoginHint: boolean;
  feedback: string;
  errorMessage: string;
  pageState: 'loading' | 'ready' | 'error';
};

export default function ArchiveStatusMessages({
  needsLoginHint,
  feedback,
  errorMessage,
  pageState,
}: ArchiveStatusMessagesProps) {
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

      {feedback ? (
        <section className="section" style={{ marginBottom: 12 }}>
          <p className="muted">{feedback}</p>
        </section>
      ) : null}

      {errorMessage && pageState !== 'error' ? (
        <section className="section" style={{ marginBottom: 12 }}>
          <p className="muted">{errorMessage}</p>
        </section>
      ) : null}
    </>
  );
}
