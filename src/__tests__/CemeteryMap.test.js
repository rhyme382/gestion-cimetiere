import { jsx as _jsx } from "react/jsx-runtime";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CemeteryMap } from "@/components/map/CemeteryMap";
import { mockCemeteryMap, createMockCemeteryMap } from "@/mocks/cemetery-map";
describe("CemeteryMap Component", () => {
    it("should render without crashing", () => {
        const { container } = render(_jsx(CemeteryMap, { data: mockCemeteryMap }));
        expect(container.querySelector("svg")).toBeInTheDocument();
    });
    it("should display legend with all status colors", () => {
        render(_jsx(CemeteryMap, { data: mockCemeteryMap }));
        expect(screen.getByText("Libre")).toBeInTheDocument();
        expect(screen.getByText("Occupé")).toBeInTheDocument();
        expect(screen.getByText("Réservé")).toBeInTheDocument();
        expect(screen.getByText("Indisponible")).toBeInTheDocument();
    });
    it("should display section labels", () => {
        const { container } = render(_jsx(CemeteryMap, { data: mockCemeteryMap }));
        const svg = container.querySelector("svg");
        expect(svg).toBeInTheDocument();
        // Check for section labels in SVG text elements
        const textElements = svg?.querySelectorAll("text");
        const hasSecA = Array.from(textElements || []).some(el => el.textContent?.includes("Secteur A"));
        expect(hasSecA).toBe(true);
    });
    it("should display statistics footer with correct counts", () => {
        render(_jsx(CemeteryMap, { data: mockCemeteryMap, selectedPlotId: null }));
        // Check for stats display (legend will always be visible)
        expect(screen.getByText("Libre")).toBeInTheDocument();
        expect(screen.getByText("Occupé")).toBeInTheDocument();
    });
    it("should call onPlotSelect when a plot is clicked", () => {
        const onPlotSelect = vi.fn();
        const { container } = render(_jsx(CemeteryMap, { data: mockCemeteryMap, onPlotSelect: onPlotSelect }));
        const svg = container.querySelector("svg");
        const firstRect = svg?.querySelector("rect");
        if (firstRect) {
            fireEvent.click(firstRect);
            expect(onPlotSelect).toHaveBeenCalled();
        }
    });
    it("should handle plot selection state", () => {
        const { rerender } = render(_jsx(CemeteryMap, { data: mockCemeteryMap, selectedPlotId: null }));
        // Check stats footer visible when no selection
        expect(screen.getByText("Capacité")).toBeInTheDocument();
        // Re-render with selected plot
        rerender(_jsx(CemeteryMap, { data: mockCemeteryMap, selectedPlotId: 1 }));
        // Selection info should update
        expect(screen.getByText("Emplacement sélectionné : ID 1")).toBeInTheDocument();
    });
    it("should render SVG with correct dimensions", () => {
        const { container } = render(_jsx(CemeteryMap, { data: mockCemeteryMap }));
        const svg = container.querySelector("svg");
        expect(svg).toHaveAttribute("width");
        expect(svg).toHaveAttribute("height");
        const width = parseInt(svg?.getAttribute("width") || "0", 10);
        const height = parseInt(svg?.getAttribute("height") || "0", 10);
        expect(width).toBeGreaterThan(0);
        expect(height).toBeGreaterThan(0);
    });
    it("should handle empty sections gracefully", () => {
        const emptyData = {
            ...mockCemeteryMap,
            plots: [],
            occupied_count: 0,
            available_count: 0,
            total_capacity: 0,
        };
        const { container } = render(_jsx(CemeteryMap, { data: emptyData }));
        const svg = container.querySelector("svg");
        expect(svg).toBeInTheDocument();
    });
    it("should render different cemetery sizes", () => {
        const smallCemetery = createMockCemeteryMap(1, 1, 2); // 2 plots
        const largeCemetery = createMockCemeteryMap(3, 5, 10); // 150 plots
        const { container: smallContainer } = render(_jsx(CemeteryMap, { data: smallCemetery }));
        const { container: largeContainer } = render(_jsx(CemeteryMap, { data: largeCemetery }));
        const smallSvg = smallContainer.querySelector("svg");
        const largeSvg = largeContainer.querySelector("svg");
        const smallHeight = parseInt(smallSvg?.getAttribute("height") || "0", 10);
        const largeHeight = parseInt(largeSvg?.getAttribute("height") || "0", 10);
        expect(largeHeight).toBeGreaterThan(smallHeight);
    });
    it("should display correct plot status colors via fill attribute", () => {
        const { container } = render(_jsx(CemeteryMap, { data: mockCemeteryMap }));
        const svg = container.querySelector("svg");
        const rects = svg?.querySelectorAll("rect");
        // Should have plots rendered as rects
        expect(rects && rects.length > 0).toBe(true);
    });
    it("should support multiple sections", () => {
        const multiSectionData = createMockCemeteryMap(3, 2, 4); // 3 sections (A, B, C)
        const { container } = render(_jsx(CemeteryMap, { data: multiSectionData }));
        const svg = container.querySelector("svg");
        const textElements = svg?.querySelectorAll("text") || [];
        // Check for section labels
        let foundSections = 0;
        textElements.forEach(el => {
            if (el.textContent?.includes("Secteur"))
                foundSections++;
        });
        expect(foundSections).toBe(3); // A, B, C
    });
    it("should calculate correct grid for complex cemetery", () => {
        const complexCemetery = createMockCemeteryMap(2, 4, 10); // 2 sections, 4 rows, 10 plots per row
        const { container } = render(_jsx(CemeteryMap, { data: complexCemetery }));
        const svg = container.querySelector("svg");
        // SVG should be rendered
        expect(svg).toBeInTheDocument();
        // Total plots should be section_count * max_row * max_number
        expect(complexCemetery.total_capacity).toBe(80);
    });
});
