import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Badge, Button, DataLoader, ErrorMessage } from "@/components/ui";
import { useConcessions } from "@/hooks";
import { FileText } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function ConcessionsPage() {
  const navigate = useNavigate();
  const { data: concessions, loading, error, refetch } = useConcessions();
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);

  const filteredConcessions = selectedStatus
    ? concessions?.filter((c) => c.status === selectedStatus)
    : concessions;

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
      {/* Filters */}
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
          {["active", "expiring_soon", "expired", "renewed", "abandoned", "reclaimed", "archived"].map((status) => (
            <Button
              key={status}
              variant={selectedStatus === status ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedStatus(status)}
            >
              {status === "active" && "Actif"}
              {status === "expiring_soon" && "Expirant bientôt"}
              {status === "expired" && "Expiré"}
              {status === "renewed" && "Renouvelé"}
              {status === "abandoned" && "Abandonné"}
              {status === "reclaimed" && "Repris"}
              {status === "archived" && "Archivé"}
            </Button>
          ))}
        </CardContent>
      </Card>

      {/* List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Concessions</CardTitle>
            {error && <ErrorMessage error={error} onRetry={refetch} />}
          </div>
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
              description: "Créez une première concession pour la voir ici",
            }}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">ID</th>
                    <th className="text-left py-3 px-4">Cimetière</th>
                    <th className="text-left py-3 px-4">Statut</th>
                    <th className="text-left py-3 px-4">Acquise le</th>
                    <th className="text-left py-3 px-4">Expire le</th>
                    <th className="text-left py-3 px-4"></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredConcessions?.map((c) => (
                    <tr key={c.id} className="border-b hover:bg-accent transition">
                      <td className="py-3 px-4 font-medium">{c.id}</td>
                      <td className="py-3 px-4">{c.cemetery_id}</td>
                      <td className="py-3 px-4">
                        <Badge
                          className={`${statusColors[c.status]} text-xs font-semibold px-2 py-1`}
                        >
                          {c.status === "active" && "Actif"}
                          {c.status === "expiring_soon" && "Expirant"}
                          {c.status === "expired" && "Expiré"}
                          {c.status === "renewed" && "Renouvelé"}
                          {c.status === "abandoned" && "Abandonné"}
                          {c.status === "reclaimed" && "Repris"}
                          {c.status === "archived" && "Archivé"}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{c.acquired_at ? formatDate(c.acquired_at) : "—"}</td>
                      <td className="py-3 px-4">{c.expires_at ? formatDate(c.expires_at) : "—"}</td>
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
