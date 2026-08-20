import { ReactNode } from "react";
import { LoadingSpinner } from "./loading-spinner";
import { ErrorMessage } from "./error-message";
import { EmptyState } from "./empty-state";

export interface DataLoaderProps {
  loading: boolean;
  error: Error | null;
  data: unknown;
  children: ReactNode;
  onRetry?: () => void;
  emptyState?: {
    icon?: ReactNode;
    title: string;
    description?: string;
  };
}

export function DataLoader({
  loading,
  error,
  data,
  children,
  onRetry,
  emptyState,
}: DataLoaderProps) {
  if (loading) {
    return <LoadingSpinner size="md" />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={onRetry} />;
  }

  if (!data || (Array.isArray(data) && data.length === 0)) {
    if (emptyState) {
      return <EmptyState {...emptyState} />;
    }
    return null;
  }

  return <>{children}</>;
}
