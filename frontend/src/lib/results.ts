import type { Verification } from '@/lib/api/contracts';
export function relevantSources(claim: Verification['claims'][number]) {
  return claim.evidence
    .filter(
      (source) =>
        source.directly_relevant &&
        ['primary', 'secondary', 'fact_check'].includes(source.source_type) &&
        !source.authority_basis.includes('incomplete_content:') &&
        source.excerpt_provenance === 'fetched_page' &&
        ['supports', 'contradicts', 'context'].includes(source.stance),
    )
    .slice(0, 3);
}
export function warningText(warning: string, language: 'en' | 'hi' | 'mr') {
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
