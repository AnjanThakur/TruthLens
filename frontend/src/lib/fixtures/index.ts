import fixtureData from './synthetic.json';
import {
  extractionSchema,
  verificationSchema,
  type InputType,
  type Verification,
} from '@/lib/api/contracts';
export const fixtures = fixtureData.fixtures.map((f) => ({
  id: f.fixture_id,
  description: f.description,
  extraction: f.extract_response ? extractionSchema.parse(f.extract_response) : null,
  verification: verificationSchema.parse(f.verification_response),
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
