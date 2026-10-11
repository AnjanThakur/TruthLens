'use client';
import { usePreferences } from '@/components/preferences';
export default function ErrorBoundary({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = usePreferences();
  return (
    <main id="main" className="route-error">
      <h1>We couldn’t display this page.</h1>
      <p>Your unsaved report may need to be submitted again.</p>
      <button className="button primary" onClick={reset}>
        {t.retry}
      </button>
    </main>
  );
}
