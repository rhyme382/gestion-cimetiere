import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";

describe("Sidebar", () => {
  it("affiche tous les liens de navigation principaux", () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText("Tableau de bord")).toBeInTheDocument();
    expect(screen.getByText("Cimetières")).toBeInTheDocument();
    expect(screen.getByText("Emplacements")).toBeInTheDocument();
    expect(screen.getByText("Concessions")).toBeInTheDocument();
    expect(screen.getByText("Défunts")).toBeInTheDocument();
    expect(screen.getByText("Alertes")).toBeInTheDocument();
    expect(screen.getByText("Recherche")).toBeInTheDocument();
    expect(screen.getByText("Paramètres")).toBeInTheDocument();
  });

  it("affiche le branding de l'application", () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.getByText("Gestion Cimetière")).toBeInTheDocument();
    expect(screen.getByText("GC")).toBeInTheDocument();
  });
});
