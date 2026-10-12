import { z } from 'zod';
export const verdicts = [
  'verified',
  'false',
  'partially_true',
  'outdated',
  'misleading_context',
  'unconfirmed',
] as const;
export const stances = ['supports', 'contradicts', 'context', 'neutral', 'unclear'] as const;
export const inputTypes = ['text', 'image', 'audio', 'pdf', 'url'] as const;
export const languageSchema = z.enum(['en', 'hi', 'mr']);
export const audienceSchema = z.enum(['child', 'teen', 'adult', 'senior']);
export type Language = z.infer<typeof languageSchema>;
export type InputType = (typeof inputTypes)[number];
const text = z.string().min(1);
export const publicUrlSchema = z
  .string()
  .url()
  .refine((value) => {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password;
  }, 'Use a public HTTP or HTTPS link without credentials.');
const date = z.string().refine((value) => !Number.isNaN(Date.parse(value)), 'Invalid date');
export const extractionSchema = z.object({
  text: z.string(),
  detected_language: text,
  input_type: z.enum(inputTypes),
  warnings: z.array(z.string()),
  extraction_details: z.record(z.string(), z.unknown()),
});
export const evidenceSchema = z.object({
  evidence_id: text,
  title: text,
  url: publicUrlSchema,
  publisher: text,
  published_at: date.nullable(),
  updated_at: date.nullable(),
  retrieved_at: date,
  source_type: z.string(),
  stance: z.enum(stances),
  excerpt: z.string(),
  excerpt_provenance: z.enum(['fetched_page', 'search_excerpt', 'fact_check_api']),
  what_source_says: z.string(),
  authority_basis: z.string(),
  relevance_score: z.number(),
  directly_relevant: z.boolean(),
});
export const claimSchema = z.object({
  claim_id: text,
  claim_text: text,
  original_span: z.string(),
  entities: z.array(z.string()),
  dates: z.array(z.string()),
  qualifiers: z.array(z.string()),
  normalized_claim: z.string(),
  lexical_hash: z.string(),
  verdict: z.enum(verdicts),
  grounded_explanation: z.string(),
  explanation: z.string(),
  short_summary: z.string(),
  key_points: z.array(z.string()),
  evidence: z.array(evidenceSchema),
  limitations: z.array(z.string()),
  next_step: z.string(),
  risk: z.object({
    score: z.number().min(0).max(100),
    level: z.enum(['low', 'medium', 'high']),
    factors: z.array(z.object({ rule: z.string(), weight: z.number(), description: z.string() })),
    is_probability: z.literal(false),
    label: z.string(),
  }),
  temporal_context: z.object({
    claim_date: z.string().nullable(),
    relevant_source_dates: z.array(z.string()),
    notes: z.string(),
  }),
  original_context: z.object({
    status: z.enum(['not_checked', 'inconclusive', 'found']),
    notes: z.string(),
    source_urls: z.array(publicUrlSchema),
  }),
  checked_at: date,
});
export const verificationSchema = z.object({
  verification_id: text,
  status: z.enum(['completed', 'partial', 'no_checkable_claims']),
  input: extractionSchema,
  claims: z
    .array(claimSchema)
    .max(12)
    .refine(
      (claims) => new Set(claims.map((c) => c.claim_id)).size === claims.length,
      'Duplicate claim identifiers',
    ),
  summary: z.string(),
  checked_at: date,
  warnings: z.array(z.string()),
  response_language: languageSchema,
  audience: audienceSchema,
});
export const verifyRequestSchema = z
  .object({
    text: z.string().trim().min(1, 'Enter some text.').max(24000, 'Use at most 24,000 characters.'),
    input_type: z.enum(inputTypes).default('text'),
    input_language: z.enum(['auto', 'en', 'hi', 'mr']).default('auto'),
    response_language: languageSchema.default('en'),
    audience: audienceSchema.default('adult'),
    jurisdiction: z
      .string()
      .regex(/^[A-Z]{2}$/)
      .default('IN'),
  })
  .strict();
export const explainRequestSchema = z
  .object({
    result: verificationSchema,
    language: languageSchema,
    audience: audienceSchema.default('adult'),
  })
  .strict();
export const explanationSchema = verificationSchema;
export const healthSchema = z.object({
  status: text,
  capabilities: z.record(z.string(), z.unknown()).optional(),
  dependencies: z.record(z.string(), z.boolean()).optional(),
  limits: z.record(z.string(), z.number()).optional(),
  notes: z.array(z.string()).optional(),
});
export type Verification = z.infer<typeof verificationSchema>;
export type Claim = z.infer<typeof claimSchema>;
export type Extraction = z.infer<typeof extractionSchema>;
export type Explanation = Verification;
export type VerifyRequest = z.infer<typeof verifyRequestSchema>;
// Compatibility export: all three documented final statuses are supported.
export function requireCompleted(value: unknown): Verification {
  return verificationSchema.parse(value);
}
export function validateExplanation(original: Verification, value: unknown): Explanation {
  const result = explanationSchema.parse(value);
  const immutable = (report: Verification) => ({
    ...report,
    summary: '',
    response_language: 'en',
    audience: 'adult',
    claims: report.claims.map((claim) => ({
      ...claim,
      explanation: '',
      short_summary: '',
      key_points: [],
      next_step: '',
    })),
  });
  if (JSON.stringify(immutable(original)) !== JSON.stringify(immutable(result)))
    throw new Error('EXPLANATION_MISMATCH');
  return result;
}
