'use client';
import Link from 'next/link';
import { useState } from 'react';
import { z } from 'zod';
import { request, jsonRequest } from '@/lib/api/client';
import {
  dashboardSchema,
  draftSchema,
  type AlertDashboard,
  type AlertDraft,
} from '@/lib/alerts/contracts';
import { uiError } from '@/lib/i18n/errors';
import { usePreferences } from './preferences';

function DraftCard({
  draft,
  evidence,
  busy,
  act,
}: {
  draft: AlertDraft;
  evidence: AlertDashboard['clusters'][number]['evidence_references'];
  busy: boolean;
  act: (value: object) => Promise<void>;
}) {
  const [reviewed, setReviewed] = useState(false);
  const [title, setTitle] = useState(draft.title);
  const [summary, setSummary] = useState(draft.claim_summary ?? '');
  const [explanation, setExplanation] = useState(draft.explanation);
  const [translation, setTranslation] = useState(false);
  const version = { alert_id: draft.alert_id, expected_version: draft.content_version };
  const eligible = evidence.filter((source) => source.eligible);
  return (
    <article className="claim-card">
      <h3>{draft.title}</h3>
      <p className="meta-line">
        {draft.language.toUpperCase()} · {draft.approval_status.replaceAll('_', ' ')} · Version{' '}
        {draft.content_version}
      </p>
      <p>{draft.claim_summary ?? 'Translation requires review.'}</p>
      <p>{draft.explanation}</p>
      <p>{draft.scope_note}</p>
      <p>
        Risk indicators: {draft.scam_warning_signs.join(', ') || 'None recorded'}. These do not
        establish fraud.
      </p>
      <p>Expires: {new Date(draft.expires_at).toLocaleString()}</p>
      <details>
        <summary>Review source passages ({eligible.length} eligible)</summary>
        {evidence.map((source, i) => (
          <div className="evidence-record" key={source.url + i}>
            <a href={source.url} target="_blank" rel="noopener noreferrer">
              {source.publisher}: {source.url}
            </a>
            <p>{source.eligible ? source.stance : 'Not eligible for approval'}</p>
            <blockquote>{source.excerpt}</blockquote>
            <p>
              Published: {source.published_at || 'Not established'} · Retrieved:{' '}
              {source.retrieved_at}
            </p>
          </div>
        ))}
      </details>
      {['draft', 'pending_review'].includes(draft.approval_status) && (
        <>
          <details>
            <summary>Edit / review translation</summary>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void act({
                  action: 'edit',
                  ...version,
                  title,
                  claim_summary: summary,
                  explanation,
                  translation_reviewed: translation,
                });
              }}
            >
              <label>
                Title
                <input
                  value={title}
                  maxLength={160}
                  required
                  onChange={(event) => setTitle(event.target.value)}
                />
              </label>
              <label>
                Claim summary
                <textarea
                  value={summary}
                  maxLength={1200}
                  required
                  onChange={(event) => setSummary(event.target.value)}
                />
              </label>
              <label>
                Explanation
                <textarea
                  value={explanation}
                  maxLength={1800}
                  required
                  onChange={(event) => setExplanation(event.target.value)}
                />
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={translation}
                  onChange={(event) => setTranslation(event.target.checked)}
                />{' '}
                I reviewed this language’s translation.
              </label>
              <button className="button secondary" disabled={busy}>
                Save revision
              </button>
            </form>
          </details>
          <div className="results-actions">
            {draft.approval_status === 'draft' && (
              <button
                className="button secondary"
                disabled={busy || draft.language_content_status !== 'ready'}
                onClick={() => void act({ action: 'submit', ...version })}
              >
                Submit for review
              </button>
            )}
            {draft.approval_status === 'pending_review' && (
              <>
                <label>
                  <input
                    type="checkbox"
                    checked={reviewed}
                    onChange={(event) => setReviewed(event.target.checked)}
                  />{' '}
                  I reviewed the eligible source passages and current dates.
                </label>
                <button
                  className="button primary"
                  disabled={busy || !reviewed || !eligible.length}
                  onClick={() =>
                    void act({ action: 'approve', ...version, evidence_reviewed: true })
                  }
                >
                  Approve reviewed candidate
                </button>
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() =>
                    void act({ action: 'reject', ...version, reason: 'insufficient_evidence' })
                  }
                >
                  Reject: insufficient evidence
                </button>
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() =>
                    void act({ action: 'reject', ...version, reason: 'translation_needed' })
                  }
                >
                  Reject: translation needed
                </button>
              </>
            )}
          </div>
        </>
      )}
      {draft.approval_status === 'approved' && (
        <p>Reviewed candidate retained. No channel publication or automatic message was sent.</p>
      )}
    </article>
  );
}

export function AlertsWorkspace({ enabled }: { enabled: boolean }) {
  const { language } = usePreferences();
  const [data, setData] = useState<AlertDashboard | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  async function load() {
    setBusy(true);
    setStatus('');
    try {
      setData(await request('/api/alerts/review', dashboardSchema));
    } catch (error) {
      setData(null);
      setStatus(uiError(error, language));
    } finally {
      setBusy(false);
    }
  }
  async function act(value: object) {
    setBusy(true);
    try {
      await request('/api/alerts/review', z.object({ draft: draftSchema }), jsonRequest(value));
      setData(await request('/api/alerts/review', dashboardSchema));
      setStatus('Review saved. No public alert or WhatsApp message was sent.');
    } catch (error) {
      setStatus(uiError(error, language));
    } finally {
      setBusy(false);
    }
  }
  async function withdraw() {
    setBusy(true);
    try {
      await request(
        '/api/alerts/withdraw',
        z.object({ withdrawn: z.literal(true) }),
        jsonRequest({}),
      );
      setData(null);
      setStatus(
        'Your retained alert contributions were withdrawn. Affected approvals require fresh review.',
      );
    } catch (error) {
      setStatus(uiError(error, language));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main id="main" className="workspace">
      <section className="hero">
        <div className="eyebrow">CONSENTED ALERT INTELLIGENCE</div>
        <h1>Alert review</h1>
        <p>
          Review recurring narratives from consenting contributors. A fact-check verdict and a
          scam-risk warning are separate. Nothing is automatically published.
        </p>
      </section>
      <section className="input-panel">
        <h2>Contribution privacy</h2>
        <p>
          Sign in through <Link href="/history">private history</Link>. Withdraw deletes your
          retained observations and invalidates affected candidates. Repeat submissions by one
          account do not count as independent contributors.
        </p>
        {!enabled ? (
          <p role="status">
            Alert integration is not configured. Verification remains available; no contributions or
            demo alerts are stored here.
          </p>
        ) : (
          <div className="results-actions">
            <button className="button secondary" disabled={busy} onClick={() => void withdraw()}>
              Withdraw my alert contributions
            </button>
            <button className="button secondary" disabled={busy} onClick={() => void load()}>
              Load reviewer dashboard
            </button>
          </div>
        )}
        <p>
          Reviewer access must be granted by the project administrator. Sign-in alone does not grant
          approval permissions.
        </p>
        {status && <p role="status">{status}</p>}
      </section>
      {data && (
        <>
          <section className="input-panel">
            <h2>Consented clusters ({data.clusters.length})</h2>
            {!data.clusters.length && <p>No consented clusters available.</p>}
            {data.clusters.map((cluster) => (
              <article className="evidence-record" key={cluster.cluster_id}>
                <h3>{cluster.canonical_claim}</h3>
                <p>
                  {cluster.unique_submission_count} independent contributors ·{' '}
                  {cluster.status.replaceAll('_', ' ')}
                </p>
                <p>{cluster.trend?.scope}</p>
                <div className="results-actions">
                  {(['en', 'hi', 'mr'] as const).map((target) => (
                    <button
                      className="button secondary"
                      key={target}
                      disabled={busy}
                      onClick={() =>
                        void act({
                          action: 'create',
                          cluster_id: cluster.cluster_id,
                          language: target,
                        })
                      }
                    >
                      Create {target.toUpperCase()} candidate
                    </button>
                  ))}
                </div>
              </article>
            ))}
          </section>
          <section className="claim-list">
            <h2>Review candidates ({data.drafts.length})</h2>
            {!data.drafts.length && <p>No evidence-gated candidates yet.</p>}
            {data.drafts.map((draft) => (
              <DraftCard
                key={`${draft.alert_id}-${draft.content_version}-${draft.approval_status}`}
                draft={draft}
                evidence={
                  data.clusters.find((cluster) => cluster.cluster_id === draft.cluster_id)
                    ?.evidence_references ?? []
                }
                busy={busy}
                act={act}
              />
            ))}
          </section>
        </>
      )}
    </main>
  );
}
