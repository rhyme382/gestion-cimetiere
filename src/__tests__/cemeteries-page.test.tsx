import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import CemeteriesPage from "@/pages/CemeteriesPage";
import * as tauriLib from "@/lib/tauri";
import type { CemeteryDTO } from "@/types/bindings";

vi.mock("@/lib/tauri");

const mockCemeteries: CemeteryDTO[] = [
  {
    id: 1,
    name: "Cimetière du Nord",
    address: "123 Avenue de la Paix",
    commune: "Paris",
    capacity: 500,
    municipality_id: 1,
    is_active: 1,
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
  },
  {
    id: 2,
    name: "Cimetière du Sud",
    address: "456 Rue de Lyon",
    commune: "Paris",
    capacity: 300,
    municipality_id: 1,
    is_active: 1,
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
  },
  {
    id: 3,
    name: "Cimetière Ancien",
    address: null,
    commune: null,
    capacity: null,
    municipality_id: 1,
    is_active: 0,
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
  },
];

function TestWrapper({ children }: { children: React.ReactNode }) {
  return <BrowserRouter>{children}</BrowserRouter>;
}

describe("CemeteriesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le titre et la description", async () => {
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    expect(screen.getByText("Cimetières")).toBeInTheDocument();
    expect(screen.getByText("Gestion des cimetières de la commune")).toBeInTheDocument();
  });

  it("charge et affiche les cimetières", async () => {
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText("Cimetière du Nord")).toBeInTheDocument();
      expect(screen.getByText("Cimetière du Sud")).toBeInTheDocument();
      expect(screen.getByText("Cimetière Ancien")).toBeInTheDocument();
    });
  });

  it("affiche l'état vide quand il n'y a pas de cimetière", async () => {
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue([]);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText("Aucun cimetière")).toBeInTheDocument();
      expect(screen.getByText("Créez votre premier cimetière pour commencer")).toBeInTheDocument();
    });
  });

  it("affiche un message d'erreur si le chargement échoue", async () => {
    const error = new Error("Erreur réseau");
    vi.mocked(tauriLib.listCemeteries).mockRejectedValue(error);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText("Erreur réseau")).toBeInTheDocument();
    });
  });

  it("distingue visuellement les cimetières inactifs", async () => {
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    await waitFor(() => {
      const inactiveBadge = screen.getAllByText("Inactif")[0];
      const card = inactiveBadge.closest("[class*='rounded-lg border']");
      expect(card).toHaveClass("opacity-60");
    });
  });

  it("affiche les badges de statut corrects", async () => {
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    await waitFor(() => {
      const activeBadges = screen.getAllByText("Actif");
      const inactiveBadges = screen.getAllByText("Inactif");
      expect(activeBadges.length).toBe(2);
      expect(inactiveBadges.length).toBe(1);
    });
  });

  it("affiche le bouton créer cimetière", async () => {
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    const createButton = await screen.findByText("Ajouter un cimetière");
    expect(createButton).toBeInTheDocument();
  });

  it("ouvre le formulaire de création au clic sur ajouter", async () => {
    const user = userEvent.setup();
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    const createButton = await screen.findByText("Ajouter un cimetière");
    await user.click(createButton);

    expect(screen.getByText("Créer un cimetière")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ex: Cimetière du Nord")).toBeInTheDocument();
  });

  it("crée un cimetière et rafraîchit la liste", async () => {
    const user = userEvent.setup();
    vi.mocked(tauriLib.listCemeteries)
      .mockResolvedValueOnce(mockCemeteries)
      .mockResolvedValueOnce([...mockCemeteries, {
        id: 4,
        name: "Nouveau Cimetière",
        address: "789 Rue du Repos",
        commune: "Paris",
        capacity: 200,
        municipality_id: 1,
        is_active: 1,
        created_at: "2026-01-15T00:00:00Z",
        updated_at: "2026-01-15T00:00:00Z",
      }]);

    const createCemeteryMock = vi.fn().mockResolvedValue({
      id: 4,
      name: "Nouveau Cimetière",
      address: "789 Rue du Repos",
      commune: "Paris",
      capacity: 200,
      municipality_id: 1,
      is_active: 1,
      created_at: "2026-01-15T00:00:00Z",
      updated_at: "2026-01-15T00:00:00Z",
    });

    vi.mocked(tauriLib.createCemetery).mockImplementation(createCemeteryMock);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    const createButton = await screen.findByText("Ajouter un cimetière");
    await user.click(createButton);

    const nameInput = screen.getByPlaceholderText("Ex: Cimetière du Nord") as HTMLInputElement;
    await user.type(nameInput, "Nouveau Cimetière");

    const submitButton = screen.getByRole("button", { name: /Créer/ });
    await user.click(submitButton);

    await waitFor(() => {
      expect(createCemeteryMock).toHaveBeenCalledWith(
        expect.objectContaining({ name: "Nouveau Cimetière" })
      );
    });
  });

  it("modifie un cimetière au clic sur éditer", async () => {
    const user = userEvent.setup();
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    const updateCemeteryMock = vi.fn().mockResolvedValue({
      ...mockCemeteries[0],
      name: "Cimetière du Nord (Modifié)",
    });

    vi.mocked(tauriLib.updateCemetery).mockImplementation(updateCemeteryMock);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText("Cimetière du Nord")).toBeInTheDocument();
    });

    const editButtons = screen.getAllByTitle("Modifier");
    await user.click(editButtons[0]);

    expect(screen.getByText("Modifier le cimetière")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Cimetière du Nord")).toBeInTheDocument();
  });

  it("affiche la fiche détails au clic sur œil", async () => {
    const user = userEvent.setup();
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText("Cimetière du Nord")).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByTitle("Voir les détails");
    await user.click(viewButtons[0]);

    expect(screen.getByText("Détails du cimetière")).toBeInTheDocument();
    expect(screen.getByText("123 Avenue de la Paix")).toBeInTheDocument();
    expect(screen.getByText("Paris")).toBeInTheDocument();
  });

  it("filtre les cimetières par recherche", async () => {
    const user = userEvent.setup();
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText("Cimetière du Nord")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Rechercher par nom, adresse ou commune...");
    await user.type(searchInput, "Sud");

    await waitFor(() => {
      expect(screen.getByText("Cimetière du Sud")).toBeInTheDocument();
      expect(screen.queryByText("Cimetière du Nord")).not.toBeInTheDocument();
    });
  });

  it("affiche les informations optionnelles du cimetière", async () => {
    vi.mocked(tauriLib.listCemeteries).mockResolvedValue(mockCemeteries);

    render(
      <TestWrapper>
        <CemeteriesPage />
      </TestWrapper>
    );

    await waitFor(() => {
      const addressElements = screen.queryAllByText(/123 Avenue de la Paix/);
      expect(addressElements.length).toBeGreaterThan(0);

      const capacityElements = screen.queryAllByText(/Capacité:/);
      expect(capacityElements.length).toBeGreaterThan(0);
    });
  });
});
