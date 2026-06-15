import { useQuery } from "./useQuery";
import { listPlots, getPlot, createPlot, updatePlot } from "@/lib/tauri";
import type { PlotDTO, CreatePlotRequest, UpdatePlotRequest } from "@/types/bindings";

interface UsePlotsOptions {
  enabled?: boolean;
}

export function usePlots(cemeteryId: number | null, options?: UsePlotsOptions) {
  return useQuery<PlotDTO[]>(
    () => listPlots(cemeteryId!),
    { enabled: cemeteryId !== null && options?.enabled !== false }
  );
}

export function usePlot(id: number | null, options?: UsePlotsOptions) {
  return useQuery<PlotDTO>(
    () => getPlot(id!),
    { enabled: id !== null && options?.enabled !== false }
  );
}

export async function createPlotAsync(request: CreatePlotRequest) {
  try {
    return await createPlot(request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export async function updatePlotAsync(id: number, request: UpdatePlotRequest) {
  try {
    return await updatePlot(id, request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}
