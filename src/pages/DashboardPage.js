import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Building2, FileText, Users, Bell } from "lucide-react";
const stats = [
    { label: "Cimetières", value: "—", icon: Building2, color: "text-blue-600" },
    { label: "Concessions", value: "—", icon: FileText, color: "text-green-600" },
    { label: "Défunts", value: "—", icon: Users, color: "text-purple-600" },
    { label: "Alertes actives", value: "—", icon: Bell, color: "text-orange-600" },
];
export default function DashboardPage() {
    return (_jsxs("div", { className: "space-y-6", children: [_jsx("div", { className: "grid grid-cols-2 gap-4 lg:grid-cols-4", children: stats.map(({ label, value, icon: Icon, color }) => (_jsxs(Card, { children: [_jsxs(CardHeader, { className: "flex flex-row items-center justify-between pb-2", children: [_jsx(CardTitle, { className: "text-sm font-medium text-muted-foreground", children: label }), _jsx(Icon, { className: `h-4 w-4 ${color}` })] }), _jsx(CardContent, { children: _jsx("p", { className: "text-2xl font-bold", children: value }) })] }, label))) }), _jsxs(Card, { children: [_jsx(CardHeader, { children: _jsx(CardTitle, { className: "text-sm", children: "Activit\u00E9 r\u00E9cente" }) }), _jsx(CardContent, { children: _jsx("p", { className: "text-sm text-muted-foreground", children: "Aucune activit\u00E9 r\u00E9cente. Les donn\u00E9es seront affich\u00E9es ici une fois le backend complet (MVP-10/11)." }) })] })] }));
}
