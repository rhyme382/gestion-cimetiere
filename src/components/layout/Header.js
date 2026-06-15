import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
export function Header({ title, subtitle }) {
    const navigate = useNavigate();
    const [query, setQuery] = useState("");
    function handleSearch(e) {
        e.preventDefault();
        if (query.trim()) {
            navigate(`/recherche?q=${encodeURIComponent(query.trim())}`);
            setQuery("");
        }
    }
    return (_jsxs("header", { className: "flex h-14 items-center justify-between border-b border-border bg-card px-6 shrink-0", children: [_jsxs("div", { children: [_jsx("h1", { className: "text-base font-semibold text-foreground", children: title }), subtitle && _jsx("p", { className: "text-xs text-muted-foreground", children: subtitle })] }), _jsx("form", { onSubmit: handleSearch, className: "w-72", children: _jsxs("div", { className: "relative", children: [_jsx(Search, { className: "absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" }), _jsx(Input, { type: "search", placeholder: "Recherche globale\u2026", className: "pl-8 h-8 text-xs", value: query, onChange: e => setQuery(e.target.value) })] }) })] }));
}
