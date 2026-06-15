import { createBurial } from "@/lib/tauri";
export async function createBurialAsync(request) {
    try {
        return await createBurial(request);
    }
    catch (error) {
        throw error instanceof Error ? error : new Error(String(error));
    }
}
