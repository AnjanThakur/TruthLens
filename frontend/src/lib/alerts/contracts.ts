import { z } from 'zod';
import { languageSchema, publicUrlSchema, verificationSchema } from '@/lib/api/contracts';

export const contributeSchema = z
  .object({ consent: z.literal(true), report: verificationSchema, receipt: z.string().max(200) })
  .strict();
export const contributionResponseSchema = z.object({
  accepted: z.literal(true),
  duplicate: z.boolean(),
  deferred: z.boolean(),
});
export const draftSchema = z.object({
  alert_id: z.string().uuid(),
  cluster_id: z.string().uuid(),
  title: z.string().max(160),
  claim_summary: z.string().nullable(),
  explanation: z.string(),
  language: languageSchema,
  language_content_status: z.enum(['ready', 'pending_translation']),
  approval_status: z.enum(['draft', 'pending_review', 'approved', 'rejected', 'expired']),
  content_version: z.number().int().positive(),
  expires_at: z.string(),
  authoritative_source_links: z.array(publicUrlSchema),
  scope_note: z.string(),
  scam_warning_signs: z.array(z.string()),
  recommended_user_actions: z.array(z.string()),
});
export const referenceSchema = z.object({
  url: publicUrlSchema,
  publisher: z.string(),
  excerpt: z.string(),
  eligible: z.boolean(),
  stance: z.string(),
  published_at: z.string().nullable(),
  retrieved_at: z.string(),
});
export const clusterSchema = z.object({
  cluster_id: z.string().uuid(),
  canonical_claim: z.string(),
  status: z.string(),
  unique_submission_count: z.number().int(),
  evidence_references: z.array(referenceSchema),
  trend: z.object({ scope: z.string() }).nullable(),
});
export const dashboardSchema = z.object({
  clusters: z.array(clusterSchema),
  drafts: z.array(draftSchema),
  publishing: z.literal(false),
});
export const reviewSchema = z.discriminatedUnion('action', [
  z
    .object({
      action: z.literal('create'),
      cluster_id: z.string().uuid(),
      language: languageSchema,
    })
    .strict(),
  z
    .object({
      action: z.literal('submit'),
      alert_id: z.string().uuid(),
      expected_version: z.number().int().positive(),
    })
    .strict(),
  z
    .object({
      action: z.literal('approve'),
      alert_id: z.string().uuid(),
      expected_version: z.number().int().positive(),
      evidence_reviewed: z.literal(true),
    })
    .strict(),
  z
    .object({
      action: z.literal('reject'),
      alert_id: z.string().uuid(),
      expected_version: z.number().int().positive(),
      reason: z.enum(['insufficient_evidence', 'translation_needed', 'incorrect_content', 'other']),
    })
    .strict(),
  z
    .object({
      action: z.literal('edit'),
      alert_id: z.string().uuid(),
      expected_version: z.number().int().positive(),
      title: z.string().min(1).max(160),
      claim_summary: z.string().min(1).max(1200),
      explanation: z.string().min(1).max(1800),
      translation_reviewed: z.boolean(),
    })
    .strict(),
]);
export type AlertDraft = z.infer<typeof draftSchema>;
export type AlertDashboard = z.infer<typeof dashboardSchema>;
