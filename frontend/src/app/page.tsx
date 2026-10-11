import { VerificationWorkspace } from '@/components/verification-workspace';
import { isMockMode } from '@/lib/api/server';
import { historyConfigured } from '@/lib/supabase/server';
export const dynamic = 'force-dynamic';
export default function Home() {
  return <VerificationWorkspace mock={isMockMode()} historyEnabled={historyConfigured()} />;
}
