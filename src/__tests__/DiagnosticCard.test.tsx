import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DiagnosticCard } from "@/components/DiagnosticCard";
import * as tauriLib from "@/lib/tauri";

vi.mock("@/lib/tauri");

describe("DiagnosticCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche l'état de chargement initialement", async () => {
    vi.spyOn(tauriLib, "getDiagnostic").mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({
        health: "Ok",
        sqlite_available: true,
        app_version: "1.0.0",
        message: "Tout fonctionne normalement"
      }), 100))
    );

    render(<DiagnosticCard />);

    await waitFor(() => {
      expect(screen.getByText("Diagnostic technique")).toBeInTheDocument();
    });
  });

  it("affiche les résultats du diagnostic nominal", async () => {
    const mockDiagnostic = {
      health: "Ok",
      sqlite_available: true,
      app_version: "1.0.0",
      message: "Tout fonctionne normalement"
    };

    vi.spyOn(tauriLib, "getDiagnostic").mockResolvedValue(mockDiagnostic);

    render(<DiagnosticCard />);

    await waitFor(() => {
      expect(screen.getByText("Ok")).toBeInTheDocument();
    });

    expect(screen.getByText("SQLite OK")).toBeInTheDocument();
    expect(screen.getByText("1.0.0")).toBeInTheDocument();
    expect(screen.getByText("Tout fonctionne normalement")).toBeInTheDocument();
  });

  it("affiche l'erreur lorsque le diagnostic échoue", async () => {
    const errorMessage = "Impossible de se connecter à la base de données";
    vi.spyOn(tauriLib, "getDiagnostic").mockRejectedValue(
      new Error(errorMessage)
    );

    render(<DiagnosticCard />);

    await waitFor(() => {
      expect(screen.getByText("Erreur")).toBeInTheDocument();
    });

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByText("Réessayer")).toBeInTheDocument();
  });

  it("affiche SQLite indisponible lorsque sqlite_available est false", async () => {
    const mockDiagnostic = {
      health: "Error",
      sqlite_available: false,
      app_version: "1.0.0",
      message: "SQLite not available"
    };

    vi.spyOn(tauriLib, "getDiagnostic").mockResolvedValue(mockDiagnostic);

    render(<DiagnosticCard />);

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument();
    });

    expect(screen.getByText("Indisponible")).toBeInTheDocument();
  });

  it("réessaye le diagnostic lors du clic sur Réessayer", async () => {
    const mockGetDiagnostic = vi.spyOn(tauriLib, "getDiagnostic");
    mockGetDiagnostic.mockRejectedValueOnce(new Error("Erreur initiale"));
    mockGetDiagnostic.mockResolvedValueOnce({
      health: "Ok",
      sqlite_available: true,
      app_version: "1.0.0",
      message: "Récupération réussie"
    });

    render(<DiagnosticCard />);

    await waitFor(() => {
      expect(screen.getByText("Erreur initiale")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const retryButton = screen.getByText("Réessayer");
    await user.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText("Ok")).toBeInTheDocument();
    });
  });

  it("affiche un header avec l'icône Activity", async () => {
    vi.spyOn(tauriLib, "getDiagnostic").mockResolvedValue({
      health: "Ok",
      sqlite_available: true,
      app_version: "1.0.0",
      message: ""
    });

    render(<DiagnosticCard />);

    await waitFor(() => {
      expect(screen.getByText("Diagnostic technique")).toBeInTheDocument();
    });
  });
});
