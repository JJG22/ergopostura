import { createBrowserRouter, Outlet, RouterProvider } from "react-router";

import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { AppErrorBoundary, NotFound, RouteError } from "./components/ErrorBoundary";
import { Layout } from "./components/Layout";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";

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
          children: [{ index: true, element: <DashboardPage /> }],
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
