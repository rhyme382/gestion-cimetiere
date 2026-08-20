import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CemeteryForm } from "@/components/forms/CemeteryForm";
import type { CemeteryDTO } from "@/types/bindings";

const mockCemetery: CemeteryDTO = {
  id: 1,
  name: "Cimetière du Nord",
  address: "123 Avenue de la Paix",
  commune: "Paris",
  capacity: 500,
  municipality_id: 1,
  is_active: 1,
  created_at: "2020-01-01T00:00:00Z",
  updated_at: "2020-01-01T00:00:00Z",
};

describe("CemeteryForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le titre créer pour un nouveau cimetière", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    expect(screen.getByText("Créer un cimetière")).toBeInTheDocument();
  });

  it("affiche le titre modifier pour un cimetière existant", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        cemetery={mockCemetery}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    expect(screen.getByText("Modifier le cimetière")).toBeInTheDocument();
  });

  it("pré-remplit les champs avec les données du cimetière", async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        cemetery={mockCemetery}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    await waitFor(() => {
      expect((screen.getByDisplayValue("Cimetière du Nord") as HTMLInputElement).value).toBe("Cimetière du Nord");
      expect((screen.getByDisplayValue("123 Avenue de la Paix") as HTMLInputElement).value).toBe("123 Avenue de la Paix");
      expect((screen.getByDisplayValue("Paris") as HTMLInputElement).value).toBe("Paris");
      expect((screen.getByDisplayValue("500") as HTMLInputElement).value).toBe("500");
    });
  });

  it("valide que le nom est obligatoire", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    const submitButton = screen.getByRole("button", { name: /Créer/ });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Le nom du cimetière est obligatoire")).toBeInTheDocument();
    });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("accepte une capacité valide", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    const nameInput = screen.getByPlaceholderText("Ex: Cimetière du Nord");
    const capacityInput = screen.getByPlaceholderText("Ex: 500");

    await user.type(nameInput, "Test Cemetery");
    await user.type(capacityInput, "500");

    const submitButton = screen.getByRole("button", { name: /Créer/ });
    await user.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          capacity: 500,
        })
      );
    });
  });

  it("soumet le formulaire avec les données valides", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    const nameInput = screen.getByPlaceholderText("Ex: Cimetière du Nord");
    const addressInput = screen.getByPlaceholderText("Ex: 123 Avenue de la Paix");
    const communeInput = screen.getByPlaceholderText("Ex: Paris");
    const capacityInput = screen.getByPlaceholderText("Ex: 500");

    await user.type(nameInput, "Nouveau Cimetière");
    await user.type(addressInput, "456 Rue de Lyon");
    await user.type(communeInput, "Marseille");
    await user.type(capacityInput, "300");

    const submitButton = screen.getByRole("button", { name: /Créer/ });
    await user.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Nouveau Cimetière",
          address: "456 Rue de Lyon",
          commune: "Marseille",
          capacity: 300,
          is_active: 1,
        })
      );
    });
  });

  it("appelle onCancel au clic sur annuler", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    const cancelButton = screen.getByRole("button", { name: /Annuler/ });
    await user.click(cancelButton);

    expect(onCancel).toHaveBeenCalled();
  });

  it("désactive le formulaire pendant la soumission", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));
    const onCancel = vi.fn();

    const { rerender } = render(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
        isSubmitting={false}
      />
    );

    const nameInput = screen.getByPlaceholderText("Ex: Cimetière du Nord");
    await user.type(nameInput, "Test");

    rerender(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
        isSubmitting={true}
      />
    );

    expect(screen.getByDisplayValue("Test")).toBeDisabled();
  });

  it("bascule l'état actif du cimetière", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        cemetery={mockCemetery}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    const activeCheckbox = screen.getByRole("checkbox", { name: /Cimetière actif/ }) as HTMLInputElement;
    expect(activeCheckbox.checked).toBe(true);

    await user.click(activeCheckbox);
    expect(activeCheckbox.checked).toBe(false);

    const nameInput = screen.getByPlaceholderText("Ex: Cimetière du Nord");
    const submitButton = screen.getByRole("button", { name: /Modifier/ });

    await user.click(submitButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          is_active: 0,
        })
      );
    });
  });

  it("affiche le message de succès", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
        showSuccess={true}
      />
    );

    expect(screen.getByText("Cimetière créé avec succès")).toBeInTheDocument();
  });

  it("affiche un message de succès différent pour la modification", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        cemetery={mockCemetery}
        onSubmit={onSubmit}
        onCancel={onCancel}
        showSuccess={true}
      />
    );

    expect(screen.getByText("Cimetière modifié avec succès")).toBeInTheDocument();
  });

  it("marque le champ nom comme obligatoire", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    const nameLabel = screen.getByText("Nom du cimetière").closest("label");
    expect(nameLabel?.textContent).toContain("*");
  });

  it("réinitialise les erreurs au saisie", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue(new Error("Erreur réseau"));
    const onCancel = vi.fn();

    render(
      <CemeteryForm
        onSubmit={onSubmit}
        onCancel={onCancel}
      />
    );

    const submitButton = screen.getByRole("button", { name: /Créer/ });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Le nom du cimetière est obligatoire")).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText("Ex: Cimetière du Nord");
    await user.type(nameInput, "Test");

    await waitFor(() => {
      expect(screen.queryByText("Le nom du cimetière est obligatoire")).not.toBeInTheDocument();
    });
  });
});
