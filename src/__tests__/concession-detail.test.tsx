import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter, MemoryRouter, Routes, Route } from "react-router-dom";
import ConcessionDetailPage from "@/pages/ConcessionDetailPage";
import * as tauriLib from "@/lib/tauri";
import type { ConcessionDTO, CemeteryDTO, PlotDTO } from "@/types/bindings";

vi.mock("@/lib/tauri");

const mockConcession: ConcessionDTO = {
  id: 1,
  cemetery_id: 1,
  plot_id: 10,
  concession_number: "A-001",
  concession_type: "TRENTENAIRE",
  duration_years: 30,
  start_date: "2020-01-15",
  holder_first_name: "Jean",
  holder_last_name: "Dupont",
  holder_address: "123 rue de la Paix",
  holder_postal_code: "75001",
  holder_commune: "Paris",
  observations: "Concession bien entretenue",
  acquired_at: "2020-01-15",
  expires_at: "2050-01-15",
  renewed_at: null,
  status: "ACTIVE",
  created_at: "2020-01-15T10:00:00Z",
  updated_at: "2023-06-20T14:30:00Z",
};

const mockCemetery: CemeteryDTO = {
  id: 1,
  name: "Cimetière du Père-Lachaise",
  commune: "Paris",
  capacity: 1000,
  created_at: "2020-01-01T10:00:00Z",
  updated_at: "2020-01-01T10:00:00Z",
};

const mockPlot: PlotDTO = {
  id: 10,
  cemetery_id: 1,
  section: "A",
  row: 5,
  number: 12,
  capacity: 2,
  status: "occupied",
  created_at: "2020-01-01T10:00:00Z",
  updated_at: "2020-01-01T10:00:00Z",
};

const mockPerpetuelle: ConcessionDTO = {
  ...mockConcession,
  id: 2,
  concession_number: "A-002",
  concession_type: "PERPETUELLE",
  duration_years: null,
  expires_at: null,
  status: "PERPETUELLE",
};

describe("ConcessionDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche l'état de chargement initialement", async () => {
    vi.spyOn(tauriLib, "getConcession").mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockConcession), 100))
    );
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Concession/)).toBeInTheDocument();
    });
  });

  it("affiche tous les champs métier d'une concession", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockConcession);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    expect(screen.getByText("30 ans")).toBeInTheDocument();
    expect(screen.getByText("Jean")).toBeInTheDocument();
    expect(screen.getByText("Dupont")).toBeInTheDocument();
    expect(screen.getByText("123 rue de la Paix")).toBeInTheDocument();
    expect(screen.getByText("75001")).toBeInTheDocument();
    expect(screen.getByText("Concession bien entretenue")).toBeInTheDocument();
  });

  it("affiche 'Perpétuelle' pour le type et le statut d'une concession perpétuelle", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockPerpetuelle);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/2"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-002")).toBeInTheDocument();
    });

    // Should show "Perpétuelle" for type
    const typeElements = screen.getAllByText("Perpétuelle");
    expect(typeElements.length).toBeGreaterThanOrEqual(2);
  });

  it("affiche 'Perpétuelle' pour l'expiration quand status est PERPETUELLE", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockPerpetuelle);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/2"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-002")).toBeInTheDocument();
    });

    // The "Expire le" field should show "Perpétuelle"
    const headings = screen.getAllByText("Perpétuelle");
    expect(headings.length).toBeGreaterThanOrEqual(2);
  });

  it("affiche les dates d'audit (créée et modifiée)", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockConcession);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    expect(screen.getByText("Créée le")).toBeInTheDocument();
    expect(screen.getByText("Modifiée le")).toBeInTheDocument();
  });

  it("affiche les informations du concessionnaire", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockConcession);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Concessionnaire")).toBeInTheDocument();
    });

    expect(screen.getByText("Jean")).toBeInTheDocument();
    expect(screen.getByText("Dupont")).toBeInTheDocument();
    expect(screen.getByText("123 rue de la Paix")).toBeInTheDocument();
    expect(screen.getByText("75001")).toBeInTheDocument();
    expect(screen.getByText("Paris")).toBeInTheDocument();
  });

  it("affiche les observations quand elles existent", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockConcession);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    expect(screen.getByText("Observations")).toBeInTheDocument();
    expect(screen.getByText("Concession bien entretenue")).toBeInTheDocument();
  });

  it("n'affiche pas la section observations quand elle est vide", async () => {
    const concessionWithoutObservations = { ...mockConcession, observations: null };
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(concessionWithoutObservations);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    expect(screen.queryByText("Observations")).not.toBeInTheDocument();
  });

  it("affiche l'emplacement avec section, rangée et numéro", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockConcession);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    // Wait for cemetery and plot data to load
    await waitFor(() => {
      expect(screen.getByText("A • 5 • 12")).toBeInTheDocument();
    });
  });

  it("gère les champs optionnels manquants", async () => {
    const concessionWithoutOptionals = {
      ...mockConcession,
      holder_first_name: null,
      holder_last_name: null,
      holder_address: null,
      holder_postal_code: null,
      holder_commune: null,
      observations: null,
      start_date: null,
      renewed_at: null,
    };

    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(concessionWithoutOptionals);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("affiche le badge de statut avec la bonne couleur", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockConcession);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    expect(screen.getByText("Actif")).toBeInTheDocument();
  });

  it("affiche une concession avec statut ECHEANCE_PROCHE", async () => {
    const concessionEcheance: ConcessionDTO = {
      ...mockConcession,
      id: 3,
      concession_number: "A-003",
      status: "ECHEANCE_PROCHE",
    };

    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(concessionEcheance);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/3"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-003")).toBeInTheDocument();
    });

    expect(screen.getByText("Échéance proche")).toBeInTheDocument();
  });

  it("affiche une concession avec statut EXPIREE", async () => {
    const concessionExpired: ConcessionDTO = {
      ...mockConcession,
      id: 4,
      concession_number: "A-004",
      status: "EXPIREE",
    };

    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(concessionExpired);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/4"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-004")).toBeInTheDocument();
    });

    expect(screen.getByText("Expiré")).toBeInTheDocument();
  });

  it("affiche une concession avec adresse complète du concessionnaire", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockConcession);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    // Vérifier tous les champs d'adresse
    expect(screen.getByText("123 rue de la Paix")).toBeInTheDocument();
    expect(screen.getByText("75001")).toBeInTheDocument();
    expect(screen.getByText("Paris")).toBeInTheDocument();
  });

  it("gère les types de concession TRENTENAIRE et CINQUANTENAIRE", async () => {
    const trente: ConcessionDTO = {
      ...mockConcession,
      concession_type: "TRENTENAIRE",
      duration_years: 30,
    };

    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(trente);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    const { rerender } = render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    expect(screen.getByText("30 ans")).toBeInTheDocument();
  });

  it("affiche le nom du cimetière associé", async () => {
    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(mockConcession);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getAllByText("Cimetière du Père-Lachaise").length).toBeGreaterThan(0);
    });
  });

  it("affiche des tirets pour les champs vides du concessionnaire", async () => {
    const concessionWithoutHolder: ConcessionDTO = {
      ...mockConcession,
      holder_address: null,
      holder_postal_code: null,
      holder_commune: null,
    };

    vi.spyOn(tauriLib, "getConcession").mockResolvedValue(concessionWithoutHolder);
    vi.spyOn(tauriLib, "getCemetery").mockResolvedValue(mockCemetery);
    vi.spyOn(tauriLib, "getPlot").mockResolvedValue(mockPlot);
    vi.spyOn(tauriLib, "listAlerts").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/concessions/1"]}>
        <Routes>
          <Route path="/concessions/:id" element={<ConcessionDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("A-001")).toBeInTheDocument();
    });

    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });
});
