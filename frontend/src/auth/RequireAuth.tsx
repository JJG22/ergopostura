import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { FullPageSpinner } from "../components/ui";
import { useAuth } from "./AuthContext";

/**
 * Protege una ruta: sin sesión lleva al login; con contraseña temporal, al cambio obligatorio.
 * El servidor aplica las mismas reglas: esto solo evita mostrar pantallas que fallarían.
 */
export function RequireAuth({ children, allowTemporaryPassword = false }: { children: ReactNode; allowTemporaryPassword?: boolean }) {
  const { state } = useAuth();
  const location = useLocation();

  if (state.status === "loading") return <FullPageSpinner />;
  if (state.status === "anonymous") {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/ingresar?next=${next}`} replace />;
  }
  if (state.session.user.must_change_password && !allowTemporaryPassword) {
    return <Navigate to="/cambiar-contrasena" replace />;
  }
  return <>{children}</>;
}
