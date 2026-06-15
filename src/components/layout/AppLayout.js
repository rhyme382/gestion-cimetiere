import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
const PAGE_TITLES = {
    "/": { title: "Tableau de bord", subtitle: "Vue d'ensemble du cimetière" },
    "/cimetieres": { title: "Cimetières", subtitle: "Gestion des cimetières de la commune" },
    "/emplacements": { title: "Emplacements", subtitle: "Gestion des emplacements" },
    "/concessions": { title: "Concessions", subtitle: "Gestion des concessions funéraires" },
    "/defunts": { title: "Défunts", subtitle: "Registre des défunts" },
    "/alertes": { title: "Alertes", subtitle: "Alertes et échéances" },
    "/recherche": { title: "Recherche", subtitle: "Recherche globale" },
    "/parametres": { title: "Paramètres", subtitle: "Configuration de l'application" },
};
export function AppLayout() {
    const location = useLocation();
    const path = location.pathname;
    const meta = PAGE_TITLES[path] ?? { title: "Gestion Cimetière" };
    return (_jsxs("div", { className: "flex h-screen overflow-hidden bg-background", children: [_jsx(Sidebar, {}), _jsxs("div", { className: "flex flex-1 flex-col overflow-hidden", children: [_jsx(Header, { title: meta.title, subtitle: meta.subtitle }), _jsx("main", { className: "flex-1 overflow-y-auto p-6", children: _jsx(Outlet, {}) })] })] }));
}
