import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Card, CardContent } from "@/components/ui/card";
import { Building2 } from "lucide-react";
export default function CemeteriesPage() {
    return (_jsx("div", { className: "space-y-4", children: _jsx(Card, { children: _jsxs(CardContent, { className: "flex flex-col items-center justify-center py-16 text-center", children: [_jsx(Building2, { className: "h-12 w-12 text-muted-foreground/30 mb-4" }), _jsx("p", { className: "text-sm font-medium", children: "Liste des cimeti\u00E8res" }), _jsx("p", { className: "text-xs text-muted-foreground mt-1", children: "Disponible apr\u00E8s impl\u00E9mentation des commandes Tauri (MVP-10)" })] }) }) }));
}
