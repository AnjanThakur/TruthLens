'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ScanLine, ArrowUpRight, BookOpen } from 'lucide-react';
import { usePreferences } from './preferences';
import type { Language } from '@/lib/api/contracts';
export function Header() {
  const path = usePathname();
  const { language, easy, setLanguage, setEasy, t } = usePreferences();
  return (
    <>
      <a href="#main" className="skip-link">
        {t.skip}
      </a>
      <header className="site-header">
        <div className="header-inner">
          <Link href="/" className="brand" aria-label="TruthLens AI home">
            <span className="brand-mark">
              <ScanLine aria-hidden="true" size={23} />
            </span>
            <span>
              truthlens<span className="brand-ai"> AI</span>
            </span>
          </Link>
          <nav aria-label={t.navigation}>
            <Link href="/" aria-current={path === '/' ? 'page' : undefined}>
              {t.verify}
            </Link>
            <Link href="/history" aria-current={path === '/history' ? 'page' : undefined}>
              {t.history}
            </Link>
            <Link href="/alerts" aria-current={path === '/alerts' ? 'page' : undefined}>
              {language === 'hi'
                ? 'चेतावनी समीक्षा'
                : language === 'mr'
                  ? 'सूचना समीक्षा'
                  : 'Alert review'}
            </Link>
          </nav>
          <div className="preferences">
            <label className="sr-only" htmlFor="language">
              {t.language}
            </label>
            <select
              id="language"
              value={language}
              onChange={(e) => setLanguage(e.target.value as Language)}
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="mr">मराठी</option>
            </select>
            <button
              type="button"
              className="reading-toggle"
              aria-label={t.easy}
              aria-pressed={easy}
              onClick={() => setEasy(!easy)}
            >
              <BookOpen size={16} aria-hidden="true" />
              <span>{t.easy}</span>
            </button>
          </div>
        </div>
      </header>
    </>
  );
}
export function Footer() {
  const { t } = usePreferences();
  return (
    <footer className="site-footer">
      <div>
        <span className="footer-brand">truthlens AI</span>
        <p>{t.footer}</p>
      </div>
      <Link href="/privacy">
        {t.privacy}
        <ArrowUpRight size={15} aria-hidden="true" />
      </Link>
    </footer>
  );
}
