import { useQuery } from "./useQuery";
import { listConcessions, getConcession, createConcession, updateConcession } from "@/lib/tauri";
import type { ConcessionDTO, CreateConcessionRequest, UpdateConcessionRequest } from "@/types/bindings";

interface UseConcessionsOptions {
  enabled?: boolean;
  cemeteryId?: number;
}

export function useConcessions(options?: UseConcessionsOptions) {
  return useQuery<ConcessionDTO[]>(
    () => listConcessions(options?.cemeteryId),
    { enabled: options?.enabled !== false }
  );
}

export function useConcession(id: number | null, options?: UseConcessionsOptions) {
  return useQuery<ConcessionDTO>(
    () => getConcession(id!),
    { enabled: id !== null && options?.enabled !== false }
  );
}

export async function createConcessionAsync(request: CreateConcessionRequest) {
  try {
    return await createConcession(request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export async function updateConcessionAsync(id: number, request: UpdateConcessionRequest) {
  try {
    return await updateConcession(id, request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}
