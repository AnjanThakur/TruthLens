'use client';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import {
  ArrowRight,
  FileText,
  Image as ImageIcon,
  Mic,
  Link as LinkIcon,
  UploadCloud,
  ShieldCheck,
  ListChecks,
  Search,
  LockKeyhole,
  LoaderCircle,
  AlertCircle,
  X,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { z } from 'zod';
import { usePreferences } from './preferences';
import { Results } from './results';
import { AlertContribution } from './alert-contribution';
import { fixtures } from '@/lib/fixtures';
import { extractFile, extractUrl, verify, explain, request, jsonRequest } from '@/lib/api/client';
import {
  healthSchema,
  inputTypes,
  publicUrlSchema,
  verifyRequestSchema,
  type Extraction,
  type Verification,
  type InputType,
  type Explanation,
} from '@/lib/api/contracts';
import { acceptedTypes, validateFile, MAX_UPLOAD_BYTES } from '@/lib/api/files';
import { extractionChunks } from '@/lib/api/chunks';
import { ApiError, errorMessage } from '@/lib/api/errors';
import { uiError } from '@/lib/i18n/errors';
type Phase = 'idle' | 'validating' | 'extracting' | 'review' | 'verifying' | 'results';
const icons = { text: FileText, image: ImageIcon, audio: Mic, pdf: FileText, url: LinkIcon };
const sampleNames = {
  en: [
    'Mixed claims',
    'Screenshot',
    'Hindi voice note',
    'PDF notice',
    'Article URL',
    'Insufficient evidence',
  ],
  hi: [
    'मिश्रित दावे',
    'स्क्रीनशॉट',
    'हिन्दी वॉइस नोट',
    'पीडीएफ सूचना',
    'लेख लिंक',
    'अपर्याप्त प्रमाण',
  ],
  mr: [
    'वेगवेगळे दावे',
    'स्क्रीनशॉट',
    'हिंदी व्हॉइस नोट',
    'पीडीएफ सूचना',
    'लेख लिंक',
    'अपुरे पुरावे',
  ],
};
function Preview({ file, kind }: { file: File; kind: InputType }) {
  const { t } = usePreferences();
  const [url, setUrl] = useState('');
  useEffect(() => {
    const objectUrl = URL.createObjectURL(file);
    // Object URLs are browser-managed resources and require effect lifecycle cleanup.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  return (
    <div className="file-preview">
      <FileText size={24} aria-hidden="true" />
      <div>
        <strong>{file.name}</strong>
        <span>{(file.size / 1024).toFixed(1)} KB</span>
      </div>
      {/* Blob previews are transient uploads, not remote optimized images. */}
      {kind === 'image' && url && <img className="image-preview" src={url} alt={t.image} />}
      {kind === 'audio' && url && (
        <>
          <p id="audio-help">{t.audioHelp}</p>
          {/* User-uploaded audio has no caption track; extraction review provides the transcript. */}
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <audio
            controls
            src={url}
            aria-label={t.audio}
            aria-describedby="audio-help"
            preload="metadata"
          />
        </>
      )}
    </div>
  );
}
export function VerificationWorkspace({
  mock,
  historyEnabled,
  alertsEnabled = false,
  whatsappUrl,
  maxUploadBytes = MAX_UPLOAD_BYTES,
}: {
  mock: boolean;
  historyEnabled: boolean;
  alertsEnabled?: boolean;
  whatsappUrl?: string | null;
  maxUploadBytes?: number;
}) {
  const { language, easy, t } = usePreferences();
  const metadataLabels: Record<string, string> = {
    filename: t.fileName,
    title: t.title,
    page_count: t.pages,
    pages: t.pages,
    duration_seconds: t.duration,
    published_at: t.published,
  };
  const [type, setType] = useState<InputType>('text');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [reviewText, setReviewText] = useState('');
  const [result, setResult] = useState<Verification | null>(null);
  const [receipt, setReceipt] = useState<string | null>(null);
  const [messageTime, setMessageTime] = useState('');
  const [error, setError] = useState('');
  const [selectedFixture, setSelectedFixture] = useState(0);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [explainBusy, setExplainBusy] = useState(false);
  const [explainError, setExplainError] = useState('');
  const [consent, setConsent] = useState(false);
  const [retention, setRetention] = useState(30);
  const [saveStatus, setSaveStatus] = useState('');
  const [saveBusy, setSaveBusy] = useState(false);
  const [health, setHealth] = useState<'checking' | 'live' | 'offline'>(mock ? 'live' : 'checking');
  const controller = useRef<AbortController | null>(null);
  const explanationController = useRef<AbortController | null>(null);
  const pending = useRef(false);
  const resultsHeading = useRef<HTMLHeadingElement>(null);
  const reviewHeading = useRef<HTMLHeadingElement>(null);
  const busy = ['validating', 'extracting', 'verifying'].includes(phase);
  useEffect(() => {
    const abort = new AbortController();
    if (!mock)
      request('/api/health', healthSchema, { signal: abort.signal })
        .then((h) =>
          setHealth(
            h.capabilities?.claim_verification === false || h.capabilities?.verify === false
              ? 'offline'
              : 'live',
          ),
        )
        .catch(() => {
          if (!abort.signal.aborted) setHealth('offline');
        });
    return () => {
      abort.abort();
      controller.current?.abort();
      explanationController.current?.abort();
    };
  }, [mock]);
  useEffect(() => {
    if (phase === 'results') resultsHeading.current?.focus();
    if (phase === 'review') reviewHeading.current?.focus();
  }, [phase]);
  function clearResult() {
    setResult(null);
    setReceipt(null);
    setExplanation(null);
    setExplainError('');
    setSaveStatus('');
    setConsent(false);
    explanationController.current?.abort();
    setExplainBusy(false);
  }
  function changeType(next: InputType) {
    if (busy) return;
    setType(next);
    setMessageTime('');
    setFile(null);
    setExtraction(null);
    setReviewText('');
    setPhase('idle');
    setError('');
    clearResult();
  }
  function reset() {
    controller.current?.abort();
    pending.current = false;
    setPhase('idle');
    setText('');
    setUrl('');
    setFile(null);
    setExtraction(null);
    setReviewText('');
    setError('');
    clearResult();
  }
  function cancel() {
    controller.current?.abort();
    pending.current = false;
    setPhase(extraction ? 'review' : 'idle');
  }
  function selectFile(next?: File) {
    if (!next || busy) return;
    try {
      validateFile(next, type, maxUploadBytes);
      setFile(next);
      setError('');
      setExtraction(null);
      setPhase('idle');
      clearResult();
    } catch (failure) {
      setError(uiError(failure, language));
    }
  }
  function useSample() {
    const sample = fixtures[selectedFixture];
    changeType(sample.verification.input.input_type);
    setText(sample.verification.input.text);
    if (sample.verification.input.input_type === 'url')
      setUrl(
        String(sample.extraction?.extraction_details?.url ?? 'https://example.org/mock-article'),
      );
    if (sample.extraction) {
      setExtraction(sample.extraction);
      setReviewText(sample.extraction.text);
      setPhase('review');
    }
  }
  async function submit() {
    if (pending.current) return;
    pending.current = true;
    const abort = new AbortController();
    controller.current?.abort();
    controller.current = abort;
    setError('');
    setPhase('validating');
    clearResult();
    try {
      if (type !== 'text' && !extraction) {
        if (type === 'url') publicUrlSchema.parse(url);
        else {
          if (!file) throw new ApiError('BAD_INPUT', 'Choose a file first.');
          validateFile(file, type, maxUploadBytes);
        }
        setPhase('extracting');
        const extracted =
          type === 'url'
            ? await extractUrl(url, abort.signal)
            : await extractFile(file!, abort.signal);
        if (abort.signal.aborted) return;
        if (extracted.text.trim().length < 10)
          throw new ApiError('EXTRACTION_EMPTY', errorMessage('EXTRACTION_EMPTY'));
        setExtraction(extracted);
        setReviewText(extracted.extraction_details.text_is_preview === true ? '' : extracted.text);
        setPhase('review');
      } else {
        const input = verifyRequestSchema.parse({
          text: type === 'text' ? text : reviewText,
          input_type: type,
          input_language: 'auto',
          response_language: language,
          audience: easy ? 'senior' : 'adult',
          jurisdiction: 'IN',
        });
        setPhase('verifying');
        const verified = await verify(
          input,
          abort.signal,
          messageTime ? new Date(messageTime).toISOString() : undefined,
        );
        if (abort.signal.aborted) return;
        setResult(verified.result);
        setReceipt(verified.receipt);
        setPhase('results');
      }
    } catch (failure) {
      if (abort.signal.aborted) return;
      setError(
        failure instanceof z.ZodError
          ? language === 'en'
            ? failure.issues[0]?.message || errorMessage('BAD_INPUT')
            : uiError(new ApiError('BAD_INPUT', ''), language)
          : uiError(failure, language),
      );
      setPhase(extraction ? 'review' : 'idle');
    } finally {
      if (controller.current === abort) pending.current = false;
    }
  }
  async function updateExplanation() {
    if (!result || explainBusy) return;
    const abort = new AbortController();
    explanationController.current = abort;
    setExplainBusy(true);
    setExplainError('');
    try {
      const value = await explain(result, language, easy ? 'easy' : 'standard', abort.signal);
      if (!abort.signal.aborted) setExplanation(value);
    } catch {
      if (!abort.signal.aborted) setExplainError(t.unavailableExplain);
    } finally {
      if (!abort.signal.aborted) setExplainBusy(false);
    }
  }
  async function save() {
    if (!result || !receipt || !consent || saveBusy) return;
    setSaveBusy(true);
    setSaveStatus('');
    try {
      await request(
        '/api/history',
        z.object({ saved: z.boolean() }),
        jsonRequest({ report: result, receipt, consent_to_store: true, retention_days: retention }),
      );
      setSaveStatus(t.saved);
    } catch (failure) {
      setSaveStatus(
        failure instanceof ApiError && failure.code === 'UNAUTHENTICATED'
          ? t.signInSave
          : uiError(failure, language),
      );
    } finally {
      setSaveBusy(false);
    }
  }
  const currentExplanation =
    explanation?.response_language === language &&
    explanation.audience === (easy ? 'senior' : 'adult')
      ? explanation
      : null;
  return (
    <main id="main" className="workspace">
      <section className="hero">
        <div className="eyebrow">
          <span className="eyebrow-line" />
          {t.eyebrow}
        </div>
        <h1>
          {t.headline}
          <br />
          <span>{t.headlineAccent}</span>
        </h1>
        <p>{t.intro}</p>
        {whatsappUrl && (
          <p>
            <a
              className="button secondary"
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              {language === 'hi'
                ? 'WhatsApp पर जाँचें'
                : language === 'mr'
                  ? 'WhatsApp वर तपासा'
                  : 'Check on WhatsApp'}
            </a>
          </p>
        )}
        <div className="hero-detail">
          <ShieldCheck size={17} aria-hidden="true" />
          <span>
            {t.trust2} · {t.trust3}
          </span>
        </div>
      </section>
      <div className="work-grid">
        <div className="main-column">
          {mock && (
            <aside className="demo-banner" aria-label={t.mock}>
              <Info size={20} aria-hidden="true" />
              <div>
                <strong>{t.mock}</strong>
                <p>{t.mockHelp}</p>
              </div>
            </aside>
          )}
          <section className="input-panel" aria-labelledby="input-heading">
            <div className="panel-heading">
              <div>
                <div className="section-kicker">01 / {t.step1}</div>
                <h2 id="input-heading">{t.verify}</h2>
              </div>
              <span className={`service-status ${mock ? 'mock' : health}`}>
                <span />
                {mock
                  ? t.serviceMock
                  : health === 'live'
                    ? t.serviceLive
                    : health === 'checking'
                      ? t.connecting
                      : t.serviceOffline}
              </span>
            </div>
            <div className="input-tabs" role="group" aria-label={t.step1}>
              {inputTypes.map((kind) => {
                const Icon = icons[kind];
                return (
                  <button
                    type="button"
                    key={kind}
                    aria-pressed={type === kind}
                    disabled={busy}
                    onClick={() => changeType(kind)}
                  >
                    <Icon size={18} aria-hidden="true" />
                    <span>{t[kind]}</span>
                  </button>
                );
              })}
            </div>
            {mock && (
              <div className="sample-picker">
                <label htmlFor="fixture">{t.sample}</label>
                <div>
                  <select
                    id="fixture"
                    value={selectedFixture}
                    disabled={busy}
                    onChange={(e) => setSelectedFixture(Number(e.target.value))}
                  >
                    {fixtures.map((f, i) => (
                      <option value={i} key={f.id}>
                        {sampleNames[language][i]}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="button secondary"
                    onClick={useSample}
                    disabled={busy}
                  >
                    {t.sampleButton}
                  </button>
                </div>
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void submit();
              }}
            >
              <div className="input-body">
                {type === 'text' && (
                  <>
                    <label htmlFor="forward">{t.inputLabel}</label>
                    <textarea
                      id="forward"
                      value={text}
                      disabled={busy}
                      onChange={(e) => {
                        setText(e.target.value);
                        if (result) {
                          clearResult();
                          setPhase('idle');
                        }
                      }}
                      placeholder={t.placeholder}
                      maxLength={24000}
                      rows={7}
                      required
                      aria-describedby="privacy-note text-count"
                    />
                    <span className="character-count" id="text-count">
                      {text.length.toLocaleString()} / 24,000
                    </span>
                    <label htmlFor="message-time">
                      {language === 'hi'
                        ? 'मूल संदेश का समय (वैकल्पिक)'
                        : language === 'mr'
                          ? 'मूळ संदेशाची वेळ (पर्यायी)'
                          : 'Original message time (optional, your local timezone)'}
                    </label>
                    <input
                      id="message-time"
                      type="datetime-local"
                      value={messageTime}
                      disabled={busy}
                      onChange={(event) => {
                        setMessageTime(event.target.value);
                        clearResult();
                      }}
                    />
                    <p className="meta-line">
                      {language === 'en'
                        ? 'Helps interpret “tomorrow” or “next Monday”. If unknown, relative dates use the time of this check.'
                        : language === 'hi'
                          ? '“अगले सोमवार” का अर्थ स्पष्ट करता है। समय न मिलने पर जाँच के समय का उपयोग होता है।'
                          : '“पुढील सोमवार”चा अर्थ स्पष्ट होतो. मूळ वेळ माहीत नसल्यास तपासणीची वेळ वापरली जाते.'}
                    </p>
                  </>
                )}
                {type === 'url' && (
                  <>
                    <label htmlFor="article-url">{t.urlLabel}</label>
                    <input
                      id="article-url"
                      type="url"
                      value={url}
                      placeholder={t.urlPlaceholder}
                      disabled={busy}
                      onChange={(e) => {
                        setUrl(e.target.value);
                        setExtraction(null);
                        clearResult();
                        setPhase('idle');
                      }}
                      required
                      aria-describedby="privacy-note"
                    />
                  </>
                )}
                {type !== 'text' && type !== 'url' && (
                  <>
                    <label
                      className="dropzone"
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={(e) => {
                        e.preventDefault();
                        selectFile(e.dataTransfer.files[0]);
                      }}
                    >
                      <UploadCloud size={32} aria-hidden="true" />
                      <strong>{t.dropFile}</strong>
                      <span>
                        {t.formats.replace(
                          '10',
                          (maxUploadBytes / 1048576).toLocaleString(language, {
                            maximumFractionDigits: 3,
                          }),
                        )}
                      </span>
                      <span className="file-formats">
                        {type === 'image'
                          ? 'JPEG · PNG · WebP'
                          : type === 'audio'
                            ? 'MP3 · M4A · OGG · WAV · WebM · AAC'
                            : 'PDF'}
                      </span>
                      <input
                        aria-label={t.chooseFile}
                        type="file"
                        disabled={busy}
                        accept={acceptedTypes[type].join(',')}
                        onChange={(e) => selectFile(e.target.files?.[0])}
                      />
                    </label>
                    {file && <Preview file={file} kind={type} />}
                  </>
                )}
              </div>
              {extraction && type !== 'text' && (
                <section className="extraction-review" aria-labelledby="review-heading">
                  <div className="section-kicker">02 / {t.step2}</div>
                  <h3 id="review-heading" ref={reviewHeading} tabIndex={-1}>
                    {t.reviewTitle}
                  </h3>
                  <p>{t.reviewHelp}</p>
                  {extraction.extraction_details.text_is_preview === true && (
                    <div className="notice chunk-review">
                      <p>
                        {language === 'hi'
                          ? 'यह केवल पूर्वावलोकन है। जाँचने के लिए पृष्ठ का एक भाग चुनें। परिणाम केवल चुने हुए भाग के लिए है।'
                          : language === 'mr'
                            ? 'हा फक्त पूर्वावलोकन आहे. तपासणीसाठी पानाचा एक भाग निवडा. निकाल फक्त निवडलेल्या भागासाठी आहे.'
                            : 'This is a document preview. Select a page chunk to check. Each result covers only the selected text, not the whole PDF.'}
                      </p>
                      <label htmlFor="page-chunk">{t.pages}</label>
                      <select
                        id="page-chunk"
                        defaultValue=""
                        disabled={busy}
                        onChange={(e) => {
                          const chunk = extractionChunks(extraction)[Number(e.target.value)];
                          if (chunk) {
                            setReviewText(chunk.text);
                            clearResult();
                            setPhase('review');
                          }
                        }}
                      >
                        <option value="" disabled>
                          —
                        </option>
                        {extractionChunks(extraction).map((chunk, i) => (
                          <option key={i} value={i}>
                            {t.pages} {chunk.page_number ?? '—'} · {i + 1}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                  <div className="extraction-meta">
                    <span>
                      {t.language}: {extraction.detected_language}
                    </span>
                    {extraction.extraction_details &&
                      Object.entries(extraction.extraction_details)
                        .filter(
                          ([key, value]) =>
                            [
                              'filename',
                              'title',
                              'page_count',
                              'pages',
                              'duration_seconds',
                              'published_at',
                            ].includes(key) &&
                            (['string', 'number'].includes(typeof value) || Array.isArray(value)),
                        )
                        .map(([key, value]) => (
                          <span key={key}>
                            {metadataLabels[key]}:{' '}
                            {Array.isArray(value) ? value.join(', ') : String(value)}
                          </span>
                        ))}
                  </div>
                  {extraction.warnings.length > 0 && (
                    <ul className="extraction-warnings">
                      {extraction.warnings.map((warning, i) => (
                        <li key={i}>{warning}</li>
                      ))}
                    </ul>
                  )}
                  <label htmlFor="review-text">{t.extractionLabel}</label>
                  <textarea
                    id="review-text"
                    value={reviewText}
                    onChange={(e) => {
                      setReviewText(e.target.value);
                      clearResult();
                      setPhase('review');
                    }}
                    disabled={busy}
                    maxLength={24000}
                    rows={6}
                  />
                  {reviewText !== extraction.text && <p className="edited-notice">{t.edited}</p>}
                </section>
              )}
              {error && (
                <div className="error-message" role="alert">
                  <AlertCircle size={20} aria-hidden="true" />
                  <div>{error}</div>
                  <button type="button" aria-label={t.dismissError} onClick={() => setError('')}>
                    <X size={16} />
                  </button>
                </div>
              )}
              <div className="submit-row">
                <button className="button primary" disabled={busy} type="submit">
                  {busy ? (
                    <LoaderCircle size={19} className="spinner" aria-hidden="true" />
                  ) : (
                    <Search size={19} aria-hidden="true" />
                  )}
                  {busy
                    ? phase === 'extracting'
                      ? t.extracting
                      : phase === 'validating'
                        ? t.validating
                        : t.verifying
                    : type === 'text' || extraction
                      ? t.check
                      : t.extract}
                  {!busy && <ArrowRight size={18} aria-hidden="true" />}
                </button>
                {busy ? (
                  <button type="button" className="button quiet" onClick={cancel}>
                    {t.cancel}
                  </button>
                ) : (
                  (result || extraction || file || text || url) && (
                    <button type="button" className="button quiet" onClick={reset}>
                      {t.reset}
                    </button>
                  )
                )}
              </div>
              <p id="privacy-note" className="privacy-note">
                <LockKeyhole size={14} aria-hidden="true" />
                {t.privacyNote} <Link href="/privacy">{t.privacy}</Link>
              </p>
            </form>
            <div className="sr-only" role="status" aria-live="polite">
              {busy
                ? phase === 'extracting'
                  ? t.extracting
                  : phase === 'verifying'
                    ? t.verifying
                    : t.validating
                : phase === 'results'
                  ? t.results
                  : phase === 'review'
                    ? t.reviewTitle
                    : ''}
            </div>
          </section>
          {result && (
            <Results result={result} explanation={currentExplanation} headingRef={resultsHeading}>
              <div className="explanation-tools">
                <div>
                  <strong>{t.explain}</strong>
                  <p>{t.originalLanguage}</p>
                </div>
                <button
                  className="button secondary"
                  disabled={explainBusy}
                  onClick={updateExplanation}
                >
                  {explainBusy ? t.explaining : t.explain}
                </button>
              </div>
              {explainError && (
                <p className="notice" role="status">
                  {explainError}
                </p>
              )}
            </Results>
          )}
          {result && (
            <section className="save-panel">
              <div>
                <LockKeyhole size={21} aria-hidden="true" />
                <h2>{t.save}</h2>
              </div>
              {mock ? (
                <p>{uiError(new ApiError('MOCK_STORAGE', ''), language)}</p>
              ) : !historyEnabled || !receipt ? (
                <p>{t.historyDisabled}</p>
              ) : (
                <>
                  <p>{t.notSaved}</p>
                  <label className="consent-check">
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(e) => setConsent(e.target.checked)}
                    />
                    {t.consent}
                  </label>
                  <div className="save-controls">
                    <label htmlFor="retention">{t.retention}</label>
                    <select
                      id="retention"
                      value={retention}
                      onChange={(e) => setRetention(Number(e.target.value))}
                    >
                      {[7, 30, 90].map((days) => (
                        <option key={days} value={days}>
                          {days} {t.days}
                        </option>
                      ))}
                    </select>
                    <button
                      className="button primary"
                      disabled={!consent || saveBusy || saveStatus === t.saved}
                      onClick={save}
                    >
                      {saveBusy ? (
                        <LoaderCircle className="spinner" size={17} />
                      ) : (
                        <CheckCircle2 size={17} />
                      )}
                      {t.save}
                    </button>
                  </div>
                  <Link href="/history" target="_blank" rel="noopener noreferrer">
                    {t.history}
                  </Link>
                </>
              )}
              {saveStatus && <p role="status">{saveStatus}</p>}
              {alertsEnabled && receipt && !mock && (
                <AlertContribution key={result.verification_id} result={result} receipt={receipt} />
              )}
            </section>
          )}
        </div>
        <aside className="guide">
          <div className="guide-label">{t.approach}</div>
          <h2>{t.guideTitle}</h2>
          <p>{t.guideIntro}</p>
          <ol>
            {[
              { icon: ListChecks, title: t.trust1, text: t.trust1Text },
              { icon: LinkIcon, title: t.trust2, text: t.trust2Text },
              { icon: ShieldCheck, title: t.trust3, text: t.trust3Text },
            ].map(({ icon: Icon, title, text }, i) => (
              <li key={i}>
                <span className="guide-icon">
                  <Icon size={20} aria-hidden="true" />
                </span>
                <div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              </li>
            ))}
          </ol>
          <div className="guide-note">
            <span className="guide-note-line" />
            <p>{t.guideNote}</p>
          </div>
        </aside>
      </div>
      <section className="how-it-works" aria-label={t.how}>
        <span>{t.how}</span>
        <ol>
          <li>
            <b>01</b>
            {t.step1}
          </li>
          <li>
            <b>02</b>
            {t.step2}
          </li>
          <li>
            <b>03</b>
            {t.step3}
          </li>
        </ol>
      </section>
    </main>
  );
}
