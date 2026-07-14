import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { ErrorMessage } from "@/components/ui/error-message";
import { getDiagnostic } from "@/lib/tauri";
import type { DiagnosticDTO } from "@/types/bindings";
import { Activity } from "lucide-react";

export function DiagnosticCard() {
  const [diagnostic, setDiagnostic] = useState<DiagnosticDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDiagnostic = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDiagnostic();
      setDiagnostic(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la récupération du diagnostic");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostic();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-base">Diagnostic technique</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <LoadingSpinner />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <div className="space-y-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-muted-foreground" />
              <CardTitle className="text-base">Diagnostic technique</CardTitle>
            </div>
          </CardHeader>
        </Card>
        <ErrorMessage error={error} onRetry={fetchDiagnostic} />
      </div>
    );
  }

  if (!diagnostic) return null;

  const healthVariant = diagnostic.health === "Ok" ? "success" : "danger";
  const sqliteVariant = diagnostic.sqlite_available ? "success" : "danger";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-base">Diagnostic technique</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">État global</p>
              <Badge variant={healthVariant}>{diagnostic.health}</Badge>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Base de données</p>
              <Badge variant={sqliteVariant}>
                {diagnostic.sqlite_available ? "SQLite OK" : "Indisponible"}
              </Badge>
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Version</p>
            <p className="text-sm font-mono bg-muted px-2 py-1 rounded">
              {diagnostic.app_version}
            </p>
          </div>

          {diagnostic.message && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Message</p>
              <p className="text-sm text-foreground">{diagnostic.message}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
