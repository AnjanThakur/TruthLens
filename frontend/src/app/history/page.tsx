import { HistoryWorkspace } from '@/components/history-workspace';
import { historyConfigured } from '@/lib/supabase/server';
export const dynamic = 'force-dynamic';
export default function HistoryPage() {
  return <HistoryWorkspace enabled={historyConfigured()} />;
}
