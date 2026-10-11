'use client';
import { useEffect, useId, useRef, useState, useSyncExternalStore } from 'react';
import {
  AlertCircle,
  ArrowUpRight,
  Check,
  CheckCircle2,
  Clock3,
  Copy,
  HelpCircle,
  Info,
  Layers,
  Volume2,
  XCircle,
  Square,
} from 'lucide-react';
import type { Verification, Explanation } from '@/lib/api/contracts';
import { locale, stanceLabels, verdictLabels } from '@/lib/i18n';
import { isSynthetic } from '@/lib/fixtures';
import { usePreferences } from './preferences';
const verdictIcons = {
  verified: CheckCircle2,
  false: XCircle,
  partially_true: Layers,
  outdated: Clock3,
  misleading_context: Info,
  unconfirmed: HelpCircle,
};
const subscribe = () => () => {};
export function Results({
  result,
  explanation,
  headingRef,
  children,
}: {
  result: Verification;
  explanation?: Explanation | null;
  headingRef?: React.RefObject<HTMLHeadingElement | null>;
  children?: React.ReactNode;
}) {
  const { language, t } = usePreferences();
  const prefix = useId().replaceAll(':', '');
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const supportsSpeech = useSyncExternalStore(
    subscribe,
    () => 'speechSynthesis' in window,
    () => false,
  );
  const utterance = useRef<SpeechSynthesisUtterance | null>(null);
  useEffect(
    () => () => {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    },
    [],
  );
  const synthetic = isSynthetic(result);
  const formatDate = (value: string | null) =>
    value
      ? new Intl.DateTimeFormat(locale[language], {
          dateStyle: 'medium',
          timeZone: 'Asia/Kolkata',
        }).format(new Date(value))
      : t.noDate;
  const displayedSummary = explanation?.summary ?? result.summary;
  const summary = [
    synthetic ? t.mock : '',
    displayedSummary,
    `${t.checked}: ${result.checked_at}`,
    ...result.claims.flatMap((claim) => [
      `${t.claim}: ${claim.claim_text}`,
      verdictLabels[language][claim.verdict],
      explanation?.claims.find((c) => c.claim_id === claim.claim_id)?.explanation ??
        claim.explanation,
      ...claim.evidence.map(
        (e) =>
          `${e.publisher} — ${e.title}\n${stanceLabels[language][e.stance]}: ${e.what_source_says}\n${t.published}: ${formatDate(e.published_at)}; ${t.retrieved}: ${formatDate(e.retrieved_at)}\n${e.url}`,
      ),
      ...claim.limitations,
      claim.next_step,
    ]),
  ]
    .filter(Boolean)
    .join('\n\n');
  async function copy() {
    try {
      await navigator.clipboard.writeText(summary);
      setCopied(true);
      setCopyError(false);
    } catch {
      setCopyError(true);
    }
  }
  function speak() {
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const voice = new SpeechSynthesisUtterance(summary);
    voice.lang = locale[language];
    voice.onend = () => setSpeaking(false);
    voice.onerror = () => setSpeaking(false);
    utterance.current = voice;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(voice);
    setSpeaking(true);
  }
  return (
    <section className="results" aria-labelledby={`${prefix}-results-heading`}>
      <div className="section-kicker">03 / {t.step3}</div>
      <div className="results-title-row">
        <h2 id={`${prefix}-results-heading`} tabIndex={-1} ref={headingRef}>
          {t.results}
        </h2>
        <span className="count-pill">
          {result.claims.length} {t.claims}
        </span>
      </div>
      {synthetic && (
        <p className="notice mock-result">
          <Info size={18} aria-hidden="true" />
          {t.mock}
        </p>
      )}
      <p className="result-summary">{displayedSummary}</p>
      {result.status === 'partial' && (
        <p className="notice" role="status">
          {language === 'hi'
            ? 'आंशिक जाँच: कुछ प्रमाण या प्रसंस्करण अधूरा है। चेतावनियाँ देखें।'
            : language === 'mr'
              ? 'अंशतः तपासणी: काही पुरावे किंवा प्रक्रिया अपूर्ण आहे. सूचना वाचा.'
              : 'Partial check: some evidence or processing was incomplete. Review the warnings and limitations.'}
        </p>
      )}
      <p className="meta-line">
        {t.checked}{' '}
        <time dateTime={result.checked_at}>
          {new Intl.DateTimeFormat(locale[language], {
            dateStyle: 'medium',
            timeStyle: 'short',
            timeZone: 'Asia/Kolkata',
          }).format(new Date(result.checked_at))}{' '}
          IST
        </time>
      </p>
      {result.claims.some((c) => c.verdict === 'unconfirmed') && (
        <p className="notice">
          <AlertCircle size={18} aria-hidden="true" />
          {t.unconfirmedNotice}
        </p>
      )}
      {result.warnings.length > 0 && (
        <details className="service-notes">
          <summary>
            {t.warnings} ({result.warnings.length})
          </summary>
          <ul>
            {result.warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </details>
      )}
      {children}
      <div className="results-actions">
        <button className="button secondary" onClick={copy}>
          {copied ? <Check size={17} /> : <Copy size={17} />}
          {copied ? t.copied : t.copy}
        </button>
        {supportsSpeech && (
          <button className="button secondary" onClick={speak}>
            {speaking ? <Square size={17} /> : <Volume2 size={17} />}
            {speaking ? t.stop : t.listen}
          </button>
        )}
      </div>
      {copyError && <p role="alert">{t.clipboardError}</p>}
      {!result.claims.length && <p className="notice">{t.noClaims}</p>}
      {result.claims.length > 1 && (
        <nav className="claim-nav" aria-label={t.claims}>
          {result.claims.map((claim, i) => (
            <a href={`#${prefix}-claim-${i + 1}`} key={claim.claim_id}>
              {t.claim} {i + 1}
            </a>
          ))}
        </nav>
      )}
      <div className="claim-list">
        {result.claims.map((claim, index) => {
          const Icon = verdictIcons[claim.verdict];
          const rewritten = explanation?.claims.find((c) => c.claim_id === claim.claim_id);
          return (
            <article
              className={`claim-card verdict-${claim.verdict}`}
              id={`${prefix}-claim-${index + 1}`}
              key={claim.claim_id}
              aria-labelledby={`${prefix}-claim-heading-${index}`}
            >
              <div className="claim-top">
                <span className="claim-number">
                  {t.claim} {String(index + 1).padStart(2, '0')}
                </span>
                <span className={`verdict verdict-${claim.verdict}`}>
                  <Icon size={17} aria-hidden="true" />
                  {verdictLabels[language][claim.verdict]}
                </span>
              </div>
              <h3 id={`${prefix}-claim-heading-${index}`} dir="auto">
                {claim.claim_text}
              </h3>
              <p className="claim-summary" dir="auto">
                {rewritten?.short_summary ?? claim.short_summary}
              </p>
              <p dir="auto">{rewritten?.explanation ?? claim.explanation}</p>
              {claim.temporal_context.notes && (
                <p>
                  <strong>{t.temporal}: </strong>
                  {claim.temporal_context.notes}
                </p>
              )}
              {claim.original_context.notes && (
                <p>
                  <strong>{t.context}: </strong>
                  {claim.original_context.notes}
                </p>
              )}
              <div className="evidence-section">
                <h4>
                  {t.sources} <span>{claim.evidence.length}</span>
                </h4>
                {!claim.evidence.length && (
                  <p className="no-evidence">
                    <HelpCircle size={20} aria-hidden="true" />
                    {t.noEvidence}
                  </p>
                )}
                {claim.evidence.map((evidence, i) => (
                  <div className="evidence-record" key={`${evidence.url}-${i}`}>
                    <div className="evidence-top">
                      <span className="publisher">{evidence.publisher}</span>
                      <span className={`stance stance-${evidence.stance}`}>
                        {stanceLabels[language][evidence.stance]}
                      </span>
                    </div>
                    <h5>
                      <a href={evidence.url} target="_blank" rel="noopener noreferrer">
                        {evidence.title}
                        <ArrowUpRight size={16} aria-hidden="true" />
                        <span className="sr-only"> — {t.original}</span>
                      </a>
                    </h5>
                    <a
                      className="source-url"
                      href={evidence.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {evidence.url}
                    </a>
                    <p className="source-paraphrase">
                      <strong>{t.says}: </strong>
                      {evidence.what_source_says || '—'}
                    </p>
                    {evidence.excerpt && (
                      <details>
                        <summary>{t.excerpt}</summary>
                        <blockquote dir="auto">{evidence.excerpt}</blockquote>
                      </details>
                    )}
                    <dl className="source-dates">
                      <div>
                        <dt>{t.published}</dt>
                        <dd>
                          {evidence.published_at ? (
                            <time dateTime={evidence.published_at}>
                              {formatDate(evidence.published_at)}
                            </time>
                          ) : (
                            t.noDate
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>{t.retrieved}</dt>
                        <dd>
                          {evidence.retrieved_at ? (
                            <time dateTime={evidence.retrieved_at}>
                              {formatDate(evidence.retrieved_at)}
                            </time>
                          ) : (
                            t.noDate
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>{t.sourceType}</dt>
                        <dd>{evidence.source_type}</dd>
                      </div>
                    </dl>
                  </div>
                ))}
              </div>
              {claim.limitations.length > 0 && (
                <div className="claim-limits">
                  <h4>{t.limitations}</h4>
                  <ul>
                    {claim.limitations.map((limitation, i) => (
                      <li key={i}>{limitation}</li>
                    ))}
                  </ul>
                </div>
              )}
              {claim.next_step && (
                <div className="next-step">
                  <span>{t.next}</span>
                  <p>{rewritten?.next_step ?? claim.next_step}</p>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
