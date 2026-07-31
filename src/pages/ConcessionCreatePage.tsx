import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, Button, ErrorMessage, Input, Label } from "@/components/ui";
import { useCemeteries, createConcessionAsync, getErrorMessage } from "@/hooks";
import { listPlots } from "@/lib/tauri";
import { ArrowLeft } from "lucide-react";
import type { PlotDTO, CreateConcessionRequest } from "@/types/bindings";

export default function ConcessionCreatePage() {
  const navigate = useNavigate();
  const {
    data: cemeteriesData,
    loading: cemeteriesLoading,
  } = useCemeteries();

  const cemeteries = cemeteriesData ?? [];

  const [plots, setPlots] = useState<PlotDTO[]>([]);
  const [plotsLoading, setPlotsLoading] = useState(false);

  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState<Partial<CreateConcessionRequest>>({
    cemetery_id: undefined,
    plot_id: undefined,
    concession_number: "",
    concession_type: "TEMPORAIRE",
    duration_years: undefined,
    start_date: "",
    holder_first_name: "",
    holder_last_name: "",
    holder_address: "",
    holder_postal_code: "",
    holder_commune: "",
    observations: "",
  });

  useEffect(() => {
    if (!formData.cemetery_id) {
      setPlots([]);
      return;
    }

    const loadPlots = async () => {
      setPlotsLoading(true);
      try {
        const plotsData = await listPlots(formData.cemetery_id!);
        setPlots(plotsData || []);
      } catch (err) {
        setFormError(`Erreur lors du chargement des emplacements: ${getErrorMessage(err)}`);
      } finally {
        setPlotsLoading(false);
      }
    };

    loadPlots();
  }, [formData.cemetery_id]);

  const handleInputChange = (field: string, value: string | number) => {
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
      if (!formData.cemetery_id || !formData.plot_id || !formData.concession_number || !formData.concession_type) {
        throw new Error("Veuillez remplir tous les champs obligatoires");
      }

      if (!formData.start_date?.trim()) {
        throw new Error("La date de début est obligatoire");
      }

      if (!formData.holder_last_name?.trim()) {
        throw new Error("Le nom du concessionnaire est obligatoire");
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

      const request: CreateConcessionRequest = {
        cemetery_id: formData.cemetery_id,
        plot_id: formData.plot_id,
        concession_number: formData.concession_number,
        concession_type: formData.concession_type,
        duration_years,
        start_date: formData.start_date || undefined,
        holder_first_name: formData.holder_first_name || undefined,
        holder_last_name: formData.holder_last_name || undefined,
        holder_address: formData.holder_address || undefined,
        holder_postal_code: formData.holder_postal_code || undefined,
        holder_commune: formData.holder_commune || undefined,
        observations: formData.observations || undefined,
      };

      const created = await createConcessionAsync(request);
      navigate(`/concessions/${created.id}`);
    } catch (err) {
      const message = getErrorMessage(err);
      setFormError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-2xl font-bold">Créer une concession</h1>
      </div>

      {formError && <ErrorMessage error={formError} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Informations générales</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Cemetery */}
              <div>
                <Label htmlFor="cemetery_id">Cimetière *</Label>
                <select
                  id="cemetery_id"
                  value={formData.cemetery_id || ""}
                  onChange={(e) => handleInputChange("cemetery_id", Number(e.target.value))}
                  disabled={cemeteriesLoading}
                  className="w-full mt-1 px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                >
                  <option value="">Sélectionner un cimetière</option>
                  {cemeteries.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Plot */}
              <div>
                <Label htmlFor="plot_id">Emplacement *</Label>
                <select
                  id="plot_id"
                  value={formData.plot_id || ""}
                  onChange={(e) => handleInputChange("plot_id", Number(e.target.value))}
                  disabled={!formData.cemetery_id || plotsLoading}
                  className="w-full mt-1 px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                >
                  <option value="">
                    {!formData.cemetery_id
                      ? "Sélectionner un cimetière d'abord"
                      : plotsLoading
                      ? "Chargement..."
                      : "Sélectionner un emplacement"}
                  </option>
                  {plots.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.section} • {p.row} • {p.number}
                    </option>
                  ))}
                </select>
              </div>

              {/* Concession Number */}
              <div>
                <Label htmlFor="concession_number">N° Concession *</Label>
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
                <Label htmlFor="concession_type">Type *</Label>
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
                  <Label htmlFor="duration_years">Durée (années) *</Label>
                  <Input
                    id="duration_years"
                    type="number"
                    placeholder="Ex: 15"
                    min="1"
                    max="99"
                    value={formData.duration_years || ""}
                    onChange={(e) => handleInputChange("duration_years", e.target.value ? Number(e.target.value) : "")}
                    className="mt-1"
                  />
                </div>
              )}
              {formData.concession_type === "TRENTENAIRE" && (
                <div>
                  <Label htmlFor="duration_years">Durée</Label>
                  <div className="mt-1 px-3 py-2 bg-muted rounded-md text-sm">
                    30 ans
                  </div>
                </div>
              )}
              {formData.concession_type === "CINQUANTENAIRE" && (
                <div>
                  <Label htmlFor="duration_years">Durée</Label>
                  <div className="mt-1 px-3 py-2 bg-muted rounded-md text-sm">
                    50 ans
                  </div>
                </div>
              )}

              {/* Start Date */}
              <div>
                <Label htmlFor="start_date">Date de début *</Label>
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
                {isSubmitting ? "Création en cours..." : "Créer"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
