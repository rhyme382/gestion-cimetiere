import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button, Input, Label, ErrorMessage } from "@/components/ui";
import { CheckCircle } from "lucide-react";
import type { CemeteryDTO, CreateCemeteryRequest, UpdateCemeteryRequest } from "@/types/bindings";

export interface CemeteryFormProps {
  cemetery?: CemeteryDTO | null;
  onSubmit: (data: CreateCemeteryRequest | UpdateCemeteryRequest) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
  showSuccess?: boolean;
}

export function CemeteryForm({
  cemetery,
  onSubmit,
  onCancel,
  isSubmitting = false,
  showSuccess = false,
}: CemeteryFormProps) {
  const [formData, setFormData] = useState<Partial<CemeteryDTO & CreateCemeteryRequest>>({
    name: "",
    address: "",
    commune: "",
    capacity: undefined,
    is_active: 1,
  });

  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | null>>({});

  useEffect(() => {
    if (cemetery) {
      setFormData({
        name: cemetery.name || "",
        address: cemetery.address || "",
        commune: cemetery.commune || "",
        capacity: cemetery.capacity || undefined,
        is_active: cemetery.is_active,
      });
    }
  }, [cemetery]);

  const handleInputChange = (field: string, value: string | number | null) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value === "" || value === null ? undefined : value,
    }));
    setFormError(null);
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
      errors.name = "Le nom du cimetière est obligatoire";
    }

    if (formData.capacity !== undefined && formData.capacity < 0) {
      errors.capacity = "La capacité doit être un nombre positif";
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setFormError(null);
      return;
    }

    try {
      const request: CreateCemeteryRequest | UpdateCemeteryRequest = {
        name: formData.name,
        address: formData.address || undefined,
        commune: formData.commune || undefined,
        capacity: formData.capacity ? Math.floor(formData.capacity) : undefined,
        is_active: formData.is_active,
      };

      await onSubmit(request);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setFormError(message);
    }
  };

  const isActive = formData.is_active === 1;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {cemetery ? "Modifier le cimetière" : "Créer un cimetière"}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {formError && <ErrorMessage error={formError} />}

        {showSuccess && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md flex items-start gap-3">
            <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
            <p className="text-sm text-green-600">
              {cemetery ? "Cimetière modifié avec succès" : "Cimetière créé avec succès"}
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <Label htmlFor="cemetery-name">
              Nom du cimetière
              <span className="text-red-600 ml-1">*</span>
            </Label>
            <Input
              id="cemetery-name"
              type="text"
              placeholder="Ex: Cimetière du Nord"
              value={formData.name || ""}
              onChange={(e) => handleInputChange("name", e.target.value)}
              disabled={isSubmitting}
              className="mt-1"
              aria-invalid={!!fieldErrors.name}
              aria-describedby={fieldErrors.name ? "name-error" : undefined}
            />
            {fieldErrors.name && (
              <p id="name-error" className="text-xs text-red-600 mt-1">{fieldErrors.name}</p>
            )}
          </div>

          {/* Address */}
          <div>
            <Label htmlFor="cemetery-address">Adresse</Label>
            <Input
              id="cemetery-address"
              type="text"
              placeholder="Ex: 123 Avenue de la Paix"
              value={formData.address || ""}
              onChange={(e) => handleInputChange("address", e.target.value)}
              disabled={isSubmitting}
              className="mt-1"
            />
          </div>

          {/* Commune */}
          <div>
            <Label htmlFor="cemetery-commune">Commune</Label>
            <Input
              id="cemetery-commune"
              type="text"
              placeholder="Ex: Paris"
              value={formData.commune || ""}
              onChange={(e) => handleInputChange("commune", e.target.value)}
              disabled={isSubmitting}
              className="mt-1"
            />
          </div>

          {/* Capacity */}
          <div>
            <Label htmlFor="cemetery-capacity">Capacité</Label>
            <Input
              id="cemetery-capacity"
              type="number"
              placeholder="Ex: 500"
              value={formData.capacity ?? ""}
              onChange={(e) => handleInputChange("capacity", e.target.value ? parseInt(e.target.value, 10) : null)}
              disabled={isSubmitting}
              className="mt-1"
              min="0"
              aria-invalid={!!fieldErrors.capacity}
              aria-describedby={fieldErrors.capacity ? "capacity-error" : undefined}
            />
            {fieldErrors.capacity && (
              <p id="capacity-error" className="text-xs text-red-600 mt-1">{fieldErrors.capacity}</p>
            )}
          </div>

          {/* Status */}
          <div>
            <div className="flex items-center gap-2">
              <input
                id="cemetery-active"
                type="checkbox"
                checked={isActive}
                onChange={(e) => handleInputChange("is_active", e.target.checked ? 1 : 0)}
                disabled={isSubmitting}
                className="rounded border-gray-300"
              />
              <Label htmlFor="cemetery-active" className="cursor-pointer">
                Cimetière actif
              </Label>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 justify-end pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Annuler
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Enregistrement..." : cemetery ? "Modifier" : "Créer"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
