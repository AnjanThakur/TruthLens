import { VerificationWorkspace } from '@/components/verification-workspace';
import { isMockMode, serverUploadLimit } from '@/lib/api/server';
import { historyConfigured } from '@/lib/supabase/server';
import { whatsappLink } from '@/lib/whatsapp';
export const dynamic = 'force-dynamic';
export default function Home() {
  return (
    <VerificationWorkspace
      mock={isMockMode()}
      historyEnabled={historyConfigured()}
      whatsappUrl={whatsappLink()}
      maxUploadBytes={serverUploadLimit()}
    />
  );
}
