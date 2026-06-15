import { useQuery } from "./useQuery";
import { listIndividuals, getIndividual, createIndividual, updateIndividual, searchIndividuals } from "@/lib/tauri";
import type { IndividualDTO, CreateIndividualRequest, UpdateIndividualRequest } from "@/types/bindings";

interface UseIndividualsOptions {
  enabled?: boolean;
}

export function useIndividuals(options?: UseIndividualsOptions) {
  return useQuery<IndividualDTO[]>(
    () => listIndividuals(),
    { enabled: options?.enabled !== false }
  );
}

export function useIndividual(id: number | null, options?: UseIndividualsOptions) {
  return useQuery<IndividualDTO>(
    () => getIndividual(id!),
    { enabled: id !== null && options?.enabled !== false }
  );
}

export function useSearchIndividuals(query: string | null, options?: UseIndividualsOptions) {
  return useQuery<IndividualDTO[]>(
    () => searchIndividuals(query!),
    { enabled: query !== null && query.trim() !== "" && options?.enabled !== false }
  );
}

export async function createIndividualAsync(request: CreateIndividualRequest) {
  try {
    return await createIndividual(request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}

export async function updateIndividualAsync(id: number, request: UpdateIndividualRequest) {
  try {
    return await updateIndividual(id, request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}
