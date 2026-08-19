import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, Badge, Button, DataLoader, Input } from "@/components/ui";
import { CemeteryForm } from "@/components/forms/CemeteryForm";
import { useCemeteries, createCemeteryAsync, updateCemeteryAsync } from "@/hooks";
import { Building2, Plus, Search, Edit2, Eye } from "lucide-react";
import { formatDate } from "@/lib/utils";
import type { CemeteryDTO, CreateCemeteryRequest, UpdateCemeteryRequest } from "@/types/bindings";

const EMPTY_CEMETERIES: CemeteryDTO[] = [];

type FormMode = "create" | "edit" | null;

export default function CemeteriesPage() {
  const { data: cemeteries, loading, error, refetch } = useCemeteries();
  const displayData = cemeteries ?? EMPTY_CEMETERIES;

  const [formMode, setFormMode] = useState<FormMode>(null);
  const [selectedCemetery, setSelectedCemetery] = useState<CemeteryDTO | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [detailView, setDetailView] = useState<CemeteryDTO | null>(null);

  const filteredCemeteries = useMemo(() => {
    let results = displayData;

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      results = results.filter((c) =>
        c.name.toLowerCase().includes(query) ||
        c.commune?.toLowerCase().includes(query) ||
        c.address?.toLowerCase().includes(query)
      );
    }

    return results;
  }, [displayData, searchQuery]);

  const handleCreateClick = () => {
    setSelectedCemetery(null);
    setFormMode("create");
    setShowSuccess(false);
  };

  const handleEditClick = (cemetery: CemeteryDTO) => {
    setSelectedCemetery(cemetery);
    setFormMode("edit");
    setShowSuccess(false);
  };

  const handleViewClick = (cemetery: CemeteryDTO) => {
    setDetailView(cemetery);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedCemetery(null);
    setShowSuccess(false);
  };

  const handleFormSubmit = async (data: CreateCemeteryRequest | UpdateCemeteryRequest) => {
    setIsSubmitting(true);
    try {
      if (formMode === "create") {
        await createCemeteryAsync(data as CreateCemeteryRequest);
      } else if (formMode === "edit" && selectedCemetery) {
        await updateCemeteryAsync(selectedCemetery.id, data as UpdateCemeteryRequest);
      }

      setShowSuccess(true);
      setFormMode(null);
      setSelectedCemetery(null);

      refetch();

      setTimeout(() => {
        setShowSuccess(false);
      }, 1500);
    } catch (err) {
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-2xl font-bold">Cimetières</h1>
        </div>
        <p className="text-sm text-muted-foreground">Gestion des cimetières de la commune</p>
      </div>

      {/* Form Mode */}
      {formMode && (
        <CemeteryForm
          cemetery={selectedCemetery}
          onSubmit={handleFormSubmit}
          onCancel={handleFormCancel}
          isSubmitting={isSubmitting}
          showSuccess={showSuccess}
        />
      )}

      {/* Detail View */}
      {detailView && !formMode && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base">Détails du cimetière</CardTitle>
            <button
              onClick={() => setDetailView(null)}
              className="p-1 hover:bg-gray-100 rounded"
              aria-label="Fermer"
            >
              <Eye className="h-4 w-4" />
            </button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs text-muted-foreground">Nom</p>
              <p className="text-sm font-medium">{detailView.name}</p>
            </div>
            {detailView.address && (
              <div>
                <p className="text-xs text-muted-foreground">Adresse</p>
                <p className="text-sm font-medium">{detailView.address}</p>
              </div>
            )}
            {detailView.commune && (
              <div>
                <p className="text-xs text-muted-foreground">Commune</p>
                <p className="text-sm font-medium">{detailView.commune}</p>
              </div>
            )}
            {detailView.capacity && (
              <div>
                <p className="text-xs text-muted-foreground">Capacité</p>
                <p className="text-sm font-medium">{detailView.capacity}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-muted-foreground">Statut</p>
              <div className="mt-1">
                <Badge variant={detailView.is_active === 1 ? "success" : "muted"}>
                  {detailView.is_active === 1 ? "Actif" : "Inactif"}
                </Badge>
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Dates</p>
              <p className="text-xs text-gray-600">
                Créé: {formatDate(detailView.created_at)}
              </p>
              <p className="text-xs text-gray-600">
                Modifié: {formatDate(detailView.updated_at)}
              </p>
            </div>
            <div className="flex gap-2 pt-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setDetailView(null);
                  handleEditClick(detailView);
                }}
              >
                <Edit2 className="h-4 w-4 mr-2" />
                Modifier
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setDetailView(null)}
              >
                Fermer
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search */}
      {!formMode && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Search className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              <Input
                type="text"
                placeholder="Rechercher par nom, adresse ou commune..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create Button */}
      {!formMode && (
        <Button onClick={handleCreateClick} className="gap-2">
          <Plus className="h-4 w-4" />
          Ajouter un cimetière
        </Button>
      )}

      {/* List */}
      {!formMode && (
        <DataLoader
          loading={loading}
          error={error}
          data={displayData}
          onRetry={refetch}
          emptyState={{
            icon: <Building2 className="h-12 w-12" />,
            title: "Aucun cimetière",
            description: "Créez votre premier cimetière pour commencer",
          }}
        >
          <div className="space-y-2">
            {filteredCemeteries.map((cemetery) => (
              <Card key={cemetery.id} className={cemetery.is_active === 0 ? "opacity-60" : ""}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <p className="font-medium text-sm truncate">{cemetery.name}</p>
                        <Badge variant={cemetery.is_active === 1 ? "success" : "muted"}>
                          {cemetery.is_active === 1 ? "Actif" : "Inactif"}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground space-y-1">
                        {cemetery.address && (
                          <p>📍 {cemetery.address}</p>
                        )}
                        {cemetery.commune && (
                          <p>🏘️ {cemetery.commune}</p>
                        )}
                        {cemetery.capacity && (
                          <p>📊 Capacité: {cemetery.capacity}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 flex-shrink-0">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleViewClick(cemetery)}
                        title="Voir les détails"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleEditClick(cemetery)}
                        title="Modifier"
                      >
                        <Edit2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </DataLoader>
      )}
    </div>
  );
}
