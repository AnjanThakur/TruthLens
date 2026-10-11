'use client';
import { useState } from 'react';
import Link from 'next/link';
import type { Verification } from '@/lib/api/contracts';
import { request, jsonRequest } from '@/lib/api/client';
import { contributionResponseSchema } from '@/lib/alerts/contracts';
import { uiError } from '@/lib/i18n/errors';
import { usePreferences } from './preferences';

export function AlertContribution({ result, receipt }: { result: Verification; receipt: string }) {
  const { language } = usePreferences();
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [status, setStatus] = useState('');
  const wording =
    language === 'hi'
      ? {
          title: 'सहमति से चेतावनी समीक्षा',
          consent:
            'इस जाँच के संपादित दावे और प्रमाण को आवर्ती संदिग्ध कथनों की समीक्षा के लिए साझा करने की सहमति है।',
          submit: 'समीक्षा के लिए भेजें',
          accepted: 'प्राप्त हुआ। सार्वजनिक चेतावनी के लिए मानव समीक्षा आवश्यक है।',
          help: 'आपका मूल संदेश प्रकाशित नहीं होगा। यह इतिहास में रखने की सहमति से अलग है।',
        }
      : language === 'mr'
        ? {
            title: 'संमतीने सूचना पुनरावलोकन',
            consent:
              'या तपासणीतील संपादित दावे आणि पुरावे वारंवार येणाऱ्या संशयास्पद कथनांच्या पुनरावलोकनासाठी देण्यास संमती आहे.',
            submit: 'पुनरावलोकनासाठी द्या',
            accepted: 'प्राप्त झाले. सार्वजनिक सूचनेसाठी मानवी पुनरावलोकन आवश्यक आहे.',
            help: 'मूळ संदेश प्रकाशित होणार नाही. ही संमती इतिहासात जतन करण्यापासून वेगळी आहे.',
          }
        : {
            title: 'Contribute to alert review',
            consent:
              'I consent to sharing this check’s redacted claims and evidence for review of recurring suspicious narratives.',
            submit: 'Contribute for review',
            accepted: 'Received. A public alert requires separate human evidence review.',
            help: 'Your original message is not published. This consent is separate from saving history.',
          };
  async function contribute() {
    if (!consent || busy || accepted) return;
    setBusy(true);
    try {
      const response = await request(
        '/api/alerts/contribute',
        contributionResponseSchema,
        jsonRequest({ consent: true, report: result, receipt }),
      );
      setAccepted(true);
      setStatus(
        response.deferred
          ? language === 'en'
            ? 'Received; evidence or recurrence requirements are not yet met. No alert was published.'
            : wording.accepted
          : wording.accepted,
      );
    } catch (error) {
      setStatus(uiError(error, language));
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="alert-consent">
      <h3>{wording.title}</h3>
      <p>{wording.help}</p>
      <label>
        <input
          type="checkbox"
          checked={consent}
          disabled={busy || accepted}
          onChange={(event) => setConsent(event.target.checked)}
        />{' '}
        {wording.consent}
      </label>
      <div className="results-actions">
        <button
          className="button secondary"
          disabled={
            !consent ||
            busy ||
            accepted ||
            result.status !== 'completed' ||
            result.warnings.length > 0
          }
          onClick={() => void contribute()}
        >
          {wording.submit}
        </button>
        <Link href="/alerts">
          {language === 'en' ? 'Withdraw contributions / reviewer dashboard' : 'पुनरावलोकन'}
        </Link>
      </div>
      {status && <p role="status">{status}</p>}
    </aside>
  );
}
