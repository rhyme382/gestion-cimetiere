import { generateConcessionPdf } from "@/lib/tauri";
import { useState } from "react";

interface UsePdfGenerationResult {
  generating: boolean;
  error: string | null;
  filePath: string | null;
  generate: () => Promise<void>;
  reset: () => void;
}

export function usePdfGeneration(concessionId: number | null): UsePdfGenerationResult {
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filePath, setFilePath] = useState<string | null>(null);

  const generate = async () => {
    if (!concessionId) {
      setError("ID de concession invalide");
      return;
    }

    setGenerating(true);
    setError(null);
    setFilePath(null);

    try {
      const path = await generateConcessionPdf(concessionId);
      setFilePath(path);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Erreur lors de la génération du PDF: ${message}`);
      console.error("PDF generation error:", err);
    } finally {
      setGenerating(false);
    }
  };

  const reset = () => {
    setError(null);
    setFilePath(null);
  };

  return { generating, error, filePath, generate, reset };
}
