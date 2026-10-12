import type { Verification } from '@/lib/api/contracts';
export function relevantSources(claim: Verification['claims'][number]) {
  return claim.evidence
    .filter(
      (source) =>
        source.directly_relevant &&
        ['primary', 'secondary', 'fact_check'].includes(source.source_type) &&
        !source.authority_basis.includes('incomplete_content:') &&
        !source.authority_basis.includes('entity_mismatch:') &&
        source.excerpt_provenance === 'fetched_page' &&
        ['supports', 'contradicts', 'context'].includes(source.stance),
    )
    .slice(0, 3);
}

type Evidence = Verification['claims'][number]['evidence'][number];
export function assessmentFailed(claim: Verification['claims'][number]) {
  return claim.limitations.some((note) => note.startsWith('Evidence assessment failed;'));
}
export function assessmentFailureText(language: 'en' | 'hi' | 'mr') {
  return {
    en: 'Evidence was retrieved, but AI assessment failed. No definitive verdict was accepted.',
    hi: 'प्रमाण मिले, लेकिन AI मूल्यांकन विफल हुआ। निर्णायक निष्कर्ष स्वीकार नहीं हुआ।',
    mr: 'पुरावे मिळाले, पण AI मूल्यांकन अयशस्वी झाले. निर्णायक निष्कर्ष स्वीकारला नाही.',
  }[language];
}
export function evidenceState(source: Evidence) {
  if (source.authority_basis.includes('source_fetch_failure=')) return 'failed';
  if (source.excerpt_provenance !== 'fetched_page') return 'snippet';
  if (!source.excerpt.trim()) return 'incomplete';
  if (source.authority_basis.includes('incomplete_content:')) return 'incomplete';
  if (
    source.authority_basis.includes('entity_mismatch:') ||
    (source.what_source_says && !source.directly_relevant)
  )
    return 'irrelevant';
  if (source.source_type === 'other') return 'unreviewed';
  return source.what_source_says ? 'assessed' : 'unassessed';
}
export function evidenceStateText(source: Evidence, language: 'en' | 'hi' | 'mr', failed = false) {
  if (failed && evidenceState(source) === 'unassessed') return assessmentFailureText(language);
  const labels = {
    en: {
      failed: 'Page retrieval failed; snippet is not proof.',
      snippet: 'Snippet only; not decisive evidence.',
      incomplete: 'Incomplete page; not decisive evidence.',
      irrelevant: 'Not relevant to the exact named subject or claim.',
      unreviewed: 'Fetched page; publisher quality is unreviewed.',
      assessed: 'Complete reviewed page; excerpt assessed.',
      unassessed: 'Complete reviewed page; awaiting evidence assessment.',
    },
    hi: {
      failed: 'पृष्ठ प्राप्त नहीं हुआ; खोज का अंश प्रमाण नहीं है।',
      snippet: 'केवल खोज का अंश; निर्णायक प्रमाण नहीं।',
      incomplete: 'अधूरा पृष्ठ; निर्णायक प्रमाण नहीं।',
      irrelevant: 'सटीक व्यक्ति या दावे से संबंधित नहीं।',
      unreviewed: 'पृष्ठ प्राप्त हुआ; प्रकाशक की गुणवत्ता की समीक्षा नहीं हुई।',
      assessed: 'पूरा समीक्षित पृष्ठ; अंश का मूल्यांकन हुआ।',
      unassessed: 'पूरा समीक्षित पृष्ठ; प्रमाण के मूल्यांकन की प्रतीक्षा है।',
    },
    mr: {
      failed: 'पृष्ठ मिळाले नाही; शोधातील उतारा पुरावा नाही.',
      snippet: 'फक्त शोधातील उतारा; निर्णायक पुरावा नाही.',
      incomplete: 'अपूर्ण पृष्ठ; निर्णायक पुरावा नाही.',
      irrelevant: 'नेमक्या व्यक्तीशी किंवा दाव्याशी संबंधित नाही.',
      unreviewed: 'पृष्ठ मिळाले; प्रकाशकाच्या गुणवत्तेचे पुनरावलोकन झाले नाही.',
      assessed: 'पूर्ण पुनरावलोकित पृष्ठ; उताऱ्याचे मूल्यांकन झाले.',
      unassessed: 'पूर्ण पुनरावलोकित पृष्ठ; पुराव्याचे मूल्यांकन बाकी आहे.',
    },
  };
  return labels[language][evidenceState(source)];
}
export function retrievalDiagnostic(source: Evidence, language: 'en' | 'hi' | 'mr') {
  const category = /(?:^|; )source_fetch_category=([a-z_]+)/.exec(source.authority_basis)?.[1];
  const status = /(?:^|; )source_fetch_http_status=(\d{3})(?:;|$)/.exec(
    source.authority_basis,
  )?.[1];
  const reasons: Record<string, [string, string, string]> = {
    dns_failure: [
      'Source address could not be resolved',
      'स्रोत का पता नहीं मिला',
      'स्रोताचा पत्ता सापडला नाही',
    ],
    access_denied: [
      'Publisher denied access',
      'प्रकाशक ने पहुँच रोकी',
      'प्रकाशकाने प्रवेश नाकारला',
    ],
    not_found: ['Page not found', 'पृष्ठ नहीं मिला', 'पृष्ठ सापडले नाही'],
    rate_limited: ['Publisher rate limit', 'प्रकाशक की दर सीमा', 'प्रकाशकाची विनंती मर्यादा'],
    transient_server: [
      'Publisher server unavailable',
      'प्रकाशक का सर्वर अनुपलब्ध',
      'प्रकाशकाचा सर्व्हर उपलब्ध नाही',
    ],
    javascript_required: ['JavaScript-only page', 'JavaScript आवश्यक', 'JavaScript आवश्यक'],
    access_shell: [
      'Access or browser-check page',
      'पहुँच या ब्राउज़र जाँच पृष्ठ',
      'प्रवेश किंवा ब्राउझर तपासणी पृष्ठ',
    ],
    empty_article: ['No readable article body', 'पढ़ने योग्य लेख नहीं', 'वाचण्यायोग्य लेख नाही'],
    connection_failed: [
      'Source connection failed',
      'स्रोत से संपर्क विफल',
      'स्रोताशी संपर्क अयशस्वी',
    ],
    timeout: ['Source timed out', 'स्रोत का समय समाप्त', 'स्रोताची वेळ संपली'],
    deadline: ['Source timed out', 'स्रोत का समय समाप्त', 'स्रोताची वेळ संपली'],
  };
  const reason = category ? reasons[category]?.[{ en: 0, hi: 1, mr: 2 }[language]] : undefined;
  return [reason, status ? `HTTP ${status}` : undefined].filter(Boolean).join(' · ');
}
export function displayWarnings(warnings: string[], language: 'en' | 'hi' | 'mr') {
  // Keep the report's original diagnostics, but present repeated notices once.
  return [...new Set(warnings.map((warning) => warningText(warning, language)))];
}
export function warningText(warning: string, language: 'en' | 'hi' | 'mr') {
  if (warning === 'llm_timeout')
    return {
      en: 'AI evidence assessment timed out. Retrieved sources remain available; no definitive verdict was accepted.',
      hi: 'AI प्रमाण मूल्यांकन का समय समाप्त हुआ। मिले स्रोत उपलब्ध हैं; निर्णायक निष्कर्ष स्वीकार नहीं हुआ।',
      mr: 'AI पुरावा मूल्यांकनाची वेळ संपली. मिळालेले स्रोत उपलब्ध आहेत; निर्णायक निष्कर्ष स्वीकारला नाही.',
    }[language];
  const kind =
    warning.startsWith('llm_') || warning.startsWith('explanation_fallback')
      ? 'model'
      : warning.startsWith('source_')
        ? 'source'
        : warning.startsWith('search_')
          ? 'search'
          : 'other';
  const text = {
    en: {
      model:
        'AI processing was unavailable or incomplete. No definitive verdict was accepted for an unassessed claim.',
      source:
        'A source page was unavailable or incomplete. Only retrieved content could be assessed.',
      search:
        'Part of the evidence investigation could not complete. Review the source ledger and try again later.',
      other:
        'Some input or evidence could not be fully processed. Review the extraction and claim limitations.',
    },
    hi: {
      model:
        'AI प्रक्रिया उपलब्ध नहीं थी या अधूरी थी। बिना मूल्यांकन के निर्णायक निष्कर्ष स्वीकार नहीं हुआ।',
      source: 'एक स्रोत पृष्ठ अनुपलब्ध या अधूरा था। केवल प्राप्त सामग्री की जाँच हो सकी।',
      search: 'प्रमाण की खोज पूरी नहीं हो सकी। स्रोत देखें और बाद में प्रयास करें।',
      other: 'कुछ सामग्री पूरी तरह जाँची नहीं जा सकी। निकाला गया पाठ और सीमाएँ देखें।',
    },
    mr: {
      model:
        'AI प्रक्रिया उपलब्ध नव्हती किंवा अपूर्ण होती. मूल्यांकनाशिवाय निर्णायक निष्कर्ष स्वीकारला नाही.',
      source: 'एक स्रोत पृष्ठ उपलब्ध नव्हते किंवा अपूर्ण होते. फक्त मिळालेली सामग्री तपासली.',
      search: 'पुरावे शोधण्याची प्रक्रिया पूर्ण झाली नाही. स्रोत पाहा आणि नंतर प्रयत्न करा.',
      other: 'काही सामग्री पूर्ण तपासता आली नाही. काढलेला मजकूर आणि मर्यादा पाहा.',
    },
  };
  return text[language][kind];
}
