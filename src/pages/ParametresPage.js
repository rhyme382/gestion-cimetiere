import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Settings } from "lucide-react";
export default function ParametresPage() {
    return (_jsx("div", { className: "space-y-4 max-w-2xl", children: _jsxs(Card, { children: [_jsx(CardHeader, { children: _jsxs("div", { className: "flex items-center gap-2", children: [_jsx(Settings, { className: "h-5 w-5 text-muted-foreground" }), _jsx(CardTitle, { className: "text-base", children: "Param\u00E8tres de l'application" })] }) }), _jsx(CardContent, { children: _jsx("p", { className: "text-sm text-muted-foreground", children: "La configuration communale sera disponible dans une version ult\u00E9rieure (MVP-21+)." }) })] }) }));
}
