import { useQuery } from "./useQuery";
import { listConcessions, getConcession, createConcession, updateConcession } from "@/lib/tauri";
export function useConcessions(options) {
    return useQuery(() => listConcessions(options?.cemeteryId), { enabled: options?.enabled !== false });
}
export function useConcession(id, options) {
    return useQuery(() => getConcession(id), { enabled: id !== null && options?.enabled !== false });
}
export async function createConcessionAsync(request) {
    try {
        return await createConcession(request);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
export async function updateConcessionAsync(id, request) {
    try {
        return await updateConcession(id, request);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
