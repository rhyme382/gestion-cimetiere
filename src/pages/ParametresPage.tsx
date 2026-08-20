import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button, ErrorMessage, Input, Label } from "@/components/ui";
import { DiagnosticCard } from "@/components/DiagnosticCard";
import { Settings, CheckCircle } from "lucide-react";
import { useMunicipalities, updateMunicipalityAsync, createMunicipalityAsync, getErrorMessage } from "@/hooks";
import type { MunicipalityDTO, UpdateMunicipalityRequest, CreateMunicipalityRequest } from "@/types/bindings";

export default function ParametresPage() {
  const { data: municipalities, loading: municipalitiesLoading, error: loadError } = useMunicipalities();

  const municipality = municipalities?.[0] || null;

  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | null>>({
    name: null,
    insee_code: null,
    email: null,
  });
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState<Partial<MunicipalityDTO & CreateMunicipalityRequest>>({
    name: "",
    insee_code: "",
    postal_code: "",
    email: "",
    department: "",
    region: "",
    notes: "",
  });

  useEffect(() => {
    if (municipality) {
      setFormData({
        id: municipality.id,
        name: municipality.name || "",
        insee_code: municipality.insee_code || "",
        postal_code: municipality.postal_code || "",
        email: municipality.email || "",
        department: municipality.department || "",
        region: municipality.region || "",
        notes: municipality.notes || "",
      });
    }
  }, [municipality]);

  const validateEmail = (email: string): boolean => {
    if (!email) return true;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value === "" ? null : value,
    }));
    setFormError(null);
    setFormSuccess(null);
    setFieldErrors((prev) => {
      const updated = { ...prev };
      delete updated[field];
      return updated;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const errors: Record<string, string> = {};

    if (!formData.name?.trim()) {
      errors.name = "Le nom de la commune est obligatoire";
    }

    if (!formData.insee_code?.trim()) {
      errors.insee_code = "Le code INSEE est obligatoire";
    }

    if (formData.email && !validateEmail(formData.email)) {
      errors.email = "L'adresse e-mail n'est pas valide";
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setFormError(null);
      setFormSuccess(null);
      return;
    }

    setIsSubmitting(true);
    setFieldErrors({});
    setFormError(null);
    setFormSuccess(null);

    try {
      const request: UpdateMunicipalityRequest | CreateMunicipalityRequest = {
        name: formData.name,
        insee_code: formData.insee_code,
        postal_code: formData.postal_code || undefined,
        email: formData.email || undefined,
        department: formData.department || undefined,
        region: formData.region || undefined,
        notes: formData.notes || undefined,
      };

      if (municipality) {
        await updateMunicipalityAsync(municipality.id, request as UpdateMunicipalityRequest);
        setFormSuccess("Configuration communale mise à jour avec succès");
      } else {
        const created = await createMunicipalityAsync(request as CreateMunicipalityRequest);
        setFormData({
          ...formData,
          id: created.id,
          created_at: created.created_at,
          updated_at: created.updated_at,
        });
        setFormSuccess("Configuration communale créée avec succès");
      }
    } catch (err) {
      const message = getErrorMessage(err);
      setFormError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 max-w-2xl">
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Settings className="h-5 w-5 text-muted-foreground" />
          <h1 className="text-2xl font-bold">Paramètres de l'application</h1>
        </div>
        <p className="text-sm text-muted-foreground">Configuration communale et paramètres généraux</p>
      </div>

      {formError && <ErrorMessage error={formError} />}
      {loadError && <ErrorMessage error={`Erreur lors du chargement de la configuration : ${getErrorMessage(loadError)}`} />}

      {formSuccess && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="flex items-start gap-3 py-4">
            <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-green-600">{formSuccess}</p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuration communale</CardTitle>
        </CardHeader>
        <CardContent>
          {municipalitiesLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : loadError ? (
            <div className="text-center py-8">
              <p className="text-sm text-muted-foreground">
                Impossible de charger la configuration de la commune.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Commune Name */}
                <div>
                  <Label htmlFor="name">
                    Nom de la commune
                    <span className="text-destructive ml-1" aria-label="obligatoire">*</span>
                  </Label>
                  <Input
                    id="name"
                    type="text"
                    placeholder="Ex: Saint-Martin"
                    value={formData.name || ""}
                    onChange={(e) => handleInputChange("name", e.target.value)}
                    disabled={isSubmitting}
                    className="mt-1"
                    required
                    aria-invalid={!!fieldErrors.name}
                    aria-describedby={fieldErrors.name ? "name-error" : undefined}
                  />
                  {fieldErrors.name && (
                    <p id="name-error" className="text-xs text-destructive mt-1">{fieldErrors.name}</p>
                  )}
                </div>

                {/* INSEE Code */}
                <div>
                  <Label htmlFor="insee_code">
                    Code INSEE
                    <span className="text-destructive ml-1" aria-label="obligatoire">*</span>
                  </Label>
                  <Input
                    id="insee_code"
                    type="text"
                    placeholder="Ex: 75056"
                    value={formData.insee_code || ""}
                    onChange={(e) => handleInputChange("insee_code", e.target.value)}
                    disabled={isSubmitting}
                    className="mt-1"
                    required
                    aria-invalid={!!fieldErrors.insee_code}
                    aria-describedby={fieldErrors.insee_code ? "insee_code-error" : undefined}
                  />
                  {fieldErrors.insee_code && (
                    <p id="insee_code-error" className="text-xs text-destructive mt-1">{fieldErrors.insee_code}</p>
                  )}
                </div>

                {/* Postal Code */}
                <div>
                  <Label htmlFor="postal_code">Code postal</Label>
                  <Input
                    id="postal_code"
                    type="text"
                    placeholder="Ex: 75001"
                    value={formData.postal_code || ""}
                    onChange={(e) => handleInputChange("postal_code", e.target.value)}
                    disabled={isSubmitting}
                    className="mt-1"
                  />
                </div>

                {/* Email */}
                <div>
                  <Label htmlFor="email">Adresse e-mail</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="contact@commune.fr"
                    value={formData.email || ""}
                    onChange={(e) => handleInputChange("email", e.target.value)}
                    disabled={isSubmitting}
                    className="mt-1"
                    aria-invalid={!!fieldErrors.email || (formData.email && !validateEmail(formData.email))}
                    aria-describedby={fieldErrors.email || (formData.email && !validateEmail(formData.email)) ? "email-error" : undefined}
                  />
                  {(fieldErrors.email || (formData.email && !validateEmail(formData.email))) && (
                    <p id="email-error" className="text-xs text-destructive mt-1">{fieldErrors.email || "Format d'e-mail invalide"}</p>
                  )}
                </div>

                {/* Department */}
                <div>
                  <Label htmlFor="department">Département</Label>
                  <Input
                    id="department"
                    type="text"
                    placeholder="Ex: 75"
                    value={formData.department || ""}
                    onChange={(e) => handleInputChange("department", e.target.value)}
                    disabled={isSubmitting}
                    className="mt-1"
                  />
                </div>

                {/* Region */}
                <div>
                  <Label htmlFor="region">Région</Label>
                  <Input
                    id="region"
                    type="text"
                    placeholder="Ex: Île-de-France"
                    value={formData.region || ""}
                    onChange={(e) => handleInputChange("region", e.target.value)}
                    disabled={isSubmitting}
                    className="mt-1"
                  />
                </div>
              </div>

              {/* Notes */}
              <div className="border-t pt-6">
                <Label htmlFor="notes">Notes</Label>
                <textarea
                  id="notes"
                  placeholder="Notes ou observations supplémentaires"
                  value={formData.notes || ""}
                  onChange={(e) => handleInputChange("notes", e.target.value)}
                  disabled={isSubmitting}
                  className="w-full mt-1 px-3 py-2 border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                  rows={4}
                />
              </div>

              {/* Form Actions */}
              <div className="flex gap-2 justify-end border-t pt-6">
                <Button
                  type="submit"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Enregistrement..." : "Enregistrer"}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>

      <DiagnosticCard />
    </div>
  );
}
