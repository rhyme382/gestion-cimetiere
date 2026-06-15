import { useQuery } from "./useQuery";
import { listCemeteries, getCemetery, createCemetery, updateCemetery, deleteCemetery } from "@/lib/tauri";
export function useCemeteries(options) {
    return useQuery(() => listCemeteries(), { enabled: options?.enabled !== false });
}
export function useCemetery(id, options) {
    return useQuery(() => getCemetery(id), { enabled: id !== null && options?.enabled !== false });
}
export async function createCemeteryAsync(request) {
    try {
        return await createCemetery(request);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
export async function updateCemeteryAsync(id, request) {
    try {
        return await updateCemetery(id, request);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
export async function deleteCemeteryAsync(id) {
    try {
        return await deleteCemetery(id);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
