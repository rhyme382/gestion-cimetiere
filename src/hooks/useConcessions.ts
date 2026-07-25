import { useQuery } from "./useQuery";
import { listConcessions, getConcession, createConcession, updateConcession } from "@/lib/tauri";
import type { ConcessionDTO, CreateConcessionRequest, UpdateConcessionRequest, ApiErrorResponse } from "@/types/bindings";

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

export function getErrorMessage(error: unknown): string {
  if (!error) return "Unknown error";
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;

  // Handle ApiErrorResponse structure
  const apiError = error as Record<string, unknown>;
  if (apiError && typeof apiError === "object") {
    if ("message" in apiError && typeof apiError.message === "string") {
      return apiError.message;
    }
  }

  return String(error);
}

export async function createConcessionAsync(request: CreateConcessionRequest): Promise<ConcessionDTO> {
  try {
    return await createConcession(request);
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function updateConcessionAsync(id: number, request: UpdateConcessionRequest): Promise<ConcessionDTO> {
  try {
    return await updateConcession(id, request);
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}
