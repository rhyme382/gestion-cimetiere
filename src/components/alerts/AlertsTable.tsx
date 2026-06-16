import { useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  DataLoader,
  Badge,
} from "@/components/ui";
import { useAlerts, acknowledgeAlertAsync } from "@/hooks";
import { AlertTriangle, Check, AlertCircle, AlertOctagon } from "lucide-react";
import { formatDate } from "@/lib/utils";
import { useNavigate } from "react-router-dom";

export function AlertsTable() {
  const navigate = useNavigate();
  const { data: alerts, loading, error, refetch } = useAlerts();
  const [acknowledging, setAcknowledging] = useState<number | null>(null);

  async function handleAcknowledge(alert_id: number) {
    setAcknowledging(alert_id);
    try {
      await acknowledgeAlertAsync(alert_id);
      await refetch();
    } catch (err) {
      console.error("Erreur lors de l'acquittement:", err);
    } finally {
      setAcknowledging(null);
    }
  }

  const getAlertIcon = (type: string) => {
    switch (type) {
      case "CRITICAL":
        return <AlertOctagon className="h-4 w-4 text-red-600" />;
      case "WARNING":
        return <AlertTriangle className="h-4 w-4 text-orange-600" />;
      case "INFO":
        return <AlertCircle className="h-4 w-4 text-blue-600" />;
      default:
        return null;
    }
  };

  const getAlertBadgeVariant = (type: string) => {
    switch (type) {
      case "CRITICAL":
        return "danger";
      case "WARNING":
        return "warning";
      case "INFO":
        return "info";
      default:
        return "default";
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Alertes d'échéance</CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          Affiche les concessions approchant de l'expiration
        </p>
      </CardHeader>
      <CardContent>
        <DataLoader
          loading={loading}
          error={error}
          data={alerts}
          onRetry={refetch}
          emptyState={{
            icon: <Check className="h-8 w-8" />,
            title: "Aucune alerte",
            description: "Toutes les concessions sont à jour",
          }}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-2 font-semibold text-xs">
                    Sévérité
                  </th>
                  <th className="text-left px-4 py-2 font-semibold text-xs">
                    Concession
                  </th>
                  <th className="text-left px-4 py-2 font-semibold text-xs">
                    Expiration
                  </th>
                  <th className="text-left px-4 py-2 font-semibold text-xs">
                    Urgence
                  </th>
                  <th className="text-left px-4 py-2 font-semibold text-xs">
                    Créée le
                  </th>
                  <th className="text-center px-4 py-2 font-semibold text-xs">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {alerts?.map((alert) => (
                  <tr
                    key={alert.id}
                    className="border-b hover:bg-gray-50 transition"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getAlertIcon(alert.alert_type)}
                        <Badge
                          variant={getAlertBadgeVariant(alert.alert_type)}
                          className="text-xs"
                        >
                          {alert.alert_type === "CRITICAL"
                            ? "Critique"
                            : alert.alert_type === "WARNING"
                            ? "Alerte"
                            : "Info"}
                        </Badge>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => navigate(`/concessions/${alert.concession_id}`)}
                        className="text-blue-600 hover:underline font-medium text-xs"
                      >
                        Concession {alert.concession_id}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {formatDate(alert.expected_expiry_date)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`font-semibold text-xs ${
                          alert.days_until_expiry <= 30
                            ? "text-red-600"
                            : alert.days_until_expiry <= 90
                            ? "text-orange-600"
                            : "text-blue-600"
                        }`}
                      >
                        {alert.days_until_expiry} j
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">
                      {formatDate(alert.created_at)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAcknowledge(alert.id)}
                        disabled={acknowledging === alert.id}
                        className="text-xs h-7"
                      >
                        {acknowledging === alert.id ? "..." : "Acquitter"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataLoader>
      </CardContent>
    </Card>
  );
}
