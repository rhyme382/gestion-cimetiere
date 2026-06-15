import { useQuery } from "./useQuery";
import { listIndividuals, getIndividual, createIndividual, updateIndividual, searchIndividuals } from "@/lib/tauri";
export function useIndividuals(options) {
    return useQuery(() => listIndividuals(), { enabled: options?.enabled !== false });
}
export function useIndividual(id, options) {
    return useQuery(() => getIndividual(id), { enabled: id !== null && options?.enabled !== false });
}
export function useSearchIndividuals(query, options) {
    return useQuery(() => searchIndividuals(query), { enabled: query !== null && query.trim() !== "" && options?.enabled !== false });
}
export async function createIndividualAsync(request) {
    try {
        return await createIndividual(request);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
export async function updateIndividualAsync(id, request) {
    try {
        return await updateIndividual(id, request);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
