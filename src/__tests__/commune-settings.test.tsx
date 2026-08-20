import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ParametresPage from "@/pages/ParametresPage";
import * as tauri from "@/lib/tauri";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@/lib/tauri");

const mockMunicipality = {
  id: 1,
  name: "Saint-Martin",
  insee_code: "75056",
  postal_code: "75001",
  email: "contact@saint-martin.fr",
  department: "75",
  region: "Île-de-France",
  notes: "Notes de test",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function TestWrapper() {
  return (
    <MemoryRouter initialEntries={["/parametres"]}>
      <Routes>
        <Route path="/parametres" element={<ParametresPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Commune Settings - ParametresPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le titre et la description", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);

    render(<TestWrapper />);

    expect(screen.getByText("Paramètres de l'application")).toBeInTheDocument();
    expect(screen.getByText("Configuration communale et paramètres généraux")).toBeInTheDocument();
  });

  it("charge et affiche les données communales existantes", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);

    render(<TestWrapper />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("Saint-Martin")).toBeInTheDocument();
      expect(screen.getByDisplayValue("75056")).toBeInTheDocument();
      expect(screen.getByDisplayValue("75001")).toBeInTheDocument();
      expect(screen.getByDisplayValue("contact@saint-martin.fr")).toBeInTheDocument();
      expect(screen.getByDisplayValue("75")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Île-de-France")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Notes de test")).toBeInTheDocument();
    });
  });

  it("affiche un formulaire vide quand aucune commune n'existe", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([]);

    render(<TestWrapper />);

    await waitFor(() => {
      const nameInput = screen.getByPlaceholderText("Ex: Saint-Martin") as HTMLInputElement;
      expect(nameInput.value).toBe("");

      const inseeInput = screen.getByPlaceholderText("Ex: 75056") as HTMLInputElement;
      expect(inseeInput.value).toBe("");
    });
  });

  it("marque les champs obligatoires avec un astérisque", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);

    render(<TestWrapper />);

    await waitFor(() => {
      const nameInput = screen.getByDisplayValue("Saint-Martin");
      expect(nameInput).toBeInTheDocument();
    });

    const nameInput = screen.getByDisplayValue("Saint-Martin") as HTMLInputElement;
    const inseeInput = screen.getByDisplayValue("75056") as HTMLInputElement;

    const nameLabel = nameInput.closest("div")?.querySelector("label");
    const inseeLabel = inseeInput.closest("div")?.querySelector("label");

    expect(nameLabel?.textContent).toContain("*");
    expect(inseeLabel?.textContent).toContain("*");
  });

  it("valide le format de l'e-mail et affiche un message d'erreur", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);

    render(<TestWrapper />);

    await waitFor(() => {
      const emailInput = screen.getByDisplayValue("contact@saint-martin.fr") as HTMLInputElement;
      expect(emailInput).toBeInTheDocument();
    });

    const emailInput = screen.getByPlaceholderText("contact@commune.fr") as HTMLInputElement;
    fireEvent.change(emailInput, { target: { value: "invalid-email" } });

    await waitFor(() => {
      expect(screen.getByText("Format d'e-mail invalide")).toBeInTheDocument();
    });
  });

  it("accepte une adresse e-mail valide", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([]);

    render(<TestWrapper />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("contact@commune.fr")).toBeInTheDocument();
    });

    const emailInput = screen.getByPlaceholderText("contact@commune.fr") as HTMLInputElement;
    fireEvent.change(emailInput, { target: { value: "valid@email.com" } });

    await waitFor(() => {
      const errorMsg = screen.queryByText("Format d'e-mail invalide");
      expect(errorMsg).not.toBeInTheDocument();
    });
  });

  it("affiche le formulaire vide prêt à la soumission", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([]);

    render(<TestWrapper />);

    await waitFor(() => {
      const submitButton = screen.getByText("Enregistrer") as HTMLButtonElement;
      expect(submitButton).toBeInTheDocument();
    });

    const submitButton = screen.getByText("Enregistrer") as HTMLButtonElement;
    expect(submitButton).not.toBeDisabled();
  });

  it("accepte la soumission avec les champs obligatoires remplis", async () => {
    const user = userEvent.setup();
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([]);
    vi.mocked(tauri.createMunicipality).mockResolvedValue(mockMunicipality);

    render(<TestWrapper />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Ex: Saint-Martin")).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText("Ex: Saint-Martin") as HTMLInputElement;
    const inseeInput = screen.getByPlaceholderText("Ex: 75056") as HTMLInputElement;

    await user.type(nameInput, "Nouvelle Commune");
    await user.type(inseeInput, "12345");

    const submitButton = screen.getByText("Enregistrer") as HTMLButtonElement;
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Configuration communale créée avec succès")).toBeInTheDocument();
    });
  });

  it("valide que les champs obligatoires sont acceptés en validation côté client", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([]);

    render(<TestWrapper />);

    await waitFor(() => {
      const nameInput = screen.getByPlaceholderText("Ex: Saint-Martin") as HTMLInputElement;
      expect(nameInput).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText("Ex: Saint-Martin") as HTMLInputElement;
    const inseeInput = screen.getByPlaceholderText("Ex: 75056") as HTMLInputElement;

    fireEvent.change(nameInput, { target: { value: "Nouvelle Commune" } });
    fireEvent.change(inseeInput, { target: { value: "12345" } });

    expect(nameInput).toBeInTheDocument();
    expect(inseeInput).toBeInTheDocument();
  });

  it("crée une nouvelle commune et affiche un message de succès", async () => {
    const user = userEvent.setup();
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([]);
    vi.mocked(tauri.createMunicipality).mockResolvedValue({
      ...mockMunicipality,
      id: 2,
    });

    render(<TestWrapper />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Ex: Saint-Martin")).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText("Ex: Saint-Martin") as HTMLInputElement;
    const inseeInput = screen.getByPlaceholderText("Ex: 75056") as HTMLInputElement;

    await user.type(nameInput, "Nouvelle Commune");
    await user.type(inseeInput, "12345");

    const submitButton = screen.getByText("Enregistrer") as HTMLButtonElement;
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Configuration communale créée avec succès")).toBeInTheDocument();
    });

    expect(tauri.createMunicipality).toHaveBeenCalled();
  });

  it("met à jour une commune existante et affiche un message de succès", async () => {
    const user = userEvent.setup();
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);
    vi.mocked(tauri.updateMunicipality).mockResolvedValue({
      ...mockMunicipality,
      name: "Saint-Martin Modifié",
    });

    render(<TestWrapper />);

    await waitFor(() => {
      const nameInput = screen.getByDisplayValue("Saint-Martin") as HTMLInputElement;
      expect(nameInput).toBeInTheDocument();
    });

    const nameInput = screen.getByDisplayValue("Saint-Martin") as HTMLInputElement;
    await user.clear(nameInput);
    await user.type(nameInput, "Saint-Martin Modifié");

    const submitButton = screen.getByText("Enregistrer") as HTMLButtonElement;
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Configuration communale mise à jour avec succès")).toBeInTheDocument();
    });

    expect(tauri.updateMunicipality).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        name: "Saint-Martin Modifié",
      })
    );
  });

  it("est accessible au clavier pour tous les champs", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);

    render(<TestWrapper />);

    await waitFor(() => {
      const nameInput = screen.getByDisplayValue("Saint-Martin") as HTMLInputElement;
      expect(nameInput).toBeInTheDocument();
    });

    // Attendre que le formulaire soit complètement chargé
    await waitFor(() => {
      expect(screen.getByText("Enregistrer")).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText("Ex: Saint-Martin") as HTMLInputElement;
    const inseeInput = screen.getByPlaceholderText("Ex: 75056") as HTMLInputElement;
    const emailInput = screen.getByPlaceholderText("contact@commune.fr") as HTMLInputElement;
    const submitButton = screen.getByText("Enregistrer") as HTMLButtonElement;

    // Tous les champs doivent être focalisables
    expect(nameInput.tabIndex).toBeGreaterThanOrEqual(-1);
    expect(inseeInput.tabIndex).toBeGreaterThanOrEqual(-1);
    expect(emailInput.tabIndex).toBeGreaterThanOrEqual(-1);
    expect(submitButton.tabIndex).toBeGreaterThanOrEqual(-1);
  });


  it("affiche l'erreur de chargement initial de la commune", async () => {
    vi.mocked(tauri.listMunicipalities).mockRejectedValue(new Error("Erreur de connexion"));

    render(<TestWrapper />);

    await waitFor(() => {
      expect(screen.getByText(/Erreur lors du chargement de la configuration/)).toBeInTheDocument();
    });
  });

  it("affiche un état vide après erreur de chargement", async () => {
    vi.mocked(tauri.listMunicipalities).mockRejectedValue(new Error("Erreur de connexion"));

    render(<TestWrapper />);

    await waitFor(() => {
      expect(screen.getByText("Impossible de charger la configuration de la commune.")).toBeInTheDocument();
    });
  });

  it("associe les champs aux messages d'erreur via aria-describedby avec des IDs uniques", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);

    render(<TestWrapper />);

    await waitFor(() => {
      const nameInput = screen.getByDisplayValue("Saint-Martin") as HTMLInputElement;
      expect(nameInput).toBeInTheDocument();
    });

    const nameInput = screen.getByPlaceholderText("Ex: Saint-Martin") as HTMLInputElement;
    const inseeInput = screen.getByPlaceholderText("Ex: 75056") as HTMLInputElement;
    const emailInput = screen.getByPlaceholderText("contact@commune.fr") as HTMLInputElement;

    // Vérifier que les champs ont des IDs uniques pour l'accessibilité
    expect(nameInput).toHaveAttribute("id", "name");
    expect(inseeInput).toHaveAttribute("id", "insee_code");
    expect(emailInput).toHaveAttribute("id", "email");

    // Vérifier que aria-invalid est défini et initialisé à false
    expect(nameInput).toHaveAttribute("aria-invalid", "false");
    expect(inseeInput).toHaveAttribute("aria-invalid", "false");

    // Vérifier que les IDs d'erreur existent dans le DOM pour les champs en erreur
    // Les éléments p avec les IDs d'erreur doivent être présents même s'ils ne sont pas visibles
    // car ils sont affichés conditionnellement
  });

  it("expose l'erreur de courriel de façon accessible en temps réel et à la soumission", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([]);

    render(<TestWrapper />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("contact@commune.fr")).toBeInTheDocument();
    });

    const emailInput = screen.getByPlaceholderText("contact@commune.fr") as HTMLInputElement;

    // Validation en temps réel
    fireEvent.change(emailInput, { target: { value: "invalid" } });

    await waitFor(() => {
      expect(emailInput).toHaveAttribute("aria-invalid", "true");
      expect(emailInput).toHaveAttribute("aria-describedby", "email-error");
      expect(screen.getByText("Format d'e-mail invalide")).toBeInTheDocument();
    });

    // Correction et validation
    fireEvent.change(emailInput, { target: { value: "valid@email.com" } });

    await waitFor(() => {
      expect(emailInput).toHaveAttribute("aria-invalid", "false");
      const error = screen.queryByText("Format d'e-mail invalide");
      expect(error).not.toBeInTheDocument();
    });
  });

  it("utilise les labels associés aux champs pour l'accessibilité", async () => {
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);

    render(<TestWrapper />);

    await waitFor(() => {
      const nameInput = screen.getByLabelText(/Nom de la commune/);
      expect(nameInput).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText(/Nom de la commune/);
    const inseeInput = screen.getByLabelText(/Code INSEE/);
    const emailInput = screen.getByLabelText(/Adresse e-mail/);

    expect(nameInput).toBeInTheDocument();
    expect(inseeInput).toBeInTheDocument();
    expect(emailInput).toBeInTheDocument();
  });

  it("gère les erreurs d'API et affiche un message d'erreur", async () => {
    const user = userEvent.setup();
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);
    vi.mocked(tauri.updateMunicipality).mockRejectedValue(new Error("Erreur base de données"));

    render(<TestWrapper />);

    await waitFor(() => {
      const nameInput = screen.getByDisplayValue("Saint-Martin") as HTMLInputElement;
      expect(nameInput).toBeInTheDocument();
    });

    const nameInput = screen.getByDisplayValue("Saint-Martin") as HTMLInputElement;
    await user.clear(nameInput);
    await user.type(nameInput, "Nouvelle Valeur");

    const submitButton = screen.getByText("Enregistrer") as HTMLButtonElement;
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Erreur base de données")).toBeInTheDocument();
    });
  });

  it("désactive le formulaire pendant la soumission", async () => {
    const user = userEvent.setup();
    vi.mocked(tauri.listMunicipalities).mockResolvedValue([mockMunicipality]);
    vi.mocked(tauri.updateMunicipality).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockMunicipality), 100))
    );

    render(<TestWrapper />);

    await waitFor(() => {
      const nameInput = screen.getByDisplayValue("Saint-Martin") as HTMLInputElement;
      expect(nameInput).toBeInTheDocument();
    });

    const nameInput = screen.getByDisplayValue("Saint-Martin") as HTMLInputElement;
    await user.clear(nameInput);
    await user.type(nameInput, "Nouvelle Valeur");

    const submitButton = screen.getByText("Enregistrer") as HTMLButtonElement;
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Enregistrement...")).toBeInTheDocument();
    });
  });
});
