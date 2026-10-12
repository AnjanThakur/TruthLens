import { AlertsWorkspace } from '@/components/alerts-workspace';
import { alertsConfigured } from '@/lib/alerts/server';
export const dynamic = 'force-dynamic';
export default function AlertsPage() {
  return <AlertsWorkspace enabled={alertsConfigured()} />;
}
