import { useQuery } from "./useQuery";
import { listAlerts, getAlertSummary, refreshAlerts, acknowledgeAlert } from "@/lib/tauri";
import type { AlertDTO, AlertSummaryDTO } from "@/types/bindings";

interface UseAlertsOptions {
  enabled?: boolean;
}

export function useAlerts(options?: UseAlertsOptions) {
  return useQuery<AlertDTO[]>(
    () => listAlerts(),
    { enabled: options?.enabled !== false }
  );
}

export function useAlertSummary(options?: UseAlertsOptions) {
  return useQuery<AlertSummaryDTO>(
    () => getAlertSummary(),
    { enabled: options?.enabled !== false }
  );
}

export async function refreshAlertsAsync() {
  try {
    return await refreshAlerts();
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export async function acknowledgeAlertAsync(alert_id: number) {
  try {
    return await acknowledgeAlert(alert_id);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}
