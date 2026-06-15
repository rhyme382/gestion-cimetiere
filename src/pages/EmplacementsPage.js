import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CemeteryMap } from "@/components/map/CemeteryMap";
import { mockCemeteryMap } from "@/mocks/cemetery-map";
export default function EmplacementsPage() {
    const [selectedPlotId, setSelectedPlotId] = useState(null);
    const [selectedPlot, setSelectedPlot] = useState(null);
    const handlePlotSelect = (plot) => {
        if (plot === null) {
            setSelectedPlotId(null);
            setSelectedPlot(null);
        }
        else {
            setSelectedPlotId(plot.id);
            setSelectedPlot(plot);
        }
    };
    return (_jsxs("div", { className: "space-y-4 h-screen flex flex-col", children: [_jsx("div", { className: "flex items-center justify-between", children: _jsxs("div", { children: [_jsx("h1", { className: "text-2xl font-bold text-gray-900", children: mockCemeteryMap.name }), mockCemeteryMap.commune && (_jsxs("p", { className: "text-sm text-gray-600", children: ["Commune de ", mockCemeteryMap.commune] }))] }) }), _jsxs("div", { className: "flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-0", children: [_jsxs(Card, { className: "lg:col-span-3 flex flex-col", children: [_jsxs(CardHeader, { className: "pb-3", children: [_jsx(CardTitle, { className: "text-lg", children: "Plan du cimeti\u00E8re (MVP-14)" }), _jsx("p", { className: "text-xs text-muted-foreground mt-1", children: "Mock data \u2013 Int\u00E9gration r\u00E9elle disponible apr\u00E8s MVP-10 (backend)" })] }), _jsx(CardContent, { className: "flex-1 overflow-hidden", children: _jsx(CemeteryMap, { data: mockCemeteryMap, onPlotSelect: handlePlotSelect, selectedPlotId: selectedPlotId }) })] }), _jsxs(Card, { children: [_jsx(CardHeader, { children: _jsx(CardTitle, { className: "text-base", children: "Informations" }) }), _jsx(CardContent, { className: "space-y-4 text-sm", children: selectedPlot ? (_jsxs(_Fragment, { children: [_jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Emplacement s\u00E9lectionn\u00E9" }), _jsxs("p", { className: "text-base font-semibold mt-1", children: [selectedPlot.section, "/", selectedPlot.row, "/", selectedPlot.number] })] }), _jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Statut" }), _jsx("p", { className: "mt-1", children: _jsx("span", { className: `inline-block px-2 py-1 rounded text-xs font-semibold text-white ${selectedPlot.status === "available"
                                                            ? "bg-green-600"
                                                            : selectedPlot.status === "occupied"
                                                                ? "bg-blue-600"
                                                                : selectedPlot.status === "reserved"
                                                                    ? "bg-orange-600"
                                                                    : "bg-gray-600"}`, children: selectedPlot.status === "available"
                                                            ? "Libre"
                                                            : selectedPlot.status === "occupied"
                                                                ? "Occupé"
                                                                : selectedPlot.status === "reserved"
                                                                    ? "Réservé"
                                                                    : "Indisponible" }) })] }), _jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Capacit\u00E9" }), _jsxs("p", { className: "mt-1", children: [selectedPlot.capacity, " place(s)"] })] }), _jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Occup\u00E9" }), _jsxs("p", { className: "mt-1", children: [selectedPlot.occupied_count, " personne(s)"] })] }), _jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Concession(s)" }), _jsx("p", { className: "mt-1", children: selectedPlot.concession_count })] }), _jsx("button", { onClick: () => {
                                                setSelectedPlotId(null);
                                                setSelectedPlot(null);
                                            }, className: "w-full mt-4 px-3 py-2 bg-gray-200 hover:bg-gray-300 rounded text-xs font-medium text-gray-900 transition", children: "D\u00E9s\u00E9lectionner" })] })) : (_jsx("div", { className: "text-center py-8 text-muted-foreground", children: _jsx("p", { className: "text-sm", children: "S\u00E9lectionnez un emplacement sur le plan" }) })) })] })] }), _jsx(Card, { children: _jsx(CardContent, { className: "pt-4", children: _jsxs("div", { className: "grid grid-cols-2 md:grid-cols-5 gap-4 text-center", children: [_jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Secteurs" }), _jsx("p", { className: "text-xl font-bold", children: mockCemeteryMap.section_count })] }), _jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Rang\u00E9es max" }), _jsx("p", { className: "text-xl font-bold", children: mockCemeteryMap.max_row })] }), _jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Capacit\u00E9 totale" }), _jsx("p", { className: "text-xl font-bold", children: mockCemeteryMap.total_capacity })] }), _jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Occup\u00E9s" }), _jsx("p", { className: "text-xl font-bold text-blue-600", children: mockCemeteryMap.occupied_count })] }), _jsxs("div", { children: [_jsx("p", { className: "text-xs text-muted-foreground font-medium", children: "Libres" }), _jsx("p", { className: "text-xl font-bold text-green-600", children: mockCemeteryMap.available_count })] })] }) }) })] }));
}
