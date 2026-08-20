import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";

vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));

function TestWrapper() {
  return (
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<div>Contenu de test</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("AppLayout", () => {
  it("rend la sidebar et le contenu principal", () => {
    render(<TestWrapper />);
    expect(screen.getAllByText("Tableau de bord")).toHaveLength(2);
    expect(screen.getByText("Concessions")).toBeInTheDocument();
    expect(screen.getByText("Défunts")).toBeInTheDocument();
    expect(screen.getByText("Contenu de test")).toBeInTheDocument();
  });

  it("affiche la recherche globale dans le header", () => {
    render(<TestWrapper />);
    expect(screen.getByPlaceholderText("Recherche globale…")).toBeInTheDocument();
  });
});
