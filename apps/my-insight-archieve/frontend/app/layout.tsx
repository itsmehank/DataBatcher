import './globals.css';
import './app-shell.css';
import type { Metadata } from 'next';
import AppShell from './components/app-shell';

export const metadata: Metadata = {
  title: 'My Insight Archive',
  description: '대화 인사이트와 템플릿을 정리하는 개인 아카이브',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
