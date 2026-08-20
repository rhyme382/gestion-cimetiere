import { useQuery } from "./useQuery";
import { listMunicipalities, getMunicipality, createMunicipality, updateMunicipality, deleteMunicipality } from "@/lib/tauri";
import type { MunicipalityDTO, CreateMunicipalityRequest, UpdateMunicipalityRequest } from "@/types/bindings";

interface UseMunicipalitiesOptions {
  enabled?: boolean;
}

export function useMunicipalities(options?: UseMunicipalitiesOptions) {
  return useQuery<MunicipalityDTO[]>(
    () => listMunicipalities(),
    { enabled: options?.enabled !== false }
  );
}

export function useMunicipality(id: number | null, options?: UseMunicipalitiesOptions) {
  return useQuery<MunicipalityDTO>(
    () => getMunicipality(id!),
    { enabled: id !== null && options?.enabled !== false }
  );
}

export async function createMunicipalityAsync(request: CreateMunicipalityRequest) {
  try {
    return await createMunicipality(request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export async function updateMunicipalityAsync(id: number, request: UpdateMunicipalityRequest) {
  try {
    return await updateMunicipality(id, request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export async function deleteMunicipalityAsync(id: number) {
  try {
    return await deleteMunicipality(id);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}
