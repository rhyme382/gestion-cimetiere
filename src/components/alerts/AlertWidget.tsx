import { Card, CardContent, CardHeader, CardTitle, DataLoader, Button } from "@/components/ui";
import { useAlertSummary } from "@/hooks";
import { AlertTriangle, AlertCircle, AlertOctagon, ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

export function AlertWidget() {
  const navigate = useNavigate();
  const { data: summary, loading, error, refetch } = useAlertSummary();

  if (!summary) {
    return null;
  }

  const hasCritical = summary.critical_count > 0;
  const hasWarning = summary.warning_count > 0;
  const hasAlerts = summary.total_alerts > 0;

  const bgColor = hasCritical
    ? "bg-red-50"
    : hasWarning
    ? "bg-orange-50"
    : "bg-blue-50";

  const borderColor = hasCritical
    ? "border-red-200"
    : hasWarning
    ? "border-orange-200"
    : "border-blue-200";

  return (
    <DataLoader
      loading={loading}
      error={error}
      data={summary}
      onRetry={refetch}
    >
      <Card className={`${bgColor} ${borderColor} border-2`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              {hasCritical && <AlertOctagon className="h-4 w-4 text-red-600" />}
              {!hasCritical && hasWarning && (
                <AlertTriangle className="h-4 w-4 text-orange-600" />
              )}
              {!hasCritical && !hasWarning && hasAlerts && (
                <AlertCircle className="h-4 w-4 text-blue-600" />
              )}
              {!hasAlerts && <AlertCircle className="h-4 w-4 text-gray-400" />}
              Alertes
            </CardTitle>
            <span className="text-lg font-bold">
              {summary.total_alerts === 0 ? "✓" : summary.total_alerts}
            </span>
          </div>
        </CardHeader>
        <CardContent>
          {hasAlerts ? (
            <div className="space-y-3">
              <div className="space-y-2 text-xs">
                {summary.critical_count > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-red-600 rounded-full"></div>
                    <span className="text-red-800 font-medium">
                      {summary.critical_count} critique{summary.critical_count > 1 ? "s" : ""}
                    </span>
                  </div>
                )}
                {summary.warning_count > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-orange-600 rounded-full"></div>
                    <span className="text-orange-800 font-medium">
                      {summary.warning_count} alerte{summary.warning_count > 1 ? "s" : ""}
                    </span>
                  </div>
                )}
                {summary.info_count > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                    <span className="text-blue-800 font-medium">
                      {summary.info_count} info{summary.info_count > 1 ? "s" : ""}
                    </span>
                  </div>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate("/alertes")}
                className="w-full text-xs h-8 justify-between"
              >
                Voir tous
                <ChevronRight className="h-3 w-3" />
              </Button>
            </div>
          ) : (
            <p className="text-xs text-gray-600 text-center py-2">
              Aucune alerte — Tout est à jour
            </p>
          )}
        </CardContent>
      </Card>
    </DataLoader>
  );
}
