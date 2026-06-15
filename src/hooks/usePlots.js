import { useQuery } from "./useQuery";
import { listPlots, getPlot, createPlot, updatePlot } from "@/lib/tauri";
export function usePlots(cemeteryId, options) {
    return useQuery(() => listPlots(cemeteryId), { enabled: cemeteryId !== null && options?.enabled !== false });
}
export function usePlot(id, options) {
    return useQuery(() => getPlot(id), { enabled: id !== null && options?.enabled !== false });
}
export async function createPlotAsync(request) {
    try {
        return await createPlot(request);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
export async function updatePlotAsync(id, request) {
    try {
        return await updatePlot(id, request);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
