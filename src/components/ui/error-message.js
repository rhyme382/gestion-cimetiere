import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { AlertCircle } from "lucide-react";
import { Card, CardContent } from "./card";
export function ErrorMessage({ error, onRetry }) {
    if (!error)
        return null;
    const message = error instanceof Error ? error.message : String(error);
    return (_jsx(Card, { className: "border-destructive bg-destructive/5", children: _jsxs(CardContent, { className: "flex items-start gap-3 py-4", children: [_jsx(AlertCircle, { className: "h-5 w-5 text-destructive shrink-0 mt-0.5" }), _jsxs("div", { className: "flex-1 min-w-0", children: [_jsx("p", { className: "text-sm font-medium text-destructive", children: "Erreur" }), _jsx("p", { className: "text-xs text-destructive/80 mt-1 break-words", children: message }), onRetry && (_jsx("button", { onClick: onRetry, className: "text-xs text-destructive underline mt-2 hover:no-underline", children: "R\u00E9essayer" }))] })] }) }));
}
