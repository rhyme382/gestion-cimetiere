import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, DataLoader, ErrorMessage } from "@/components/ui";
import { useIndividual } from "@/hooks";
import { ArrowLeft, Mail, Phone } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function DefuntDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const individualId = id ? Number(id) : null;

  const { data: individual, loading, error, refetch } = useIndividual(individualId);

  if (!individualId) {
    return (
      <div className="space-y-4">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-sm text-muted-foreground">ID invalide</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const roleLabels: Record<string, string> = {
    deceased: "Défunt",
    concessionnaire: "Concessionnaire",
    heir: "Ayant droit",
    contact: "Contact",
  };

  const roleColors: Record<string, string> = {
    deceased: "bg-slate-100 text-slate-800",
    concessionnaire: "bg-blue-100 text-blue-800",
    heir: "bg-green-100 text-green-800",
    contact: "bg-orange-100 text-orange-800",
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-bold">Détails</h1>
      </div>

      {error && <ErrorMessage error={error} onRetry={refetch} />}

      {/* Details */}
      <DataLoader
        loading={loading}
        error={error}
        data={individual}
        onRetry={refetch}
      >
        {individual && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Main Info */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{individual.name}</CardTitle>
                  <Badge className={`${roleColors[individual.role]} text-xs font-semibold`}>
                    {roleLabels[individual.role]}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="border-b pb-4">
                  <h3 className="font-semibold text-sm mb-3">Informations de contact</h3>
                  <div className="space-y-2">
                    {individual.email && (
                      <div className="flex items-center gap-3">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <a href={`mailto:${individual.email}`} className="text-sm text-blue-600 hover:underline">
                          {individual.email}
                        </a>
                      </div>
                    )}
                    {individual.phone && (
                      <div className="flex items-center gap-3">
                        <Phone className="h-4 w-4 text-muted-foreground" />
                        <a href={`tel:${individual.phone}`} className="text-sm text-blue-600 hover:underline">
                          {individual.phone}
                        </a>
                      </div>
                    )}
                    {!individual.email && !individual.phone && (
                      <p className="text-sm text-muted-foreground">Aucune information de contact</p>
                    )}
                  </div>
                </div>

                <div className="border-b pb-4">
                  <h3 className="font-semibold text-sm mb-3">Audit</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Créé le</p>
                      <p className="text-xs mt-1">{formatDate(individual.created_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground font-medium">Modifié le</p>
                      <p className="text-xs mt-1">{formatDate(individual.updated_at)}</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-sm mb-3">ID</h3>
                  <p className="text-sm font-mono">{individual.id}</p>
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
                <Button
                  className="w-full"
                  variant="outline"
                  onClick={() => navigate("/emplacements")}
                >
                  Localiser sur la carte
                </Button>
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
