import { createBurial } from "@/lib/tauri";
import type { CreateBurialRequest } from "@/types/bindings";

export async function createBurialAsync(request: CreateBurialRequest) {
  try {
    return await createBurial(request);
  } catch (error) {
    throw error instanceof Error ? error : new Error(String(error));
  }
}
