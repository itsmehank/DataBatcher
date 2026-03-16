'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '../../lib/use-auth';

const NAV_ITEMS = [
  { href: '/', label: '아카이브' },
  { href: '/templates', label: '템플릿' },
  { href: '/admin', label: '어드민' },
];

export default function MainNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading, logout } = useAuth();

  function onLogout() {
    logout();
    router.replace('/');
    router.refresh();
  }

  return (
    <div className="page-shell site-nav">
      <Link href="/" className="brand">
        <span className="brand-mark">IA</span>
        <span>My Insight Archive</span>
      </Link>
      <nav className="nav-links" aria-label="주요 메뉴">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);
          const classes = ['nav-link', isActive ? 'nav-link-active' : ''].filter(Boolean).join(' ');

          return (
            <Link key={item.href} href={item.href} className={classes}>
              {item.label}
            </Link>
          );
        })}

        {isLoading ? <span className="nav-link auth-link">확인중</span> : null}

        {!isLoading && !isAuthenticated ? (
          <Link href="/login" className="nav-link auth-link">
            로그인
          </Link>
        ) : null}

        {!isLoading && isAuthenticated ? (
          <button type="button" className="nav-link auth-link nav-link-button" onClick={onLogout}>
            로그아웃
          </button>
        ) : null}
      </nav>
    </div>
  );
}
