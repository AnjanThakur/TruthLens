import { z } from 'zod';
import { verificationSchema } from '@/lib/api/contracts';
export const saveSchema = z.object({
  report: verificationSchema,
  receipt: z.string().min(1),
  consent_to_store: z.literal(true),
  retention_days: z.union([z.literal(7), z.literal(30), z.literal(90)]),
});
export const reportRowSchema = z.object({
  id: z.string().uuid(),
  verification_id: z.string(),
  input_type: z.string(),
  input_excerpt: z.string(),
  report_json: verificationSchema,
  created_at: z.string(),
  retention_expires_at: z.string(),
});
export const historySchema = z.object({
  reports: z.array(reportRowSchema),
  next_cursor: z.string().nullable(),
});
export type ReportRow = z.infer<typeof reportRowSchema>;
