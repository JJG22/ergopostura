import { createBrowserRouter, Outlet, RouterProvider } from "react-router";

import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { AppErrorBoundary, NotFound, RouteError } from "./components/ErrorBoundary";
import { Layout } from "./components/Layout";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { AccountsPage } from "./features/accounts/AccountsPage";
import { ContractDetailPage } from "./features/contracts/ContractDetailPage";
import { ContractFormPage } from "./features/contracts/ContractFormPage";
import { ContractsPage } from "./features/contracts/ContractsPage";
import { CompaniesPage } from "./features/companies/CompaniesPage";
import { CompanyDetailPage } from "./features/companies/CompanyDetailPage";

/** La app vive bajo /app/ en el mismo dominio que la API: la sesión es la misma cookie. */
const router = createBrowserRouter(
  [
    {
      element: <AuthProvider><Outlet /></AuthProvider>,
      errorElement: <RouteError />,
      children: [
        { path: "/ingresar", element: <LoginPage /> },
        {
          path: "/cambiar-contrasena",
          element: <RequireAuth allowTemporaryPassword><ChangePasswordPage /></RequireAuth>,
        },
        {
          path: "/",
          element: <RequireAuth><Layout /></RequireAuth>,
          children: [
            { index: true, element: <DashboardPage /> },
            { path: "empresas", element: <CompaniesPage /> },
            { path: "empresas/:id", element: <CompanyDetailPage /> },
            { path: "usuarios", element: <AccountsPage /> },
            { path: "contratos", element: <ContractsPage /> },
            { path: "contratos/nuevo", element: <ContractFormPage /> },
            { path: "contratos/:id", element: <ContractDetailPage /> },
            { path: "contratos/:id/editar", element: <ContractFormPage /> },
          ],
        },
        { path: "*", element: <NotFound /> },
      ],
    },
  ],
  { basename: "/app" },
);

export function App() {
  return (
    <AppErrorBoundary>
      <RouterProvider router={router} />
    </AppErrorBoundary>
  );
}
