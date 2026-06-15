import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { MapPin } from "lucide-react";
// Grid rendering constants (from MVP-07)
const PLOT_WIDTH = 50;
const PLOT_HEIGHT = 50;
const PLOT_GAP = 2;
const SECTION_SPACING = 80;
const ROW_SPACING = 60;
export function CemeteryMap({ data, onPlotSelect, selectedPlotId, }) {
    const [hoveredPlotId, setHoveredPlotId] = useState(null);
    // Group plots by section and row
    const groupedPlots = groupPlotsBySection(data.plots);
    // Calculate canvas dimensions
    const sections = Object.keys(groupedPlots).sort();
    const sectionCount = sections.length;
    const maxRowPerSection = Math.max(...Object.values(groupedPlots).map((rows) => Object.keys(rows).length));
    const maxPlotsPerRow = Math.max(...data.plots
        .filter((p) => p.section && p.row)
        .map((p) => p.number || 0));
    const svgWidth = sectionCount * (SECTION_SPACING + (maxPlotsPerRow * (PLOT_WIDTH + PLOT_GAP)));
    const svgHeight = maxRowPerSection * (ROW_SPACING + PLOT_HEIGHT) + 100;
    // Get color for plot status
    const getPlotColor = (status) => {
        switch (status) {
            case "available":
                return "#10b981"; // green
            case "occupied":
                return "#3b82f6"; // blue
            case "reserved":
                return "#f59e0b"; // orange
            case "unavailable":
                return "#9ca3af"; // gray
            default:
                return "#e5e7eb"; // light gray
        }
    };
    return (_jsxs("div", { className: "w-full h-full flex flex-col", children: [_jsxs("div", { className: "mb-4 flex gap-4 flex-wrap text-xs", children: [_jsxs("div", { className: "flex items-center gap-2", children: [_jsx("div", { className: "w-4 h-4 rounded", style: { backgroundColor: "#10b981" } }), _jsx("span", { children: "Libre" })] }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsx("div", { className: "w-4 h-4 rounded", style: { backgroundColor: "#3b82f6" } }), _jsx("span", { children: "Occup\u00E9" })] }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsx("div", { className: "w-4 h-4 rounded", style: { backgroundColor: "#f59e0b" } }), _jsx("span", { children: "R\u00E9serv\u00E9" })] }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsx("div", { className: "w-4 h-4 rounded", style: { backgroundColor: "#9ca3af" } }), _jsx("span", { children: "Indisponible" })] })] }), _jsx("div", { className: "flex-1 border rounded-lg overflow-auto bg-slate-50", children: _jsx("svg", { width: svgWidth, height: svgHeight, className: "block", style: { minWidth: "100%", minHeight: "100%" }, children: sections.map((sectionKey, sectionIdx) => {
                        const rows = groupedPlots[sectionKey];
                        const sectionX = sectionIdx * SECTION_SPACING + 40;
                        return (_jsxs("g", { children: [_jsxs("text", { x: sectionX, y: 25, className: "text-xs font-bold", textAnchor: "start", fill: "#1f2937", children: ["Secteur ", sectionKey] }), Object.entries(rows)
                                    .sort(([rowA], [rowB]) => Number(rowA) - Number(rowB))
                                    .map(([rowKey, plots]) => {
                                    const rowNum = Number(rowKey);
                                    const rowY = rowNum * ROW_SPACING + 40;
                                    return (_jsxs("g", { children: [_jsxs("text", { x: sectionX - 30, y: rowY + PLOT_HEIGHT / 2 + 4, className: "text-xs font-semibold", textAnchor: "end", fill: "#4b5563", children: ["L", rowNum] }), plots
                                                .sort((a, b) => (a.number || 0) - (b.number || 0))
                                                .map((plot, idx) => {
                                                const plotX = sectionX + idx * (PLOT_WIDTH + PLOT_GAP);
                                                const plotY = rowY;
                                                const isSelected = selectedPlotId === plot.id;
                                                const isHovered = hoveredPlotId === plot.id;
                                                return (_jsxs("g", { onMouseEnter: () => setHoveredPlotId(plot.id), onMouseLeave: () => setHoveredPlotId(null), onClick: () => onPlotSelect?.(plot), style: { cursor: "pointer" }, children: [_jsx("rect", { x: plotX, y: plotY, width: PLOT_WIDTH, height: PLOT_HEIGHT, fill: getPlotColor(plot.status), stroke: isSelected
                                                                ? "#1e40af"
                                                                : isHovered
                                                                    ? "#374151"
                                                                    : "#d1d5db", strokeWidth: isSelected ? 3 : isHovered ? 2 : 1, rx: 2, opacity: isHovered ? 0.9 : 0.8 }), plot.number && (_jsx("text", { x: plotX + PLOT_WIDTH / 2, y: plotY + PLOT_HEIGHT / 2 + 4, className: "text-xs font-bold pointer-events-none", textAnchor: "middle", fill: "white", style: { textShadow: "0 1px 2px rgba(0,0,0,0.5)" }, children: plot.number })), isHovered && (_jsxs("g", { children: [_jsx("rect", { x: plotX + PLOT_WIDTH / 2 - 50, y: plotY - 35, width: 100, height: 30, fill: "rgba(0, 0, 0, 0.9)", rx: 4, pointerEvents: "none" }), _jsxs("text", { x: plotX + PLOT_WIDTH / 2, y: plotY - 20, className: "text-xs font-semibold pointer-events-none", textAnchor: "middle", fill: "white", children: [sectionKey, "/", rowNum, "/", plot.number] }), _jsx("text", { x: plotX + PLOT_WIDTH / 2, y: plotY - 10, className: "text-xs pointer-events-none", textAnchor: "middle", fill: "#d1d5db", children: plot.status === "available"
                                                                        ? "Libre"
                                                                        : plot.status === "occupied"
                                                                            ? "Occupé"
                                                                            : "Réservé" })] }))] }, `plot-${plot.id}`));
                                            })] }, `row-${sectionKey}-${rowKey}`));
                                })] }, `section-${sectionKey}`));
                    }) }) }), selectedPlotId === null && (_jsxs("div", { className: "mt-4 grid grid-cols-4 gap-4 text-center text-xs", children: [_jsxs("div", { children: [_jsx("div", { className: "font-semibold text-lg", children: data.total_capacity }), _jsx("div", { className: "text-muted-foreground", children: "Capacit\u00E9" })] }), _jsxs("div", { children: [_jsx("div", { className: "font-semibold text-lg text-blue-600", children: data.occupied_count }), _jsx("div", { className: "text-muted-foreground", children: "Occup\u00E9s" })] }), _jsxs("div", { children: [_jsx("div", { className: "font-semibold text-lg text-green-600", children: data.available_count }), _jsx("div", { className: "text-muted-foreground", children: "Libres" })] }), _jsxs("div", { children: [_jsx("div", { className: "font-semibold text-lg", children: data.section_count }), _jsx("div", { className: "text-muted-foreground", children: "Secteurs" })] })] })), selectedPlotId !== null && (_jsx("div", { className: "mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs", children: _jsxs("div", { className: "flex items-center justify-between", children: [_jsxs("div", { className: "flex items-center gap-2", children: [_jsx(MapPin, { className: "w-4 h-4 text-blue-600" }), _jsxs("span", { children: ["Emplacement s\u00E9lectionn\u00E9 : ID ", selectedPlotId] })] }), _jsx("button", { onClick: () => onPlotSelect?.(null), className: "text-blue-600 hover:text-blue-800 text-xs font-medium", children: "\u2715" })] }) }))] }));
}
// Helper function to group plots by section and row
function groupPlotsBySection(plots) {
    const grouped = {};
    plots.forEach((plot) => {
        const section = plot.section || "?";
        const row = plot.row || 0;
        if (!grouped[section]) {
            grouped[section] = {};
        }
        if (!grouped[section][row]) {
            grouped[section][row] = [];
        }
        grouped[section][row].push(plot);
    });
    return grouped;
}
