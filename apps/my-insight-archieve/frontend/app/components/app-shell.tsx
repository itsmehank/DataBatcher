'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/use-auth';
import type { Category } from '../../types/category';
import type { Entry } from '../../types/entry';

const NAV_ITEMS = [
  { label: '아카이브', href: '/', exact: true },
  { label: '템플릿', href: '/templates', exact: false },
  { label: '어드민', href: '/admin', exact: false },
] as const;

type CategoryWithCount = Category & { count: number };

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, username, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [categories, setCategories] = useState<CategoryWithCount[]>([]);
  const [activeCategoryId, setActiveCategoryId] = useState('');

  const closeSidebar = useCallback(() => {
    setSidebarOpen(false);
  }, []);

  useEffect(() => {
    let mounted = true;

    async function loadSidebarData() {
      try {
        const [categoriesRes, entriesRes] = await Promise.all([
          api<Category[]>('/categories'),
          api<Entry[]>('/entries'),
        ]);

        if (!mounted) {
          return;
        }

        const counts = entriesRes.reduce<Record<string, number>>((acc, entry) => {
          if (!entry.categoryId) {
            return acc;
          }
          acc[entry.categoryId] = (acc[entry.categoryId] ?? 0) + 1;
          return acc;
        }, {});

        const merged = categoriesRes.map((category) => ({
          ...category,
          count: counts[category._id] ?? 0,
        }));
        setCategories(merged);
      } catch {
        if (mounted) {
          setCategories([]);
        }
      }
    }

    loadSidebarData().catch(() => undefined);

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    closeSidebar();
  }, [pathname, closeSidebar]);

  const navItems = useMemo(() => {
    return NAV_ITEMS.map((item) => {
      const isActive = item.exact ? pathname === item.href : pathname.startsWith(item.href);
      return { ...item, isActive };
    });
  }, [pathname]);

  const handleCategoryClick = useCallback(
    (categoryId: string) => {
      const params = new URLSearchParams(window.location.search);
      params.set('category', categoryId);
      const query = params.toString();
      router.push(query ? `/?${query}` : '/');
      window.dispatchEvent(new CustomEvent('insight:set-category-filter', { detail: { categoryId } }));
      closeSidebar();
    },
    [closeSidebar, router],
  );

  useEffect(() => {
    const syncCategory = () => {
      if (pathname !== '/') {
        setActiveCategoryId('');
        return;
      }
      const params = new URLSearchParams(window.location.search);
      setActiveCategoryId(params.get('category') || '');
    };

    syncCategory();
    const onCategoryChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ categoryId?: string }>).detail;
      setActiveCategoryId(detail?.categoryId || '');
    };
    window.addEventListener('popstate', syncCategory);
    window.addEventListener('insight:set-category-filter', onCategoryChanged as EventListener);
    return () => {
      window.removeEventListener('popstate', syncCategory);
      window.removeEventListener('insight:set-category-filter', onCategoryChanged as EventListener);
    };
  }, [pathname]);

  return (
    <div className="v2-root">
      <div className={`v2-overlay${sidebarOpen ? ' visible' : ''}`} onClick={closeSidebar} />

      <div className="v2-mobile-topbar">
        <button
          type="button"
          className="v2-hamburger"
          onClick={() => setSidebarOpen(true)}
          aria-label="메뉴 열기"
        >
          ☰
        </button>
        <span className="v2-mobile-brand">Insight Archive</span>
      </div>

      <aside className={`v2-sidebar${sidebarOpen ? ' open' : ''}`}>
        <Link href="/" className="v2-sidebar-brand" onClick={closeSidebar}>
          <div className="v2-sidebar-brand-icon">IA</div>
          <span className="v2-sidebar-brand-text">Insight Archive</span>
        </Link>

        <nav className="v2-sidebar-nav" aria-label="기본 탐색">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`v2-nav-item${item.isActive ? ' active' : ''}`}
              onClick={closeSidebar}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="v2-sidebar-divider" />

        <div className="v2-sidebar-section-label">카테고리</div>
        <ul className="v2-sidebar-categories">
          {categories.map((category) => (
            <li key={category._id}>
              <button
                type="button"
                className={`v2-sidebar-cat-item${activeCategoryId === category._id ? ' active' : ''}`}
                onClick={() => handleCategoryClick(category._id)}
              >
                <span className="v2-sidebar-cat-dot" style={{ background: category.color }} />
                <span className="v2-sidebar-cat-name">{category.name}</span>
                <span className="v2-sidebar-cat-count">{category.count}</span>
              </button>
            </li>
          ))}
        </ul>

        <div className="v2-sidebar-footer">
          {isAuthenticated ? (
            <>
              <span className="v2-sidebar-user">{username}</span>
              <button type="button" className="v2-sidebar-logout" onClick={() => logout()}>
                로그아웃
              </button>
            </>
          ) : (
            <Link href="/login" className="v2-sidebar-login" onClick={closeSidebar}>
              로그인
            </Link>
          )}
        </div>
      </aside>

      <main className="v2-content">{children}</main>
    </div>
  );
}
