import fixtureData from './synthetic.json';
// Convert ONLY the supplied legacy fictional examples. Live responses never pass here.
function fixtureResult(raw: (typeof fixtureData.fixtures)[number]['verification_response']) {
  return {
    ...raw,
    response_language: 'en',
    audience: 'adult',
    input: { ...raw.input, warnings: [], extraction_details: {} },
    claims: raw.claims.map((c) => ({
      ...c,
      original_span: c.claim_text,
      entities: [],
      dates: [],
      qualifiers: [],
      normalized_claim: c.claim_text,
      lexical_hash: 'synthetic',
      grounded_explanation: c.explanation,
      key_points: [],
      checked_at: raw.checked_at,
      risk: {
        score: 0,
        level: 'low',
        factors: [],
        is_probability: false,
        label: 'Synthetic example; no risk assessment.',
      },
      temporal_context: {
        claim_date: null,
        relevant_source_dates: [],
        notes: c.temporal_context ?? '',
      },
      original_context: { status: 'not_checked', notes: c.original_context ?? '', source_urls: [] },
      evidence: c.evidence.map((e, i) => ({
        ...e,
        evidence_id: `synthetic-${c.claim_id}-${i}`,
        updated_at: null,
        excerpt_provenance: 'search_excerpt',
        authority_basis: 'FICTIONAL',
        relevance_score: 0,
        directly_relevant: false,
      })),
    })),
  };
}
import {
  extractionSchema,
  verificationSchema,
  type InputType,
  type Verification,
} from '@/lib/api/contracts';
export const fixtures = fixtureData.fixtures.map((f) => ({
  id: f.fixture_id,
  description: f.description,
  extraction: f.extract_response
    ? extractionSchema.parse({
        ...f.extract_response,
        extraction_details: f.extract_response.metadata ?? {},
      })
    : null,
  verification: verificationSchema.parse(fixtureResult(f.verification_response)),
}));
export function fixtureForType(type: InputType) {
  return fixtures.find((f) => f.verification.input.input_type === type) ?? fixtures[0];
}
export function isSynthetic(result: Verification) {
  return (
    result.verification_id.startsWith('mock-') ||
    result.warnings.some((w) => /synthetic|fixture|mock/i.test(w)) ||
    result.claims.some((c) => c.evidence.some((e) => e.source_type === 'synthetic_fixture'))
  );
}
