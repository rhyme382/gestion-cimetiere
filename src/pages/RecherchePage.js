import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";
import { useState } from "react";
export default function RecherchePage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [query, setQuery] = useState(searchParams.get("q") ?? "");
    function handleSearch(e) {
        e.preventDefault();
        if (query.trim())
            setSearchParams({ q: query.trim() });
    }
    const currentQuery = searchParams.get("q");
    return (_jsxs("div", { className: "space-y-4 max-w-2xl", children: [_jsx("form", { onSubmit: handleSearch, className: "flex gap-2", children: _jsxs("div", { className: "relative flex-1", children: [_jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" }), _jsx(Input, { type: "search", placeholder: "Rechercher un d\u00E9funt, une concession, un emplacement\u2026", className: "pl-9", value: query, onChange: e => setQuery(e.target.value) })] }) }), currentQuery ? (_jsxs(Card, { children: [_jsx(CardHeader, { children: _jsxs(CardTitle, { className: "text-sm", children: ["R\u00E9sultats pour \u00AB ", currentQuery, " \u00BB"] }) }), _jsx(CardContent, { children: _jsx("p", { className: "text-sm text-muted-foreground", children: "La recherche sera disponible apr\u00E8s MVP-11 (commandes Tauri search_individuals)." }) })] })) : (_jsx(Card, { children: _jsxs(CardContent, { className: "py-12 text-center", children: [_jsx(Search, { className: "h-10 w-10 text-muted-foreground/30 mx-auto mb-3" }), _jsx("p", { className: "text-sm text-muted-foreground", children: "Saisissez un terme pour rechercher dans tous les registres." })] }) }))] }));
}
