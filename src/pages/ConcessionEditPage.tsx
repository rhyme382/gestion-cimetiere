import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Button, ErrorMessage, Input, Label, DataLoader } from "@/components/ui";
import { useConcession, useCemeteries, updateConcessionAsync, getErrorMessage } from "@/hooks";
import { listPlots } from "@/lib/tauri";
import { ArrowLeft } from "lucide-react";
import type { PlotDTO, UpdateConcessionRequest } from "@/types/bindings";

export default function ConcessionEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const concessionId = id ? Number(id) : null;

  const { data: concession, loading: concessionLoading, error: concessionError, refetch } = useConcession(concessionId);
  const { data: cemeteries = [], loading: cemeteriesLoading } = useCemeteries();

  const [plots, setPlots] = useState<PlotDTO[]>([]);
  const [plotsLoading, setPlotsLoading] = useState(false);

  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState<Partial<UpdateConcessionRequest>>({});

  useEffect(() => {
    if (concession) {
      setFormData({
        plot_id: concession.plot_id || undefined,
        concession_number: concession.concession_number || "",
        concession_type: concession.concession_type || "TEMPORAIRE",
        duration_years: concession.duration_years || undefined,
        start_date: concession.start_date || "",
        holder_first_name: concession.holder_first_name || "",
        holder_last_name: concession.holder_last_name || "",
        holder_address: concession.holder_address || "",
        holder_postal_code: concession.holder_postal_code || "",
        holder_commune: concession.holder_commune || "",
        observations: concession.observations || "",
      });
    }
  }, [concession]);

  useEffect(() => {
    if (!concession?.cemetery_id) {
      setPlots([]);
      return;
    }

    const loadPlots = async () => {
      setPlotsLoading(true);
      try {
        const plotsData = await listPlots(concession.cemetery_id);
        setPlots(plotsData || []);
      } catch (err) {
        setFormError(`Erreur lors du chargement des emplacements: ${getErrorMessage(err)}`);
      } finally {
        setPlotsLoading(false);
      }
    };

    loadPlots();
  }, [concession?.cemetery_id]);

  const handleInputChange = (field: string, value: string | number | null) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value === "" ? undefined : value,
    }));
    setFormError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      if (!concessionId) {
        throw new Error("ID de concession invalide");
      }

      if (formData.concession_type === "TEMPORAIRE" && !formData.duration_years) {
        throw new Error("La durée est obligatoire pour une concession temporaire");
      }

      let duration_years: number | undefined = formData.duration_years ? Number(formData.duration_years) : undefined;
      if (formData.concession_type === "TRENTENAIRE") {
        duration_years = 30;
      } else if (formData.concession_type === "CINQUANTENAIRE") {
        duration_years = 50;
      }

      const request: UpdateConcessionRequest = {
        plot_id: formData.plot_id ? Number(formData.plot_id) : undefined,
        concession_number: formData.concession_number || undefined,
        concession_type: formData.concession_type || undefined,
        duration_years,
        start_date: formData.start_date || undefined,
        holder_first_name: formData.holder_first_name || undefined,
        holder_last_name: formData.holder_last_name || undefined,
        holder_address: formData.holder_address || undefined,
        holder_postal_code: formData.holder_postal_code || undefined,
        holder_commune: formData.holder_commune || undefined,
        observations: formData.observations || undefined,
      };

      await updateConcessionAsync(concessionId, request);
      navigate(`/concessions/${concessionId}`);
    } catch (err) {
      const message = getErrorMessage(err);
      setFormError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

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

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-bold">Éditer la concession</h1>
      </div>

      {formError && <ErrorMessage error={formError} />}

      <DataLoader
        loading={concessionLoading}
        error={concessionError}
        data={concession}
        onRetry={refetch}
      >
        {concession && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Informations générales</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Cimetière (read-only) */}
                  <div>
                    <Label>Cimetière</Label>
                    <div className="mt-1 px-3 py-2 bg-muted rounded-md text-sm">
                      {cemeteries.find((c) => c.id === concession.cemetery_id)?.name || `#${concession.cemetery_id}`}
                    </div>
                  </div>

                  {/* Plot */}
                  <div>
                    <Label htmlFor="plot_id">Emplacement</Label>
                    <select
                      id="plot_id"
                      value={formData.plot_id || ""}
                      onChange={(e) => handleInputChange("plot_id", e.target.value ? Number(e.target.value) : null)}
                      disabled={plotsLoading}
                      className="w-full mt-1 px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                    >
                      <option value="">Sélectionner un emplacement</option>
                      {plots.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.section} • {p.row} • {p.number}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Concession Number */}
                  <div>
                    <Label htmlFor="concession_number">N° Concession</Label>
                    <Input
                      id="concession_number"
                      type="text"
                      placeholder="Ex: A-001"
                      value={formData.concession_number || ""}
                      onChange={(e) => handleInputChange("concession_number", e.target.value)}
                      className="mt-1"
                    />
                  </div>

                  {/* Concession Type */}
                  <div>
                    <Label htmlFor="concession_type">Type</Label>
                    <select
                      id="concession_type"
                      value={formData.concession_type || ""}
                      onChange={(e) => handleInputChange("concession_type", e.target.value)}
                      className="w-full mt-1 px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value="TEMPORAIRE">Temporaire</option>
                      <option value="TRENTENAIRE">30 ans</option>
                      <option value="CINQUANTENAIRE">50 ans</option>
                      <option value="PERPETUELLE">Perpétuelle</option>
                    </select>
                  </div>

                  {/* Duration Years */}
                  {formData.concession_type === "TEMPORAIRE" && (
                    <div>
                      <Label htmlFor="duration_years">Durée (années)</Label>
                      <Input
                        id="duration_years"
                        type="number"
                        placeholder="Ex: 15"
                        min="1"
                        max="99"
                        value={formData.duration_years || ""}
                        onChange={(e) => handleInputChange("duration_years", e.target.value ? Number(e.target.value) : null)}
                        className="mt-1"
                      />
                    </div>
                  )}
                  {formData.concession_type === "TRENTENAIRE" && (
                    <div>
                      <Label>Durée</Label>
                      <div className="mt-1 px-3 py-2 bg-muted rounded-md text-sm">
                        30 ans
                      </div>
                    </div>
                  )}
                  {formData.concession_type === "CINQUANTENAIRE" && (
                    <div>
                      <Label>Durée</Label>
                      <div className="mt-1 px-3 py-2 bg-muted rounded-md text-sm">
                        50 ans
                      </div>
                    </div>
                  )}

                  {/* Start Date */}
                  <div>
                    <Label htmlFor="start_date">Date de début</Label>
                    <Input
                      id="start_date"
                      type="date"
                      value={formData.start_date || ""}
                      onChange={(e) => handleInputChange("start_date", e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>

                {/* Concessionnaire Section */}
                <div className="border-t pt-6">
                  <h3 className="font-semibold text-sm mb-4">Concessionnaire</h3>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="holder_first_name">Prénom</Label>
                      <Input
                        id="holder_first_name"
                        type="text"
                        placeholder="Prénom"
                        value={formData.holder_first_name || ""}
                        onChange={(e) => handleInputChange("holder_first_name", e.target.value)}
                        className="mt-1"
                      />
                    </div>

                    <div>
                      <Label htmlFor="holder_last_name">Nom</Label>
                      <Input
                        id="holder_last_name"
                        type="text"
                        placeholder="Nom"
                        value={formData.holder_last_name || ""}
                        onChange={(e) => handleInputChange("holder_last_name", e.target.value)}
                        className="mt-1"
                      />
                    </div>

                    <div className="lg:col-span-2">
                      <Label htmlFor="holder_address">Adresse</Label>
                      <Input
                        id="holder_address"
                        type="text"
                        placeholder="Adresse"
                        value={formData.holder_address || ""}
                        onChange={(e) => handleInputChange("holder_address", e.target.value)}
                        className="mt-1"
                      />
                    </div>

                    <div>
                      <Label htmlFor="holder_postal_code">Code postal</Label>
                      <Input
                        id="holder_postal_code"
                        type="text"
                        placeholder="Code postal"
                        value={formData.holder_postal_code || ""}
                        onChange={(e) => handleInputChange("holder_postal_code", e.target.value)}
                        className="mt-1"
                      />
                    </div>

                    <div>
                      <Label htmlFor="holder_commune">Commune</Label>
                      <Input
                        id="holder_commune"
                        type="text"
                        placeholder="Commune"
                        value={formData.holder_commune || ""}
                        onChange={(e) => handleInputChange("holder_commune", e.target.value)}
                        className="mt-1"
                      />
                    </div>
                  </div>
                </div>

                {/* Observations */}
                <div className="border-t pt-6">
                  <Label htmlFor="observations">Observations</Label>
                  <textarea
                    id="observations"
                    placeholder="Observations"
                    value={formData.observations || ""}
                    onChange={(e) => handleInputChange("observations", e.target.value)}
                    className="w-full mt-1 px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    rows={4}
                  />
                </div>

                {/* Form Actions */}
                <div className="flex gap-2 justify-end border-t pt-6">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => navigate(-1)}
                    disabled={isSubmitting}
                  >
                    Annuler
                  </Button>
                  <Button
                    type="submit"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "Mise à jour en cours..." : "Mettre à jour"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}
      </DataLoader>
    </div>
  );
}
