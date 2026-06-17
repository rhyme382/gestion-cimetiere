import { invoke } from "@tauri-apps/api/core";
import { useState, useCallback } from "react";

export interface BackupInfo {
  filename: string;
  path: string;
  size: number;
  created_at: string;
}

interface UseBackupsResult {
  backups: BackupInfo[] | null;
  loading: boolean;
  error: string | null;
  creating: boolean;
  restoring: boolean;
  listBackups: () => Promise<void>;
  createBackup: () => Promise<void>;
  restoreBackup: (filename: string) => Promise<void>;
  reset: () => void;
}

export function useBackups(): UseBackupsResult {
  const [backups, setBackups] = useState<BackupInfo[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState(false);

  const listBackups = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await invoke<BackupInfo[]>("list_backups");
      setBackups(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Erreur lors de la récupération des sauvegardes: ${message}`);
      console.error("List backups error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createBackup = useCallback(async () => {
    setCreating(true);
    setError(null);
    try {
      await invoke("create_backup");
      // Refresh the list
      await listBackups();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Erreur lors de la création de sauvegarde: ${message}`);
      console.error("Create backup error:", err);
    } finally {
      setCreating(false);
    }
  }, [listBackups]);

  const restoreBackup = useCallback(async (filename: string) => {
    setRestoring(true);
    setError(null);
    try {
      await invoke("restore_backup", { filename });
      // Refresh the list after restore
      await listBackups();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Erreur lors de la restauration: ${message}`);
      console.error("Restore backup error:", err);
    } finally {
      setRestoring(false);
    }
  }, [listBackups]);

  const reset = useCallback(() => {
    setError(null);
  }, []);

  return { backups, loading, error, creating, restoring, listBackups, createBackup, restoreBackup, reset };
}
