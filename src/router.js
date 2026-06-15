import { jsx as _jsx } from "react/jsx-runtime";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { lazy, Suspense } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const CemeteriesPage = lazy(() => import("@/pages/CemeteriesPage"));
const ConcessionsPage = lazy(() => import("@/pages/ConcessionsPage"));
const DefuntsPage = lazy(() => import("@/pages/DefuntsPage"));
const EmplacementsPage = lazy(() => import("@/pages/EmplacementsPage"));
const RecherchePage = lazy(() => import("@/pages/RecherchePage"));
const AlertesPage = lazy(() => import("@/pages/AlertesPage"));
const ParametresPage = lazy(() => import("@/pages/ParametresPage"));
function PageLoader() {
    return (_jsx("div", { className: "flex h-full items-center justify-center", children: _jsx("div", { className: "h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" }) }));
}
const router = createBrowserRouter([
    {
        path: "/",
        element: _jsx(AppLayout, {}),
        children: [
            { index: true, element: _jsx(Suspense, { fallback: _jsx(PageLoader, {}), children: _jsx(DashboardPage, {}) }) },
            { path: "cimetieres", element: _jsx(Suspense, { fallback: _jsx(PageLoader, {}), children: _jsx(CemeteriesPage, {}) }) },
            { path: "emplacements", element: _jsx(Suspense, { fallback: _jsx(PageLoader, {}), children: _jsx(EmplacementsPage, {}) }) },
            { path: "concessions", element: _jsx(Suspense, { fallback: _jsx(PageLoader, {}), children: _jsx(ConcessionsPage, {}) }) },
            { path: "defunts", element: _jsx(Suspense, { fallback: _jsx(PageLoader, {}), children: _jsx(DefuntsPage, {}) }) },
            { path: "alertes", element: _jsx(Suspense, { fallback: _jsx(PageLoader, {}), children: _jsx(AlertesPage, {}) }) },
            { path: "recherche", element: _jsx(Suspense, { fallback: _jsx(PageLoader, {}), children: _jsx(RecherchePage, {}) }) },
            { path: "parametres", element: _jsx(Suspense, { fallback: _jsx(PageLoader, {}), children: _jsx(ParametresPage, {}) }) },
        ],
    },
]);
export function AppRouter() {
    return _jsx(RouterProvider, { router: router });
}
