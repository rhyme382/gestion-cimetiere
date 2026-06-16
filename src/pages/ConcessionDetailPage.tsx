import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, DataLoader, ErrorMessage } from "@/components/ui";
import { useConcession, useCemetery, usePlot, useAlerts, acknowledgeAlertAsync } from "@/hooks";
import { ArrowLeft, AlertTriangle, AlertOctagon, AlertCircle } from "lucide-react";
import { formatDate } from "@/lib/utils";
import { PlotViewer } from "@/components/map/PlotViewer";
import { useState } from "react";

export default function ConcessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const concessionId = id ? Number(id) : null;
  const [acknowledging, setAcknowledging] = useState<number | null>(null);

  const { data: concession, loading, error, refetch } = useConcession(concessionId);
  const { data: cemetery } = useCemetery(concession?.cemetery_id ?? null);
  const { data: plot } = usePlot(concession?.plot_id ?? null);
  const { data: allAlerts, refetch: refetchAlerts } = useAlerts();

  const relatedAlerts = allAlerts?.filter((a) => a.concession_id === concessionId) ?? [];

  async function handleAcknowledgeAlert(alert_id: number) {
    setAcknowledging(alert_id);
    try {
      await acknowledgeAlertAsync(alert_id);
      await refetchAlerts();
    } catch (err) {
      console.error("Erreur lors de l'acquittement:", err);
    } finally {
      setAcknowledging(null);
    }
  }

  if (!concessionId) {
    return (
      <div className="space-y-4">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-sm text-muted-foreground">ID de concession invalide</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    active: "bg-green-100 text-green-800",
    expiring_soon: "bg-orange-100 text-orange-800",
    expired: "bg-red-100 text-red-800",
    renewed: "bg-blue-100 text-blue-800",
    abandoned: "bg-gray-100 text-gray-800",
    reclaimed: "bg-purple-100 text-purple-800",
    archived: "bg-slate-100 text-slate-800",
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-bold">Concession {concessionId}</h1>
      </div>

      {error && <ErrorMessage error={error} onRetry={refetch} />}

      {/* Alerts */}
      {relatedAlerts.length > 0 && (
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2 text-orange-800">
              <AlertTriangle className="h-4 w-4" />
              Alertes associées
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {relatedAlerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between p-3 border rounded bg-white"
              >
                <div className="flex items-center gap-3 flex-1">
                  {alert.alert_type === "CRITICAL" && (
                    <AlertOctagon className="h-4 w-4 text-red-600 flex-shrink-0" />
                  )}
                  {alert.alert_type === "WARNING" && (
                    <AlertTriangle className="h-4 w-4 text-orange-600 flex-shrink-0" />
                  )}
                  {alert.alert_type === "INFO" && (
                    <AlertCircle className="h-4 w-4 text-blue-600 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <p className="text-xs font-medium">
                      {alert.alert_type === "CRITICAL"
                        ? "Alerte critique"
                        : alert.alert_type === "WARNING"
                        ? "Alerte"
                        : "Information"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Expire le {formatDate(alert.expected_expiry_date)} (
                      {alert.days_until_expiry} jours)
                    </p>
                  </div>
                </div>
                {!alert.acknowledged_at && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAcknowledgeAlert(alert.id)}
                    disabled={acknowledging === alert.id}
                    className="text-xs h-7 ml-2 flex-shrink-0"
                  >
                    {acknowledging === alert.id ? "..." : "Acquitter"}
                  </Button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Details */}
      <DataLoader
        loading={loading}
        error={error}
        data={concession}
        onRetry={refetch}
      >
        {concession && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Localisation */}
            {concession.plot_id && (
              <div className="lg:col-span-3">
                <PlotViewer plot={plot} cemeteryName={cemetery?.name} size="sm" />
              </div>
            )}

            {/* Main Info */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base">Informations générales</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground font-medium">ID</p>
                    <p className="text-sm font-semibold mt-1">{concession.id}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium">Cimetière</p>
                    <p className="text-sm font-semibold mt-1">{concession.cemetery_id}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium">Emplacement</p>
                    <p className="text-sm font-semibold mt-1">{concession.plot_id ?? "—"}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium">Statut</p>
                    <p className="mt-1">
                      <Badge className={`${statusColors[concession.status]} text-xs font-semibold`}>
                        {concession.status === "active" && "Actif"}
                        {concession.status === "expiring_soon" && "Expirant bientôt"}
                        {concession.status === "expired" && "Expiré"}
                        {concession.status === "renewed" && "Renouvelé"}
                        {concession.status === "abandoned" && "Abandonné"}
                        {concession.status === "reclaimed" && "Repris"}
                        {concession.status === "archived" && "Archivé"}
                      </Badge>
                    </p>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <h3 className="font-semibold text-sm mb-3">Dates importantes</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Acquise le</p>
                      <p className="text-sm mt-1">{formatDate(concession.acquired_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Expire le</p>
                      <p className="text-sm mt-1">{formatDate(concession.expires_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Renouvelée le</p>
                      <p className="text-sm mt-1">{formatDate(concession.renewed_at)}</p>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <h3 className="font-semibold text-sm mb-3">Audit</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Créée le</p>
                      <p className="text-xs mt-1">{formatDate(concession.created_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Modifiée le</p>
                      <p className="text-xs mt-1">{formatDate(concession.updated_at)}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Sidebar Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button className="w-full" variant="default">
                  Éditer
                </Button>
                <Button className="w-full" variant="outline">
                  Imprimer
                </Button>
                <Button className="w-full" variant="outline">
                  Télécharger
                </Button>
                {concession.plot_id && (
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={() => navigate("/emplacements")}
                  >
                    Voir sur la carte
                  </Button>
                )}
                <Button className="w-full" variant="destructive">
                  Supprimer
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </DataLoader>
    </div>
  );
}
