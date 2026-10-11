import { VerificationWorkspace } from '@/components/verification-workspace';
import { isMockMode, serverUploadLimit } from '@/lib/api/server';
import { historyConfigured } from '@/lib/supabase/server';
import { whatsappLink } from '@/lib/whatsapp';
import { alertsConfigured } from '@/lib/alerts/server';
export const dynamic = 'force-dynamic';
export default function Home() {
  return (
    <VerificationWorkspace
      mock={isMockMode()}
      historyEnabled={historyConfigured()}
      alertsEnabled={alertsConfigured()}
      whatsappUrl={whatsappLink()}
      maxUploadBytes={serverUploadLimit()}
    />
  );
}
