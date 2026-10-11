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
const date = z
  .string()
  .refine((value) => !Number.isNaN(Date.parse(value)), 'Invalid date')
  .nullable();
export const evidenceSchema = z.object({
  title: text,
  url: publicUrlSchema,
  publisher: text,
  published_at: date,
  retrieved_at: date,
  source_type: text,
  stance: z.enum(stances),
  excerpt: z.string(),
  what_source_says: z.string(),
});
export const claimSchema = z.object({
  claim_id: text,
  claim_text: text,
  verdict: z.enum(verdicts),
  explanation: text,
  short_summary: text,
  evidence: z.array(evidenceSchema),
  limitations: z.array(z.string()),
  next_step: z.string(),
  temporal_context: z.string().nullable(),
  original_context: z.string().nullable(),
  forwarding_risk: z.unknown().optional(),
});
export const verificationSchema = z.object({
  verification_id: text,
  // Deliberately no invented transport-status enum. Render only completed until P1 confirms.
  status: text,
  input: z.object({ text: z.string(), detected_language: text, input_type: z.enum(inputTypes) }),
  claims: z
    .array(claimSchema)
    .refine(
      (claims) => new Set(claims.map((c) => c.claim_id)).size === claims.length,
      'Duplicate claim identifiers',
    ),
  summary: z.string(),
  checked_at: z.string().refine((value) => !Number.isNaN(Date.parse(value))),
  warnings: z.array(z.string()),
});
export const extractionSchema = z.object({
  text: z.string(),
  detected_language: text,
  input_type: z.enum(inputTypes),
  metadata: z.record(z.string(), z.unknown()).optional(),
  warnings: z.array(z.string()),
});
export const verifyRequestSchema = z.object({
  text: z
    .string()
    .trim()
    .min(10, 'Add at least 10 characters.')
    .max(30000, 'Use at most 30,000 characters.'),
  input_type: z.enum(inputTypes),
  detected_language: z.string().optional(),
  source_metadata: z.record(z.string(), z.unknown()).optional(),
});
export const explainRequestSchema = z.object({
  verification: verificationSchema,
  language: languageSchema,
  audience: z.enum(['standard', 'easy']),
});
// Provisional: only these display strings may be returned by /explain.
export const explanationSchema = z.object({
  verification_id: text,
  language: languageSchema,
  audience: z.enum(['standard', 'easy']),
  summary: z.string(),
  claims: z.array(
    z.object({ claim_id: text, explanation: text, short_summary: text, next_step: z.string() }),
  ),
});
export const healthSchema = z.object({
  status: text,
  capabilities: z
    .object({ extract: z.array(z.enum(inputTypes)), verify: z.boolean(), explain: z.boolean() })
    .optional(),
});
export type Verification = z.infer<typeof verificationSchema>;
export type Claim = z.infer<typeof claimSchema>;
export type Extraction = z.infer<typeof extractionSchema>;
export type Explanation = z.infer<typeof explanationSchema>;
export type VerifyRequest = z.infer<typeof verifyRequestSchema>;

export function requireCompleted(value: unknown): Verification {
  const result = verificationSchema.parse(value);
  if (result.status !== 'completed') throw new Error('UNSUPPORTED_STATUS');
  return result;
}

export function validateExplanation(original: Verification, value: unknown): Explanation {
  const result = explanationSchema.parse(value);
  const ids = new Set(result.claims.map((c) => c.claim_id));
  if (
    result.verification_id !== original.verification_id ||
    result.claims.length !== original.claims.length ||
    ids.size !== result.claims.length ||
    original.claims.some((c) => !ids.has(c.claim_id))
  ) {
    throw new Error('EXPLANATION_MISMATCH');
  }
  // No spreading of the rewritten response onto the verified object. Facts stay immutable.
  return result;
}
