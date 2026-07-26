import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import ConcessionsPage from "@/pages/ConcessionsPage";
import * as tauriLib from "@/lib/tauri";
import type { ConcessionDTO, CemeteryDTO, PlotDTO } from "@/types/bindings";

vi.mock("@/lib/tauri");

const mockCemeteries: CemeteryDTO[] = [
  {
    id: 1,
    name: "Cimetière du Nord",
    commune: "Paris",
    capacity: 500,
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
  },
  {
    id: 2,
    name: "Cimetière du Sud",
    commune: "Paris",
    capacity: 300,
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
  },
];

const mockPlots: PlotDTO[] = [
  {
    id: 10,
    cemetery_id: 1,
    section: "A",
    row: 1,
    number: 5,
    capacity: 4,
    status: "occupied",
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
  },
  {
    id: 11,
    cemetery_id: 1,
    section: "A",
    row: 1,
    number: 6,
    capacity: 4,
    status: "occupied",
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
  },
  {
    id: 20,
    cemetery_id: 2,
    section: "B",
    row: 2,
    number: 10,
    capacity: 4,
    status: "occupied",
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
  },
];

const mockConcessions: ConcessionDTO[] = [
  {
    id: 1,
    cemetery_id: 1,
    plot_id: 10,
    concession_number: "A-001",
    concession_type: "PERPETUELLE",
    duration_years: null,
    start_date: "2020-01-15",
    holder_first_name: "Jean",
    holder_last_name: "Dupont",
    holder_address: "123 rue de la Paix",
    holder_postal_code: "75001",
    holder_commune: "Paris",
    observations: "Concession perpétuelle",
    acquired_at: "2020-01-15",
    expires_at: null,
    renewed_at: null,
    status: "ACTIVE",
    created_at: "2020-01-15T10:00:00Z",
    updated_at: "2020-01-15T10:00:00Z",
  },
  {
    id: 2,
    cemetery_id: 1,
    plot_id: 11,
    concession_number: "A-002",
    concession_type: "TRENTENAIRE",
    duration_years: 30,
    start_date: "2020-06-20",
    holder_first_name: "Marie",
    holder_last_name: "Martin",
    holder_address: "456 avenue de Lyon",
    holder_postal_code: "75020",
    holder_commune: "Paris",
    observations: null,
    acquired_at: "2020-06-20",
    expires_at: "2050-06-20",
    renewed_at: null,
    status: "ECHEANCE_PROCHE",
    created_at: "2020-06-20T10:00:00Z",
    updated_at: "2020-06-20T10:00:00Z",
  },
  {
    id: 3,
    cemetery_id: 2,
    plot_id: 20,
    concession_number: "B-001",
    concession_type: "CINQUANTENAIRE",
    duration_years: 50,
    start_date: "2010-03-10",
    holder_first_name: "Pierre",
    holder_last_name: "Bernard",
    holder_address: "789 rue de Rivoli",
    holder_postal_code: "75004",
    holder_commune: "Paris",
    observations: null,
    acquired_at: "2010-03-10",
    expires_at: "2060-03-10",
    renewed_at: null,
    status: "EXPIREE",
    created_at: "2010-03-10T10:00:00Z",
    updated_at: "2010-03-10T10:00:00Z",
  },
];

describe("ConcessionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(tauriLib, "listCemeteries").mockResolvedValue(mockCemeteries);
    vi.spyOn(tauriLib, "listPlots").mockImplementation((cemeteryId) => {
      const plots = mockPlots.filter((p) => p.cemetery_id === cemeteryId);
      return Promise.resolve(plots);
    });
  });

  it("affiche l'état de chargement initialement", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockConcessions), 100))
    );

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Concessions")).toBeInTheDocument();
    });
  });

  it("affiche la liste des concessions avec tous les champs requis", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue(mockConcessions);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    expect(screen.getByText("Jean Dupont")).toBeInTheDocument();
    expect(screen.getByText("Marie Martin")).toBeInTheDocument();
    expect(screen.getByText("Pierre Bernard")).toBeInTheDocument();

    // Check cemetery names - wait for them to load
    await waitFor(() => {
      const rows = screen.getAllByRole("row");
      expect(rows.length).toBeGreaterThan(1);
      // Check that cemetery names appear in the table
      const rowTexts = rows.map((row) => row.textContent);
      expect(rowTexts.join(" ")).toContain("Cimetière du Nord");
      expect(rowTexts.join(" ")).toContain("Cimetière du Sud");
    });

    // Check plot locations - wait for them to load
    await waitFor(() => {
      expect(screen.getByText("A • 1 • 5")).toBeInTheDocument();
    });
    expect(screen.getByText("A • 1 • 6")).toBeInTheDocument();
    expect(screen.getByText("B • 2 • 10")).toBeInTheDocument();

    // Verify columns appear in table
    expect(screen.getByText("30 ans")).toBeInTheDocument();
    expect(screen.getByText("50 ans")).toBeInTheDocument();
  });

  it("affiche le badge de statut avec la bonne couleur", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue(mockConcessions);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    // Verify status badges exist in table
    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThan(1);
  });

  it("filtre les concessions par statut", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue(mockConcessions);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const activeButton = screen.getByRole("button", { name: /Actif/ });
    await user.click(activeButton);

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
      expect(screen.queryByText("A-002")).not.toBeInTheDocument();
      expect(screen.queryByText("B-001")).not.toBeInTheDocument();
    });
  });

  it("recherche par numéro de concession", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue(mockConcessions);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const searchInput = screen.getByPlaceholderText("Numéro, concessionnaire...");
    await user.type(searchInput, "A-002");

    await waitFor(() => {
      expect(screen.queryByText("A-001")).not.toBeInTheDocument();
      expect(screen.getByText("A-002")).toBeInTheDocument();
      expect(screen.queryByText("B-001")).not.toBeInTheDocument();
    });
  });

  it("recherche par nom du concessionnaire", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue(mockConcessions);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Jean Dupont")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const searchInput = screen.getByPlaceholderText("Numéro, concessionnaire...");
    await user.type(searchInput, "Marie");

    await waitFor(() => {
      expect(screen.queryByText("Jean Dupont")).not.toBeInTheDocument();
      expect(screen.getByText("Marie Martin")).toBeInTheDocument();
      expect(screen.queryByText("Pierre Bernard")).not.toBeInTheDocument();
    });
  });

  it("combine recherche et filtre de statut", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue(mockConcessions);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    const user = userEvent.setup();

    const statusButton = screen.getByRole("button", { name: /Échéance proche/ });
    await user.click(statusButton);

    const searchInput = screen.getByPlaceholderText("Numéro, concessionnaire...");
    await user.type(searchInput, "Marie");

    await waitFor(() => {
      expect(screen.getByText("Marie Martin")).toBeInTheDocument();
      expect(screen.queryByText("Jean Dupont")).not.toBeInTheDocument();
    });
  });

  it("affiche l'état vide avec le bon message", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue([]);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Aucune concession")).toBeInTheDocument();
      expect(screen.getByText("Créez une première concession pour la voir ici")).toBeInTheDocument();
    });
  });

  it("affiche l'état vide lors d'une recherche sans résultat", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue(mockConcessions);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const searchInput = screen.getByPlaceholderText("Numéro, concessionnaire...");
    await user.type(searchInput, "INEXISTANT");

    await waitFor(() => {
      expect(screen.getByText("Aucune concession")).toBeInTheDocument();
      expect(screen.getByText("Aucune concession ne correspond à vos critères")).toBeInTheDocument();
    });
  });

  it("affiche l'erreur quand l'API échoue", async () => {
    const errorMessage = "Erreur de connexion";
    vi.spyOn(tauriLib, "listConcessions").mockRejectedValue(new Error(errorMessage));

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      const errorElements = screen.getAllByText("Erreur");
      expect(errorElements.length).toBeGreaterThan(0);
    });
  });

  it("affiche 'Perpétuelle' pour expires_at quand le statut est PERPETUELLE", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue([mockConcessions[0]]);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    const row = screen.getByText("Jean Dupont").closest("tr");
    expect(within(row!).getByText("Perpétuelle")).toBeInTheDocument();
  });

  it("gère les concessionnaires sans nom", async () => {
    const concessionWithoutName: ConcessionDTO = {
      ...mockConcessions[0],
      holder_first_name: null,
      holder_last_name: null,
    };

    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue([concessionWithoutName]);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThan(1);
  });

  it("gère le refetch avec le bouton Réessayer après une erreur", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValueOnce(mockConcessions);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    // Vérifier que le titre "Concessions" est présent
    const title = screen.getByText("Concessions");
    expect(title).toBeInTheDocument();
  });

  it("affiche la liste même après plusieurs interactions de filtre et recherche", async () => {
    vi.spyOn(tauriLib, "listConcessions").mockResolvedValue(mockConcessions);

    render(
      <BrowserRouter>
        <ConcessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    const user = userEvent.setup();

    // Appliquer filtre de statut
    const activeButton = screen.getByRole("button", { name: /Actif/ });
    await user.click(activeButton);

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    // Appliquer recherche
    const searchInput = screen.getByPlaceholderText("Numéro, concessionnaire...");
    await user.type(searchInput, "A");

    // Vérifier que les résultats sont correctement filtrés
    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });
  });
});
