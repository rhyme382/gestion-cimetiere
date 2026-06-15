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
  return (
    <div className="flex h-full items-center justify-center">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Suspense fallback={<PageLoader />}><DashboardPage /></Suspense> },
      { path: "cimetieres", element: <Suspense fallback={<PageLoader />}><CemeteriesPage /></Suspense> },
      { path: "emplacements", element: <Suspense fallback={<PageLoader />}><EmplacementsPage /></Suspense> },
      { path: "concessions", element: <Suspense fallback={<PageLoader />}><ConcessionsPage /></Suspense> },
      { path: "defunts", element: <Suspense fallback={<PageLoader />}><DefuntsPage /></Suspense> },
      { path: "alertes", element: <Suspense fallback={<PageLoader />}><AlertesPage /></Suspense> },
      { path: "recherche", element: <Suspense fallback={<PageLoader />}><RecherchePage /></Suspense> },
      { path: "parametres", element: <Suspense fallback={<PageLoader />}><ParametresPage /></Suspense> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
