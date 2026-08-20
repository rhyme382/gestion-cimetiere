import { useQuery } from "./useQuery";
import { listCemeteries, getCemetery, createCemetery, updateCemetery, deleteCemetery } from "@/lib/tauri";
import type { CemeteryDTO, CreateCemeteryRequest, UpdateCemeteryRequest } from "@/types/bindings";

interface UseCemeteriesOptions {
  enabled?: boolean;
}

export function useCemeteries(options?: UseCemeteriesOptions) {
  return useQuery<CemeteryDTO[]>(
    () => listCemeteries(),
    { enabled: options?.enabled !== false }
  );
}

export function useCemetery(id: number | null, options?: UseCemeteriesOptions) {
  return useQuery<CemeteryDTO>(
    () => getCemetery(id!),
    { enabled: id !== null && options?.enabled !== false }
  );
}

export async function createCemeteryAsync(request: CreateCemeteryRequest) {
  try {
    return await createCemetery(request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export async function updateCemeteryAsync(id: number, request: UpdateCemeteryRequest) {
  try {
    return await updateCemetery(id, request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export async function deleteCemeteryAsync(id: number) {
  try {
    return await deleteCemetery(id);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}
