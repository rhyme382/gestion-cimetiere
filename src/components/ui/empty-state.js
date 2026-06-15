import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Card, CardContent } from "./card";
export function EmptyState({ icon, title, description }) {
    return (_jsx(Card, { children: _jsxs(CardContent, { className: "flex flex-col items-center justify-center py-12 text-center", children: [icon && _jsx("div", { className: "mb-4 text-muted-foreground/30", children: icon }), _jsx("p", { className: "text-sm font-medium text-foreground", children: title }), description && _jsx("p", { className: "text-xs text-muted-foreground mt-1", children: description })] }) }));
}
