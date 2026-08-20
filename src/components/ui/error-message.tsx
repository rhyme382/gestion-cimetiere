import { AlertCircle } from "lucide-react";
import { Card, CardContent } from "./card";

export interface ErrorMessageProps {
  error: Error | null | string;
  onRetry?: () => void;
}

export function ErrorMessage({ error, onRetry }: ErrorMessageProps) {
  if (!error) return null;

  const message = error instanceof Error ? error.message : String(error);

  return (
    <Card className="border-destructive bg-destructive/5">
      <CardContent className="flex items-start gap-3 py-4">
        <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-destructive">Erreur</p>
          <p className="text-xs text-destructive/80 mt-1 break-words">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="text-xs text-destructive underline mt-2 hover:no-underline"
            >
              Réessayer
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
