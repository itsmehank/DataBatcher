import './globals.css';
import type { Metadata } from 'next';
import MainNav from './components/main-nav';

export const metadata: Metadata = {
  title: 'My Insight Archive',
  description: '대화 인사이트와 템플릿을 정리하는 개인 아카이브',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <header className="site-header">
          <MainNav />
        </header>
        <main className="page-shell page">{children}</main>
      </body>
    </html>
  );
}
