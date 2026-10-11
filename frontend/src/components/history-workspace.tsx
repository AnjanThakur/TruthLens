'use client';
import { useEffect, useRef, useState } from 'react';
import { z } from 'zod';
import { LockKeyhole, LoaderCircle, Trash2, LogOut, Mail } from 'lucide-react';
import { usePreferences } from './preferences';
import { Results } from './results';
import { historySchema, type ReportRow } from '@/lib/history/contracts';
import { request, jsonRequest } from '@/lib/api/client';
import { ApiError, errorMessage } from '@/lib/api/errors';
import { locale, verdictLabels } from '@/lib/i18n';
import { uiError } from '@/lib/i18n/errors';
export function HistoryWorkspace({ enabled }: { enabled: boolean }) {
  const { t, language } = usePreferences();
  const [email, setEmail] = useState('');
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const operation = useRef(false);
  useEffect(() => {
    if (!enabled) return;
    const abort = new AbortController();
    request('/api/history', historySchema, { signal: abort.signal })
      .then((value) => {
        setReports(value.reports);
        setCursor(value.next_cursor);
        setAuthenticated(true);
      })
      .catch((failure) => {
        if (
          !abort.signal.aborted &&
          !(failure instanceof ApiError && failure.code === 'UNAUTHENTICATED')
        )
          setError(failure instanceof Error ? failure.message : errorMessage('STORAGE_ERROR'));
      });
    if (new URLSearchParams(window.location.search).get('auth') === 'failed') {
      // Callback status is external browser state, read on mount.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setError(t.authFailed);
    }
    return () => abort.abort();
  }, [enabled, t.authFailed]);
  async function action(run: () => Promise<void>) {
    if (operation.current) return;
    operation.current = true;
    setBusy(true);
    setError('');
    setStatus('');
    try {
      await run();
    } catch (failure) {
      if (failure instanceof ApiError && failure.code === 'UNAUTHENTICATED') {
        setReports([]);
        setAuthenticated(false);
      }
      setError(uiError(failure, language));
    } finally {
      setBusy(false);
      operation.current = false;
    }
  }
  const load = (more: boolean) =>
    action(async () => {
      const value = await request(
        `/api/history${more && cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`,
        historySchema,
      );
      setReports((previous) => (more ? [...previous, ...value.reports] : value.reports));
      setCursor(value.next_cursor);
      setAuthenticated(true);
    });
  return (
    <main id="main" className="page-container">
      <div className="eyebrow">
        <LockKeyhole size={16} aria-hidden="true" />
        {t.history}
      </div>
      <h1>{t.historyTitle}</h1>
      <p className="page-intro">{t.historyIntro}</p>
      {!enabled ? (
        <p className="notice">{t.historyDisabled}</p>
      ) : (
        <>
          {!authenticated && (
            <form
              className="history-auth"
              onSubmit={(e) => {
                e.preventDefault();
                void action(async () => {
                  await request(
                    '/api/auth/email',
                    z.object({ sent: z.boolean() }),
                    jsonRequest({ email }),
                  );
                  setStatus(t.emailSent);
                });
              }}
            >
              <label htmlFor="email">{t.email}</label>
              <input
                type="email"
                id="email"
                autoComplete="email"
                required
                maxLength={254}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={busy}
              />
              <button type="submit" className="button primary" disabled={busy}>
                {busy ? <LoaderCircle size={18} className="spinner" /> : <Mail size={18} />}
                {t.signIn}
              </button>
            </form>
          )}
          <div className="history-toolbar">
            <button className="button secondary" disabled={busy} onClick={() => load(false)}>
              {t.load}
            </button>
            {authenticated && (
              <button
                className="button secondary"
                disabled={busy}
                onClick={() =>
                  action(async () => {
                    await request(
                      '/api/auth/signout',
                      z.object({ signed_out: z.boolean() }),
                      jsonRequest({}),
                    );
                    setAuthenticated(false);
                    setReports([]);
                    setCursor(null);
                  })
                }
              >
                <LogOut size={17} />
                {t.signOut}
              </button>
            )}
          </div>
          {authenticated && !reports.length && <p className="notice">{t.emptyHistory}</p>}
          {reports.map((row) => (
            <article key={row.id} className="history-row">
              <details>
                <summary>{row.input_excerpt}</summary>
                <p>
                  <time dateTime={row.created_at}>
                    {new Intl.DateTimeFormat(locale[language], {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    }).format(new Date(row.created_at))}
                  </time>{' '}
                  · {row.input_type}
                </p>
                <p>
                  {row.report_json.claims
                    .map((c) => verdictLabels[language][c.verdict])
                    .join(' · ')}
                </p>
                <p>
                  {t.retention}:{' '}
                  <time dateTime={row.retention_expires_at}>
                    {new Intl.DateTimeFormat(locale[language], { dateStyle: 'medium' }).format(
                      new Date(row.retention_expires_at),
                    )}
                  </time>
                </p>
                <Results result={row.report_json} />
              </details>
              {deleteId === row.id ? (
                <div>
                  <p>{t.deleteConfirm}</p>
                  <button
                    className="button secondary danger"
                    disabled={busy}
                    onClick={() =>
                      action(async () => {
                        await request('/api/history', z.object({ deleted: z.boolean() }), {
                          ...jsonRequest({ id: row.id }),
                          method: 'DELETE',
                        });
                        setReports((previous) => previous.filter((report) => report.id !== row.id));
                        setDeleteId(null);
                      })
                    }
                  >
                    <Trash2 size={16} />
                    {t.delete}
                  </button>
                  <button
                    className="button quiet"
                    onClick={() => setDeleteId(null)}
                    disabled={busy}
                  >
                    {t.cancel}
                  </button>
                </div>
              ) : (
                <button
                  className="button secondary danger"
                  disabled={busy}
                  onClick={() => setDeleteId(row.id)}
                >
                  <Trash2 size={16} />
                  {t.delete}
                </button>
              )}
            </article>
          ))}
          {cursor && authenticated && (
            <button className="button secondary" disabled={busy} onClick={() => load(true)}>
              {t.more}
            </button>
          )}
        </>
      )}
      {status && (
        <p role="status" className="status-message">
          {status}
        </p>
      )}
      {error && (
        <p role="alert" className="notice">
          {error}
        </p>
      )}
    </main>
  );
}
