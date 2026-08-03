import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Badge, Button, DataLoader, ErrorMessage, Input } from "@/components/ui";
import { useConcessions, useCemeteries } from "@/hooks";
import { listPlots } from "@/lib/tauri";
import { FileText, Search, Plus } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { ConcessionDTO, CemeteryDTO, PlotDTO } from "@/types/bindings";

const EMPTY_CONCESSIONS: ConcessionDTO[] = [];
const EMPTY_CEMETERIES: CemeteryDTO[] = [];

export default function ConcessionsPage() {
  const navigate = useNavigate();

  const {
    data: concessionsData,
    loading,
    isRefetching,
    error,
    refetch,
  } = useConcessions();

  const concessions = concessionsData ?? EMPTY_CONCESSIONS;

  const {
    data: cemeteriesData,
    error: cemeteriesError,
  } = useCemeteries();

  const cemeteries = cemeteriesData ?? EMPTY_CEMETERIES;

  const [plots, setPlots] = useState<Map<number, PlotDTO>>(new Map());
  const [plotsLoading, setplotsLoading] = useState(false);
  const [plotsError, setPlotsError] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    const loadPlots = async () => {
      const uniqueCemeteryIds = new Set(concessions?.map((c) => c.cemetery_id) ?? []);
      if (uniqueCemeteryIds.size === 0) {
        setPlots(new Map());
        setPlotsError(null);
        setplotsLoading(false);
        return;
      }

      setplotsLoading(true);
      setPlotsError(null);
      const plotsMap = new Map<number, PlotDTO>();
      let hasError = false;

      for (const cemeteryId of uniqueCemeteryIds) {
        try {
          const cemeteryPlots = await listPlots(cemeteryId);
          cemeteryPlots?.forEach((plot) => {
            plotsMap.set(plot.id, plot);
          });
        } catch (err) {
          setPlotsError(`Erreur lors du chargement des emplacements du cimetière ${cemeteryId}`);
          hasError = true;
          break;
        }
      }

      if (!hasError) {
        setPlots(plotsMap);
      }
      setplotsLoading(false);
    };

    if (concessions && concessions.length > 0) {
      loadPlots();
    } else if (concessions?.length === 0) {
      setPlots(new Map());
      setPlotsError(null);
      setplotsLoading(false);
    }
  }, [concessions]);

  const filteredConcessions = useMemo(() => {
    let results = concessions ?? [];

    if (selectedStatus) {
      results = results.filter((c) => c.status === selectedStatus);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      results = results.filter((c) => {
        const matchesNumber = c.concession_number?.toLowerCase().includes(query) ?? false;
        const matchesFirstName = c.holder_first_name?.toLowerCase().includes(query) ?? false;
        const matchesLastName = c.holder_last_name?.toLowerCase().includes(query) ?? false;
        return matchesNumber || matchesFirstName || matchesLastName;
      });
    }

    return results;
  }, [concessions, selectedStatus, searchQuery]);

  const statusColors: Record<string, string> = {
    ACTIVE: "bg-green-100 text-green-800",
    ECHEANCE_PROCHE: "bg-orange-100 text-orange-800",
    EXPIREE: "bg-red-100 text-red-800",
    PERPETUELLE: "bg-blue-100 text-blue-800",
  };

  const getStatusLabel = (status: string): string => {
    switch (status) {
      case "ACTIVE":
        return "Actif";
      case "ECHEANCE_PROCHE":
        return "Échéance proche";
      case "EXPIREE":
        return "Expiré";
      case "PERPETUELLE":
        return "Perpétuelle";
      default:
        return status;
    }
  };

  const getCemeteryName = (cemeteryId: number): string => {
    const cemetery = (cemeteries ?? []).find((c) => c.id === cemeteryId);
    return cemetery?.name ?? "—";
  };

  const getPlotLocation = (plotId: number | null): string => {
    if (!plotId) return "—";
    const plot = plots.get(plotId);
    if (!plot) return "—";
    const parts = [
      plot.section ?? "—",
      plot.row ?? "—",
      plot.number ?? "—",
    ];
    return parts.join(" • ");
  };

  return (
    <div className="space-y-4">
      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Rechercher une concession</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            <Input
              placeholder="Numéro, concessionnaire..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1"
            />
          </div>
        </CardContent>
      </Card>

      {/* Status Filter */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Filtrer par statut</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            variant={selectedStatus === null ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedStatus(null)}
          >
            Tous
          </Button>
          {["ACTIVE", "ECHEANCE_PROCHE", "EXPIREE", "PERPETUELLE"].map((status) => (
            <Button
              key={status}
              variant={selectedStatus === status ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedStatus(status)}
            >
              {getStatusLabel(status)}
            </Button>
          ))}
        </CardContent>
      </Card>

      {/* List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle className="text-base">Concessions</CardTitle>
              {(isRefetching || plotsLoading) && (
                <span className="text-xs text-muted-foreground animate-pulse">
                  Actualisation en cours...
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={() => navigate("/concessions/new")}
                className="gap-2"
              >
                <Plus className="h-4 w-4" />
                Créer
              </Button>
              {error && <ErrorMessage error={error} onRetry={refetch} />}
            </div>
          </div>
          {(cemeteriesError || plotsError) && (
            <span className="text-xs text-orange-600 mt-2">
              Avertissement: Certaines données annexes ne sont pas disponibles
            </span>
          )}
        </CardHeader>
        <CardContent>
          <DataLoader
            loading={loading}
            error={error}
            data={filteredConcessions}
            onRetry={refetch}
            emptyState={{
              icon: <FileText className="h-8 w-8" />,
              title: "Aucune concession",
              description: searchQuery || selectedStatus
                ? "Aucune concession ne correspond à vos critères"
                : "Créez une première concession pour la voir ici",
            }}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">N° Concession</th>
                    <th className="text-left py-3 px-4">Concessionnaire</th>
                    <th className="text-left py-3 px-4">Cimetière</th>
                    <th className="text-left py-3 px-4">Emplacement</th>
                    <th className="text-left py-3 px-4">Type</th>
                    <th className="text-left py-3 px-4">Date de début</th>
                    <th className="text-left py-3 px-4">Expire le</th>
                    <th className="text-left py-3 px-4">Statut</th>
                    <th className="text-left py-3 px-4"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredConcessions?.map((c) => (
                    <tr key={c.id} className="border-b hover:bg-accent transition">
                      <td className="py-3 px-4 font-medium">{c.concession_number || `#${c.id}`}</td>
                      <td className="py-3 px-4">
                        {c.holder_first_name || c.holder_last_name
                          ? `${c.holder_first_name ?? ""} ${c.holder_last_name ?? ""}`.trim()
                          : "—"}
                      </td>
                      <td className="py-3 px-4">{getCemeteryName(c.cemetery_id)}</td>
                      <td className="py-3 px-4">{getPlotLocation(c.plot_id)}</td>
                      <td className="py-3 px-4">
                        {c.concession_type === "PERPETUELLE"
                          ? "Perpétuelle"
                          : c.concession_type === "TRENTENAIRE"
                          ? "30 ans"
                          : c.concession_type === "CINQUANTENAIRE"
                          ? "50 ans"
                          : c.concession_type === "TEMPORAIRE"
                          ? "Temporaire"
                          : c.concession_type ?? "—"}
                      </td>
                      <td className="py-3 px-4">{c.start_date ? formatDate(c.start_date) : "—"}</td>
                      <td className="py-3 px-4">
                        {c.status === "PERPETUELLE"
                          ? "Perpétuelle"
                          : c.expires_at
                          ? formatDate(c.expires_at)
                          : "—"}
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          className={`${statusColors[c.status] || "bg-gray-100 text-gray-800"} text-xs font-semibold px-2 py-1`}
                        >
                          {getStatusLabel(c.status)}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/concessions/${c.id}`)}
                        >
                          Détails
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
    </div>
  );
}
