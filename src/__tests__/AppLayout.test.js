import { jsx as _jsx } from "react/jsx-runtime";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
function TestWrapper() {
    return (_jsx(MemoryRouter, { initialEntries: ["/"], children: _jsx(Routes, { children: _jsx(Route, { path: "/", element: _jsx(AppLayout, {}), children: _jsx(Route, { index: true, element: _jsx("div", { children: "Contenu de test" }) }) }) }) }));
}
describe("AppLayout", () => {
    it("rend la sidebar et le contenu principal", () => {
        render(_jsx(TestWrapper, {}));
        expect(screen.getAllByText("Tableau de bord")).toHaveLength(2);
        expect(screen.getByText("Concessions")).toBeInTheDocument();
        expect(screen.getByText("Défunts")).toBeInTheDocument();
        expect(screen.getByText("Contenu de test")).toBeInTheDocument();
    });
    it("affiche la recherche globale dans le header", () => {
        render(_jsx(TestWrapper, {}));
        expect(screen.getByPlaceholderText("Recherche globale…")).toBeInTheDocument();
    });
});
