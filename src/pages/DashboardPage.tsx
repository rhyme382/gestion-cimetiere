import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataLoader } from "@/components/ui";
import { useCemeteries, useConcessions, useIndividuals } from "@/hooks";
import { Building2, FileText, Users, Bell } from "lucide-react";
import { AlertWidget } from "@/components/alerts/AlertWidget";

export default function DashboardPage() {
  const { data: cemeteries, loading: cemLoading } = useCemeteries();
  const { data: concessions, loading: conLoading, error: conError } = useConcessions();
  const { data: individuals, loading: indLoading } = useIndividuals();

  const stats = [
    { label: "Cimetières", value: cemLoading ? "..." : cemeteries?.length ?? 0, icon: Building2, color: "text-blue-600" },
    { label: "Concessions", value: conLoading ? "..." : concessions?.length ?? 0, icon: FileText, color: "text-green-600" },
    { label: "Défunts/Personnes", value: indLoading ? "..." : individuals?.length ?? 0, icon: Users, color: "text-purple-600" },
    { label: "Alertes actives", value: "—", icon: Bell, color: "text-orange-600" },
  ];

  const recentConcessions = concessions?.slice(0, 5) ?? [];

  return (
    <div className="space-y-6">
      {/* Alerts Widget */}
      <div className="mb-4">
        <AlertWidget />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
              <Icon className={`h-4 w-4 ${color}`} />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Concessions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Concessions récentes</CardTitle>
        </CardHeader>
        <CardContent>
          <DataLoader
            loading={conLoading}
            error={conError}
            data={recentConcessions}
            emptyState={{
              icon: <FileText className="h-8 w-8" />,
              title: "Aucune concession",
              description: "Créez une première concession pour la voir ici",
            }}
          >
            <div className="space-y-3">
              {recentConcessions.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between p-3 border rounded hover:bg-accent transition"
                >
                  <div>
                    <p className="text-sm font-medium">Concession {c.id}</p>
                    <p className="text-xs text-muted-foreground">
                      Cimetière {c.cemetery_id} • Statut: {c.status}
                    </p>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {new Date(c.created_at).toLocaleDateString("fr-FR")}
                  </div>
                </div>
              ))}
            </div>
          </DataLoader>
        </CardContent>
      </Card>
    </div>
  );
}
