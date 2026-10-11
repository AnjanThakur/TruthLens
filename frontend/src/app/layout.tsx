import type { Metadata } from 'next';
import { PreferencesProvider } from '@/components/preferences';
import { Header, Footer } from '@/components/shell';
import './globals.css';
export const metadata: Metadata = {
  title: 'TruthLens AI — Check the facts behind a forward',
  description:
    'Inspect individual claims, traceable sources and honest uncertainty in forwarded messages.',
  robots: { index: false, follow: false },
};
export const dynamic = 'force-dynamic';
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <PreferencesProvider>
          <Header />
          {children}
          <Footer />
        </PreferencesProvider>
      </body>
    </html>
  );
}
